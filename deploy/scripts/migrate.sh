#!/usr/bin/env bash
# Roda Alembic upgrade head (one-shot). Útil se migrate falhou no up.
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

validate_prod_env

echo "==> alembic upgrade head…"
compose run --rm --no-deps migrate
echo "OK."
