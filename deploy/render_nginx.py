"""Render a review artifact only. Does not install, reload, connect or overwrite."""
import argparse
from pathlib import Path
import re


def render_nginx(domain, certificate, private_key, frontend, access_file):
    if len(domain) > 253 or '.' not in domain or any(
        not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
        for label in domain.split('.')
    ):
        raise ValueError('Supply a reviewed DNS name without configuration syntax')
    paths = [certificate, private_key, frontend, access_file]
    if any(not re.fullmatch(r'/[A-Za-z0-9_./-]+', value) or '..' in value.split('/') for value in paths):
        raise ValueError('Supply absolute Linux paths without whitespace or configuration syntax')
    content = (Path(__file__).parent / 'nginx/whatnot.conf.template').read_text(encoding='utf-8')
    values = dict(PILOT_DOMAIN=domain.lower(), TLS_CERTIFICATE=certificate,
                  TLS_PRIVATE_KEY=private_key, FRONTEND_ROOT=frontend,
                  PILOT_ACCESS_FILE=access_file)
    for name, value in values.items():
        content = content.replace('@@' + name + '@@', value)
    if '@@' in content:
        raise ValueError('Unresolved configuration input')
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['domain', 'certificate', 'private-key', 'frontend', 'access-file', 'output']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    content = render_nginx(args.domain, args.certificate, args.private_key, args.frontend, args.access_file)
    # Exclusive creation protects any previously reviewed configuration.
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as target:
        target.write(content)
    print('Rendered review artifact. nginx -t and owner-approved installation remain required.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileExistsError):
        raise SystemExit('STOP: invalid input or output already exists; no installation performed') from None
