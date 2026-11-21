#!/usr/bin/env bash
# Cria o usuário admin via CLI dentro do container api.
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

validate_prod_env

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

email="${ADMIN_EMAIL:-admin@vitrine.local}"

echo "==> create-admin (${email})"
if [[ -t 0 ]]; then
  # Interativo: a CLI pede senha se --password for omitido.
  compose exec -it api python -m app.cli create-admin --email "${email}"
else
  if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
    echo "Erro: sem TTY e ADMIN_PASSWORD vazio — defina no .env ou rode interativo." >&2
    exit 1
  fi
  compose exec -T api python -m app.cli create-admin \
    --email "${email}" \
    --password "${ADMIN_PASSWORD}"
fi
