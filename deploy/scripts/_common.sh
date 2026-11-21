#!/usr/bin/env bash
# Helpers compartilhados pelos scripts de operação (rodar na VM Ubuntu).
# shellcheck shell=bash

set -euo pipefail

DEPLOY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DEPLOY_ROOT}"

ENV_FILE="${DEPLOY_ROOT}/.env"
COMPOSE_BASE=(docker compose -f docker-compose.yml)

if [[ "${USE_LOCAL_BUILD:-0}" == "1" ]]; then
  COMPOSE_BASE+=(-f docker-compose.build.yml)
fi

compose() {
  "${COMPOSE_BASE[@]}" "$@"
}

require_env_file() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Erro: falta ${ENV_FILE}" >&2
    echo "Copie .env.prod.example → .env e preencha os valores da LAN." >&2
    exit 1
  fi
}

require_var() {
  local name="$1"
  # shellcheck disable=SC1090
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
  if [[ -z "${!name:-}" ]]; then
    echo "Erro: variável obrigatória ${name} está vazia no .env" >&2
    exit 1
  fi
}

validate_prod_env() {
  require_env_file
  require_var POSTGRES_PASSWORD
  require_var JWT_SECRET
  require_var ADMIN_PASSWORD
  require_var ALLOWED_HOSTS
  require_var CORS_ORIGINS
  if [[ "${CORS_ORIGINS}" == "*" ]]; then
    echo "Erro: CORS_ORIGINS não pode ser '*' em produção." >&2
    exit 1
  fi
}
