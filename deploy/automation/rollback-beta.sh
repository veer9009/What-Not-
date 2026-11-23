#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec "${WHATNOT_AUTOMATION_PYTHON:-python3}" -I -B "$script_dir/beta_automation.py" rollback "$@"
