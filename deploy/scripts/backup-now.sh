#!/usr/bin/env bash
# pg_dump one-shot no volume db_backups (mesmo volume do serviço db-backup).
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

validate_prod_env

echo "==> Dump one-shot → volume db_backups"
compose run --rm --entrypoint /bin/sh db-backup -c '
  set -eu
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  file="/backups/vitrine_${ts}.sql.gz"
  echo "db-backup-now: writing ${file}"
  pg_dump -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-acl \
    | gzip -c > "${file}.tmp"
  mv "${file}.tmp" "${file}"
  ls -lh "${file}"
'
echo "OK."
