# Contrato OpenAPI → TypeScript

Fonte de verdade HTTP: schema OpenAPI gerado pela app FastAPI.  
Tipos TS versionados em `backend/api-contract.d.ts` (sincronizar manualmente nesta fase).

## Exportar OpenAPI

```bash
cd backend
python scripts/export-openapi.py
# → backend/openapi.json
```

## Gerar `api-contract.d.ts`

Requer Node.js:

```bash
cd backend
npx openapi-typescript openapi.json -o api-contract.d.ts
```

Revise o diff e commit ambos `openapi.json` (opcional) e `api-contract.d.ts` com mudanças de contrato.

CI desta fase **não** roda `openapi-typescript` (evita Node no pipeline). O script Python de export é o caminho mínimo para manter o schema reproduzível.

## Integração front

Contrato narrativo (envelope, camelCase, auth/roles): [FRONTEND_INTEGRATION.md](../FRONTEND_INTEGRATION.md).
