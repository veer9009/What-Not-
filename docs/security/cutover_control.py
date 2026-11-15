"""Guarded administrative controls; only postgres may control the original DB."""
DB='whatnot_app_dev'


def verify_control_identity(actual,oid):
    if tuple(actual)!=('postgres','127.0.0.1/32',5432,oid,True):
        raise RuntimeError('Maintenance connection context, target OID or ownership mismatch')


def verify_defaults(settings):
    if settings not in ([],[(['default_transaction_read_only=on'],)]):
        raise RuntimeError('Unexpected database defaults; stop for review')


def release_plan(integrity_verified):
    if integrity_verified is not True:
        raise RuntimeError('Keep maintenance enabled until integrity passes')
    return ('reset_readonly','allow_connections')


def is_expected_refusal(message,allow_connections):
    return allow_connections is False and 'not currently accepting connections' in message.lower()


COMMANDS={
    'set_readonly':'ALTER DATABASE whatnot_app_dev SET default_transaction_read_only = on',
    'block_connections':'ALTER DATABASE whatnot_app_dev ALLOW_CONNECTIONS false',
    'reset_readonly':'ALTER DATABASE whatnot_app_dev RESET default_transaction_read_only',
    'allow_connections':'ALTER DATABASE whatnot_app_dev ALLOW_CONNECTIONS true',
}


def control(connection,oid,action):
    # Every mutation rechecks actual connection identity and target ownership.
    actual=connection.execute("""SELECT current_database(),inet_server_addr()::text,
        inet_server_port(),oid,datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user)
        FROM pg_database WHERE datname='whatnot_app_dev'""").fetchone()
    verify_control_identity(actual,oid)
    if action not in COMMANDS:
        raise RuntimeError('Unapproved administrative action')
    connection.execute(COMMANDS[action])
    connection.commit()
