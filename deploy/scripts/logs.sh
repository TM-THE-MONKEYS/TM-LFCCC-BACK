#!/usr/bin/env bash
# Tail dos logs. Uso: ./logs.sh [serviço]  — ex.: ./logs.sh api
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

require_env_file
service="${1:-}"
if [[ -n "${service}" ]]; then
  compose logs -f --tail=200 "${service}"
else
  compose logs -f --tail=100
fi
