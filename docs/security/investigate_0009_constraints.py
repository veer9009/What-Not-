"""Read-only investigation; never restores, migrates, or changes application code."""
import importlib.util
import json
from pathlib import Path
import re

from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rehearsal_guards', Path(__file__).with_name('rehearse_0009_migration.py'))
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)

TARGETS = [('whatnot_app_dev', 41069),
           ('whatnot_0009_rehearsal_20261115_f24a8f87', 51678),
           ('whatnot_0009_rollback_20261115_f24a8f87', 51679)]
LITERAL = r"'(?:[^']|'')*'"


def narrow_signature(definition):
    """Diagnostic recognizer ONLY for the two observed enum-check forms.

    Not installed in the rehearsal validator; unknown syntax fails closed.
    Retains column, literal order, spelling, operator and unrestricted cast types.
    """
    for prefix, item, suffix in [
        ('CHECK ((({column})::text = ANY ((ARRAY[', LITERAL + r'::character varying', '])::text[])))'),
        ('CHECK ((({column})::text = ANY (ARRAY[', r'\(' + LITERAL + r'::character varying\)::text', '])))'),
    ]:
        pattern = re.escape(prefix).replace(re.escape('{column}'), r'(?P<column>[a-z_]+)')
        pattern += r'(?P<items>' + item + r'(?:, ' + item + r')*)' + re.escape(suffix)
        match = re.fullmatch(pattern, definition)
        if match:
            return match['column'], tuple(re.findall(LITERAL, match['items']))
    return None


CATALOG = """SELECT t.relname,k.conname,pg_get_constraintdef(k.oid),
    k.contype,k.convalidated,k.condeferrable,k.condeferred,k.connoinherit,
    k.conislocal,k.coninhcount,
    ARRAY(SELECT a.attname || ':' || format_type(a.atttypid,a.atttypmod)
        || ':' || a.attcollation::text || ':' || a.attnotnull::text
        FROM unnest(k.conkey) WITH ORDINALITY AS keys(attnum,position)
        JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=keys.attnum
        ORDER BY keys.position)
    FROM pg_constraint k JOIN pg_class t ON t.oid=k.conrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' ORDER BY t.relname,k.conname"""


def main():
    url = guards.configuration()
    # Verify all catalog OIDs before opening either target connection. The
    # original connection's first application query verifies its own identity.
    with guards.connect(url, guards.SOURCE) as source:
        guards.source_check(source)
        for name, oid in TARGETS:
            actual = source.execute('SELECT oid,datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_database WHERE datname=%s', (name,)).fetchone()
            guards.require(actual == (oid, True))
    databases = []
    catalogs = []
    for name, oid in TARGETS:
        with guards.connect(url, name) as connection:
            actual = connection.execute(guards.IDENTITY).fetchone()
            if name == guards.SOURCE:
                guards.source_check(connection)
            else:
                guards.validate_target(actual, name, oid, 'f24a8f87')
            guards.require(connection.execute('SHOW transaction_read_only').fetchone()[0] == 'on')
            tables = connection.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
            revision = connection.execute('SELECT version_num FROM public.alembic_version').fetchone()[0] if tables else None
            public_columns = connection.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='seller_profiles' AND column_name=ANY(%s)", (list(guards.PUBLIC_FIELDS),)).fetchone()[0]
            databases.append(dict(name=name, oid=oid, host=actual[2], port=actual[3],
                                  server_version=actual[4], primary=not actual[5],
                                  owner_match=actual[6], read_only=True, public_tables=tables,
                                  revision=revision, public_discovery_columns=public_columns))
            catalogs.append(connection.execute(CATALOG).fetchall())

    source, restored = catalogs[:2]
    guards.require(len(source) == len(restored))
    differences = []
    total_cases = negative_tests = 0
    # Evaluate only synthetic inputs, with a read-only connection to rehearsal.
    with guards.connect(url, TARGETS[1][0]) as connection:
        guards.validate_target(connection.execute(guards.IDENTITY).fetchone(), TARGETS[1][0], TARGETS[1][1], 'f24a8f87')
        connection.execute('SET LOCAL search_path = pg_catalog, public')
        guards.require(connection.execute('SHOW standard_conforming_strings').fetchone()[0] == 'on')
        for expected, actual in zip(source, restored):
            guards.require(expected[:2] == actual[:2] and expected[3:] == actual[3:])
            if expected[2] == actual[2]:
                continue
            sig = narrow_signature(expected[2])
            guards.require(sig is not None and sig == narrow_signature(actual[2]))
            column, literals = sig
            values = [s[1:-1].replace("''", "'") for s in literals]
            cases = values + [None, '', '__SYNTHETIC_INVALID__', ' ', '\u2603']
            cases += [v.lower() for v in values] + [' '+v for v in values] + [v+' ' for v in values]
            query = sql.SQL('''SELECT count(*),
                count(*) FILTER (WHERE ({before}) IS DISTINCT FROM ({after})),
                count(*) FILTER (WHERE (({before}) IS NOT FALSE) IS DISTINCT FROM (({after}) IS NOT FALSE))
                FROM unnest(%s::text[]) AS synthetic({column})''').format(
                    before=sql.SQL(expected[2][6:]), after=sql.SQL(actual[2][6:]), column=sql.Identifier(column))
            count, boolean_diffs, acceptance_diffs = connection.execute(query, (cases,)).fetchone()
            guards.require(count == len(cases) and boolean_diffs == acceptance_diffs == 0)
            # Mutation tests for the proposed narrow comparison, not modifications
            # to the real validator. Reject changed literals, columns/operators,
            # bounded casts, NOT VALID flags and unrecognized expressions.
            for changed in [actual[2].replace(literals[0], "'__CHANGED__'", 1),
                            actual[2].replace('('+column+')', '(other_column)', 1),
                            actual[2].replace(' = ANY ', ' <> ANY ', 1),
                            actual[2].replace('character varying', 'character varying(1)', 1),
                            actual[2]+' NOT VALID', 'CHECK (true)']:
                guards.require(narrow_signature(changed) != sig)
                negative_tests += 1
            total_cases += count
            differences.append(dict(table=expected[0], constraint=expected[1], expected=expected[2],
                                    actual=actual[2], metadata_equal=True, validated=actual[4],
                                    structural_signature_equal=True, synthetic_cases=count,
                                    boolean_differences=boolean_diffs, check_acceptance_differences=acceptance_diffs))
    result = dict(status='PASS',investigation_only=True,databases=databases,
                  constraints_compared=len(source),textually_different=len(differences),
                  all_constraint_names_and_metadata_equal=True,
                  synthetic_truth_table_cases=total_cases,negative_recognizer_tests=negative_tests,
                  conclusion='Observed differences are equivalent varchar-array versus per-element text casts; strict string equality caused a false rejection.',
                  migration_0009_executed=False,application_and_rehearsal_code_changed=False,
                  database_writes=False,differences=differences)
    path = ROOT/'docs/security/evidence/0009-constraint-investigation.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='differences'},indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps(dict(status='STOP',error_category=type(error).__name__,private_inputs_suppressed=True)))
        raise SystemExit(1) from None
