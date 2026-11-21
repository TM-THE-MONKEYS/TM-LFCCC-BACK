# Deploy on-prem — LFCCC / Vitrine (VM Ubuntu)

Pacote para subir **API + Postgres + front (nginx origem única)** na rede local do cliente.

- **Produção:** imagens no GHCR (`ghcr.io/tm-the-monkeys/tm-lfccc-back` e `…/tm-lfccc-front`).
- **Sem TLS** por enquanto (HTTP na LAN — decisão do produto).
- **Sem Cloudflare Tunnel / Caddy.**
- Esta pasta vive no repo **TM-LFCCC-BACK**. O front entra só como imagem (ou build local opcional).

A máquina de desenvolvimento Windows **não** é o alvo. O alvo é a **VM Ubuntu** (Hyper-V no host Windows do cliente).

---

## Pré-requisitos (na VM Ubuntu)

1. Docker Engine + plugin Compose v2 (`docker compose version`).
2. Acesso de rede à LAN; IP **fixo** ou reserva DHCP recomendada (TeamViewer fica no host Windows; a VM precisa ser alcançável pelo IP).
3. Conta GitHub com permissão de leitura em packages **ou** imagens GHCR públicas.
4. `git` opcional (pode copiar só a pasta `deploy/` + `.env`).

```bash
# Exemplo Ubuntu
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker "$USER"   # relogue depois
```

---

## Subir em menos de 10 passos

1. Na VM, clone o back (ou copie a pasta `deploy/`):

   ```bash
   git clone https://github.com/TM-THE-MONKEYS/TM-LFCCC-BACK.git
   cd TM-LFCCC-BACK
   git checkout chore/prod-readiness   # ou main, quando mergeado
   cd deploy
   ```

2. Login no GHCR (se as imagens forem privadas):

   ```bash
   # PAT com read:packages (e SSO autorizado no org, se aplicável)
   echo "$GITHUB_TOKEN" | docker login ghcr.io -u SEU_USUARIO --password-stdin
   ```

3. Ambiente:

   ```bash
   cp .env.prod.example .env
   nano .env   # ou vim
   ```

4. **Obrigatório editar no `.env`:**

   | Variável | O que colocar |
   |---|---|
   | `POSTGRES_PASSWORD` | senha forte URL-safe |
   | `JWT_SECRET` | ≥ 32 chars aleatórios |
   | `ADMIN_PASSWORD` | senha do admin inicial |
   | `ALLOWED_HOSTS` | `IP_DA_VM,127.0.0.1` (e hostname se houver) |
   | `CORS_ORIGINS` | `http://IP_DA_VM` |
   | `APP_TAG` | `latest` ou sha publicado pelo CI |

5. Tornar scripts executáveis (se o clone veio do Windows):

   ```bash
   chmod +x scripts/*.sh
   ```

6. Subir:

   ```bash
   ./scripts/up.sh
   ```

7. Criar admin (se for a primeira vez):

   ```bash
   ./scripts/create-admin.sh
   ```

8. Abrir no navegador da LAN: `http://IP_DA_VM/`

9. (Opcional) Conferir logs: `./scripts/logs.sh api`

10. Backup manual: `./scripts/backup-now.sh`

---

## Variáveis obrigatórias

Sem estas o `docker compose` / `up.sh` recusa subir:

- `POSTGRES_PASSWORD`, `JWT_SECRET`, `ADMIN_PASSWORD`
- `ALLOWED_HOSTS`, `CORS_ORIGINS` (nunca `*`)

Defaults seguros já no compose:

- `ENVIRONMENT=production`, `CREATE_TABLES_ON_STARTUP=false`
- `PUBLIC_BASE_URL=` (vazio → `imageUrl` relativo)
- `FORWARDED_ALLOW_IPS=172.28.0.0/16` (= `VITRINE_SUBNET`)
- Imagens: `ghcr.io/tm-the-monkeys/tm-lfccc-{back,front}:${APP_TAG}`

---

