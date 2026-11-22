#!/usr/bin/env bash
# Sobe o stack de produção (pull GHCR ou build local se USE_LOCAL_BUILD=1).
set -euo pipefail
# shellcheck source=_common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

validate_prod_env

echo "==> Validando compose…"
compose config --quiet

if [[ "${USE_LOCAL_BUILD:-0}" == "1" ]]; then
  echo "==> Build local (USE_LOCAL_BUILD=1)…"
  compose build
else
  echo "==> Pull imagens (APP_TAG=${APP_TAG:-latest})…"
  compose pull
fi

echo "==> Subindo serviços…"
compose up -d --remove-orphans

echo "==> Status:"
compose ps
echo
echo "Health (aguarde alguns segundos se acabou de subir):"
compose ps --format 'table {{.Name}}\t{{.Status}}' || true
echo
echo "Abra http://<IP-da-VM>/ no navegador da LAN."
echo "Depois: ./scripts/create-admin.sh  (se ainda não criou o admin)"
