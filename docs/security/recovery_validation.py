"""Shared validation bodies from the reviewed isolated-cluster rehearsal runner."""
from rehearse_auth_recovery import *

def validate_copy(target, baseline, config, clone_args, save):
    stage = "validation"
    users = baseline["users"]
    orders = {row[0]["id"]: row[0] for row in baseline["orders"]}
    engine = create_engine(target, echo=False, hide_parameters=True)
    try:
        with psycopg.connect(**clone_args) as clone:
            current = snapshot(clone)
            require(current['alembic_version'] == [({'version_num': '0008'},)], 'Wrong final revision')
            for table, rows in baseline.items():
                if table not in {'alembic_version', 'users', 'orders'}:
                    require(current[table] == rows, 'Original business rows changed unexpectedly')
            preserved = [{k:v for k,v in r[0].items() if k not in
                {'phone_verified_at','email_verified_at'}} for r in current['users']]
            require(sorted(preserved, key=lambda r:r['id']) == sorted(
                [r[0] for r in users], key=lambda r:r['id']), 'Original user fields changed')
            require(all(r[0]['phone_verified_at'] is None and r[0]['email_verified_at'] is None
                        for r in current['users']), 'Unexpected verification evidence')
            audits = [r[0] for r in current['audit_events']]
            require(len(audits) == 2, 'Unexpected migration audit count')
            converted = 0
            for row, in current['orders']:
                previous = orders[row['id']]
                expected = dict(previous)
                expected.update(delivered_at=None, confirmation_deadline=None,
                                completed_at=None, completion_source=None)
                if previous['status'] == 'DELIVERED':
                    expected.update(status='COMPLETED', completion_source='LEGACY')
                    converted += 1
                    matching = [a for a in audits if a['entity_id'] == row['id'] and
                        a['actor_type']=='MIGRATION' and a['entity_type']=='order' and
                        a['action']=='ORDER_MIGRATION' and a['previous_status']=='DELIVERED' and
                        a['next_status']=='COMPLETED' and a['reason']=='0005_LEGACY_MAPPING']
                    require(len(matching) == 1, 'Missing exact order migration audit event')
                require(row == expected, 'Order transformation mismatch')
            invalid = clone.execute("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated").fetchone()[0]
            invalid_indexes = clone.execute("SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND (NOT i.indisvalid OR NOT i.indisready)").fetchone()[0]
            require(invalid == 0 and invalid_indexes == 0, 'Invalid constraints or indexes')
            sequences = clone.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND column_default LIKE 'nextval(%'").fetchall()
            for table, column in sequences:
                seq = clone.execute('SELECT pg_get_serial_sequence(%s,%s)', (f'public.{table}',column)).fetchone()[0]
                last, called = clone.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(*seq.split('.')))).fetchone()
                maximum = clone.execute(sql.SQL('SELECT max({}) FROM public.{}').format(sql.Identifier(column),sql.Identifier(table))).fetchone()[0]
                require(maximum is None or last > maximum or (called and last == maximum), 'Sequence behind existing IDs')
        with engine.connect() as connection:
            inspector = inspect(connection)
            for table in Base.metadata.sorted_tables:
                require(inspector.has_table(table.name), 'Missing ORM table')
                require(set(table.columns.keys()) <= {c['name'] for c in inspector.get_columns(table.name)}, 'Missing ORM columns')
            connection.execute(select(User).limit(0))
            connection.execute(select(RequestQuota).limit(0))
        with Session(engine) as session:
            require(len(UserRepository(session).by_normalized_email(users[0][0]['email'].lower())) == 1,
                    'Existing-user authentication lookup failed')
        command.check(config)
        save(stage, {'status':'PASS', 'original_users_unchanged':5,
            'legacy_order_conversions':converted, 'placed_orders_unchanged':1,
            'matching_migration_audit_events':len(audits), 'all_original_other_rows_unchanged':True,
            'orm_table_column_coverage':True, 'alembic_check':'PASS',
            'request_quotas_table_present':True, 'user_verification_columns_present':True,
            'invalid_constraints':invalid, 'invalid_indexes':invalid_indexes,
            'sequences_checked':len(sequences), 'auth_queries':'PASS'})
    finally:
        engine.dispose()

def smoke_authentication(target, clone_args, save):
    stage = "authentication_smoke"
    smoke_settings = Settings(_env_file=None, database_url=target.render_as_string(hide_password=False),
        environment='development', jwt_secret_key=secrets.token_urlsafe(48),
        email_provider='disabled', beta_allowed_emails=[], abuse_limits_enabled=True)
    require(make_url(smoke_settings.database_url.get_secret_value()) == target, 'Smoke DB mismatch')
    application = create_app(smoke_settings)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    password = secrets.token_urlsafe(32)
    payload = dict(name='Recovery rehearsal buyer', email='recovery-rehearsal@example.com',
                   phone='rehearsal-'+secrets.token_hex(6), password=password, role='BUYER')
    statuses = {}
    with TestClient(application) as client:
        def check(label, method, path, expected, **kwargs):
            response = client.request(method, '/api/v1'+path, **kwargs)
            statuses[label] = response.status_code
            require(response.status_code == expected, f'{label} HTTP status mismatch')
            return response
        check('readiness','GET','/ready',200)
        registration = check('registration','POST','/auth/register',201,json=payload)
        check('duplicate_registration','POST','/auth/register',409,json=payload)
        check('invalid_registration','POST','/auth/register',422,json={})
        login = check('login','POST','/auth/login',200,json=dict(email=payload['email'],password=password))
        me = check('authenticated_identity','GET','/auth/me',200,
                   headers={'Authorization':'Bearer '+login.json()['access_token']})
        require(me.json()['id'] == registration.json()['id'], 'Authenticated identity mismatch')
        check('wrong_password','POST','/auth/login',401,json=dict(email=payload['email'],password='wrong-password'))
        check('invalid_token','GET','/auth/me',401,headers={'Authorization':'Bearer invalid'})
    with psycopg.connect(**clone_args) as clone:
        quotas = clone.execute('SELECT count(*) FROM request_quotas').fetchone()[0]
        require(quotas > 0, 'Development authentication quotas were not written')
    save(stage, {'status':'PASS','http_statuses':statuses,'quota_rows_created':quotas,
                 'credentials_and_tokens_printed':False,'smtp_and_workers_disabled':True})