## Atualização

1. Publique novas imagens (CI na `main` / tag) ou defina `APP_TAG=<sha>`.
2. Na VM: edite `.env` (`APP_TAG=…`), depois:

   ```bash
   ./scripts/up.sh
   ```

O serviço `migrate` roda de novo (Alembic idempotente) antes da API ficar healthy.

---

## Fallback: build local (sem GHCR)

Clones **irmãos** no mesmo nível:

```text
/opt/lfccc/TM-LFCCC-BACK/   ← este repo
/opt/lfccc/LFCCC-FRONT/     ← front (nome da pasta)
```

```bash
cd /opt/lfccc/TM-LFCCC-BACK/deploy
cp .env.prod.example .env   # edite
USE_LOCAL_BUILD=1 ./scripts/up.sh
```

Isso aplica `docker-compose.build.yml` (context `../backend` e `../../LFCCC-FRONT`).

---

## Backup e restore básico

- **Agendado:** serviço `db-backup` grava `vitrine_*.sql.gz` no volume `db_backups` (intervalo/retenção no `.env`).
- **Agora:** `./scripts/backup-now.sh`
- **Listar:**

  ```bash
  docker compose -f docker-compose.yml run --rm --entrypoint ls db-backup -lah /backups
  ```

- **Restore (cuidado — sobrescreve dados):**

  ```bash
  # copie o .sql.gz para dentro do volume ou use docker cp
  gunzip -c vitrine_YYYYMMDD.sql.gz | docker compose -f docker-compose.yml exec -T db \
    psql -U vitrine -d vitrine
  ```

Offsite / cópia para outro host: **backlog** (Julio decide depois).

---

## Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| HTTP 400 TrustedHost | `ALLOWED_HOSTS` sem o IP/hostname usado no browser | Inclua o host + `127.0.0.1` |
| 502 / 503 em `/api` | API unhealthy ou ainda migrando | `./scripts/logs.sh api` e `docker compose ps` |
| Login 429 | Rate limit no nginx (10/min) | Aguarde ~1 min |
| `pull` 401/403 GHCR | Sem login ou package privado | `docker login ghcr.io` + PAT `read:packages` |
| Migrate falhou | DB/senha/URL | `./scripts/migrate.sh` + logs |
| Imagens não carregam | `PUBLIC_BASE_URL` absoluto errado | Deixe vazio (origem única) |

Dev local (Windows/dev): continue usando `backend/docker-compose.yml` (+ override para publicar `:8000`). **Não** misture com esta pasta `deploy/` no mesmo host sem cuidado com portas/volumes.

---

## TeamViewer / rede

- Suporte remoto: host Windows do cliente (TeamViewer).
- A VM Ubuntu precisa de **IP fixo na LAN** ou reserva DHCP para `ALLOWED_HOSTS`/`CORS_ORIGINS` estáveis.
- Firewall do host Hyper-V / Windows deve permitir tráfego LAN → porta 80 da VM.

---

## O que Julio configura na VM (checklist)

- [ ] IP/hostname da VM
- [ ] Senhas: Postgres, JWT, admin
- [ ] Login GHCR (se packages privados) ou tornar packages públicos no org
- [ ] `APP_TAG` desejado
- [ ] Confirmar porta 80 livre (`FRONT_HOST_PORT`)

---

## Scripts

| Script | Função |
|---|---|
| `scripts/up.sh` | valida `.env`, pull/build, `up -d`, status |
| `scripts/migrate.sh` | `alembic upgrade head` one-shot |
| `scripts/create-admin.sh` | `python -m app.cli create-admin` |
| `scripts/backup-now.sh` | `pg_dump` → volume `db_backups` |
| `scripts/down.sh` | para stack (`WIPE_VOLUMES=1` apaga volumes) |
| `scripts/logs.sh` | `logs -f` |

No Windows (só se editar daqui): scripts devem ficar com **LF** (`git` + `.gitattributes`). Na VM: `chmod +x scripts/*.sh`.
