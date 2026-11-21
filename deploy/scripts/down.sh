#!/usr/bin/env bash
# Para e remove containers (volumes preservados por padrão).
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_env_file

if [[ "${WIPE_VOLUMES:-0}" == "1" ]]; then
  echo "==> down -v (APAGA postgres_data, uploads_data, db_backups)"
  compose down -v --remove-orphans
else
  echo "==> down (volumes preservados; WIPE_VOLUMES=1 para apagar)"
  compose down --remove-orphans
fi
