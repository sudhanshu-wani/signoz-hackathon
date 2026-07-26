# Deploying SigNoz with Foundry (what judges reproduce)

This repo ships `casting.yaml` + `casting.yaml.lock`, so you can reproduce the
exact SigNoz deployment this project was built and verified against.

## 1. Install foundryctl
```bash
curl -fsSL https://signoz.io/foundry.sh | bash
foundryctl --help
```

## 2. Deploy
```bash
foundryctl cast -f casting.yaml
```
`cast` validates tooling (`gauge`), forges deployment files into `pours/`, and
starts the stack. It writes `casting.yaml.lock` (resolved config + checksums);
the one committed here came from a real run on the author's machine.

- UI: **http://localhost:8080**
- OTLP ingest (where the proxy exports): gRPC `:4317`, HTTP `:4318`

If `cast` is interrupted mid-image-pull, bring the already-forged stack up with:
```bash
docker compose -f pours/deployment/compose.yaml up -d
```

## 3. ⚠️ Create the first account — required before ANY telemetry works
Open **http://localhost:8080** and create the admin account, then:
```bash
docker restart signoz-ingester-1
```

This is not optional plumbing. The collector registers with the SigNoz server
over OpAMP, and the server refuses to register it until an organization exists —
which only happens when the first user is created. Until then the OTLP port
accepts connections and immediately resets them, and **all telemetry is silently
dropped** (server log: `cannot create agent without orgId`). We lost an hour to
this; hence the loud warning.

## 4. Point this project at it
```bash
cp .env.example .env     # set SIGNOZ_EMAIL / SIGNOZ_PASSWORD (the account above)
```
No API key needed — the REST client logs in with those credentials and discovers
the org via `/api/v2/sessions/context`. If you'd rather use a key, set
`SIGNOZ_API_KEY` and it takes precedence.

## Endpoints this project uses (verified on SigNoz v0.134)
| Purpose             | Endpoint                                          |
|---------------------|---------------------------------------------------|
| Trace/metric export | OTLP gRPC `:4317`                                 |
| Login               | `POST /api/v2/sessions/email_password` (+ `orgID`) |
| Create dashboard    | `POST /api/v1/dashboards`                         |
| Query data          | `POST /api/v5/query_range`                        |
| Alert rules         | `POST /api/v1/rules` — rejected our payloads on this build; create the alert in the UI (spec in `proxy/dashboards/cost_spike_alert.json`) |

## Files committed for reproduction
- `casting.yaml` — declarative deployment
- `casting.yaml.lock` — real checksums from `foundryctl cast`
