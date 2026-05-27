# Architecture

## Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│  Internet                                                        │
└──────────────────┬──────────────────────────┬───────────────────┘
                   │                          │
              pflegeos.de                care.pflegeos.de
              (statisch,                 (Bewohnerdaten,
               kein PII)                  hinter Auth)
                   │                          │
                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Hetzner CX22 — Falkenstein/DE — Docker Compose                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  nginx   │→ │ care-app │  │   api    │← │  worker      │   │
│  │  + TLS   │  │ SvelteKit│  │ FastAPI  │  │  (cron jobs) │   │
│  └──────────┘  └──────────┘  └─────┬────┘  └──────┬───────┘   │
│                                    │              │            │
│  ┌──────────────────┐    ┌─────────▼──────┐  ┌────▼────┐      │
│  │  Whisper (lokal) │    │   PostgreSQL   │  │  Redis  │      │
│  │  Faster-Whisper  │    │   + pgvector   │  │         │      │
│  └──────────────────┘    └────────────────┘  └─────────┘      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │  (nur anonymisierte Prompts)
                       ▼
              ┌────────────────┐
              │   OpenRouter   │
              │   (LLM-Bezug)  │
              └────────────────┘
```

---

## Tech-Stack-Entscheidungen

### Frontend: **SvelteKit**
- **Warum:** Kleinere Bundles als React (wichtig für ältere Tablets in Einrichtungen). PWA-fähig out of the box. Web-Components-freundlich für eingebettete Bewohner-UIs.
- **Verworfen:** React (Bundle-Größe), Vue (Ökosystem schwächer für unsere Mischung), HTMX (zu wenig Reaktivität für Sprach-UI).
- **Apps:** `care-app/` (Pflegekraft + Bewohner UI), `public-site/` (Landingpage, Contribute-Formular, Roadmap-Tracker).

### Backend: **Python + FastAPI**
- **Warum:** Native KI-Integration (Whisper, Embeddings), starkes Typsystem mit Pydantic, gute async-Story, Ökosystem für PDF/Audio-Verarbeitung.
- **Verworfen:** Node (KI-Bibliotheken schwächer), Go (Whisper-Bindings unreif), Elixir (Ökosystem-Risiko für Solo/KI-Projekt).

### Datenbank: **PostgreSQL + pgvector**
- **Warum:** Eine DB für alles. pgvector ersetzt Pinecone DSGVO-konform. Volltextsuche eingebaut. Row-Level-Security für Mandantenfähigkeit später.
- **Verworfen:** Pinecone (US-Cloud), SQLite (kein pgvector, keine Concurrency), MongoDB (kein gutes Relationsmodell für Pflegedaten).

### Cache & Queue: **Redis**
- Sessions, Rate-Limiting, Job-Queue für asynchrone KI-Verarbeitung.
- Persistente Jobs (z. B. tägliche Reports) liegen in PostgreSQL, kurzlebige in Redis.

### Sprache: **faster-whisper (lokal)**
- **Warum:** DSGVO. Audio darf den VPS nicht verlassen. faster-whisper-small läuft mit ~1.5GB RAM auf CX22.
- **Modell-Empfehlung:** `small` für deutsch (gute Qualität, akzeptable Latenz). `tiny` als Fallback bei Last.
- **Verworfen:** OpenAI Whisper API (Daten verlassen DE), Deepgram (US), AssemblyAI (US).

### LLM: **OpenRouter**
- Ein Account, viele Modelle.
- **Standard-Modell (Build-Agent):** Deepseek-V3 oder Gemini Flash (billigste guten Modelle).
- **Standard-Modell (Produktiv-Pflegeunterstützung):** Gemini Flash 1.5 (schnell, billig, gut deutsch).
- **Legal-Audit-Modell:** Claude Sonnet (stärker, 1× pro Monat).
- **Hartes Budget:** $1.10/Tag, durchgesetzt in `packages/llm/budget_guard.py`.

### Container & Deploy: **Docker Compose**
- Kein Kubernetes — Overkill für 1 VPS.
- Compose-File deklariert: db, redis, api, care-app, public-site, worker, nginx.
- Deploy via `make deploy`: pull → build → up -d → healthcheck.

### Reverse Proxy: **nginx**
- TLS via Let's Encrypt (acme.sh oder certbot).
- Rate-Limiting auf Contribute-Endpoint.
- HSTS, CSP, X-Frame-Options, Strict-Transport.

---

## Hosting

### Hetzner Cloud
- **Server:** CX22 (Intel, 2 vCPU, 4 GB RAM, 40 GB SSD) — ca. 4,50 €/Monat
- **Standort:** Falkenstein oder Nürnberg (DE, DSGVO)
- **Backup:** Hetzner Backup-Add-on (~0,90 €/Monat) + tägliches `pg_dump` zu Hetzner Storage Box
- **Skalierung:** Bei wachsendem Bedarf hoch auf CX32 (4 vCPU, 8 GB RAM, ~7 €/Monat)

### Domain & DNS
- **Empfohlen:** pflegeos.de (Cloudflare DNS, EU-Routing)
- **Cloudflare-Proxy:** Nur für statische Public-Site. **Niemals** für `care.pflegeos.de` (Patientendaten dürfen nicht durch US-Proxy).
- **TLS:** Let's Encrypt direkt am nginx.

### Public-Site (separat hostbar)
- Statisch generiert, kann auf Cloudflare Pages oder Vercel (kein PII drauf).
- Contribute-Formular postet via HTTPS an `api.pflegeos.de` (Backend auf Hetzner).

---

## Datenschutz & Sicherheit

### DSGVO Art. 9 (Gesundheitsdaten = besondere Kategorie)
- Verarbeitung nur mit Rechtsgrundlage (Pflegevertrag, Einwilligung)
- Datenminimierung: keine Daten erheben, die nicht direkt nötig sind
- Speicherorts-Garantie: alles auf Hetzner DE
- Recht auf Auskunft, Löschung, Datenübertragbarkeit: implementiert in Phase 4

### Verschlüsselung
- **In Transit:** TLS 1.3 überall, mTLS für interne Service-Calls (später)
- **At Rest:** LUKS auf VPS-Disk (Standard bei Hetzner Cloud verfügbar)
- **Backups:** verschlüsselt mit `age` oder GPG vor Upload zur Storage Box

### Anonymisierung vor LLM-Calls
- `packages/llm/anonymize.py` (TODO): ersetzt Namen, Geburtsdaten, Adressen durch Tokens vor OpenRouter-Call
- Nach Antwort: Tokens zurück-mappen
- Audit: jeder LLM-Call wird mit Tokens und Kosten geloggt

### Audit-Log
- Jeder Zugriff auf Patientendaten wird geloggt (wer, wann, was)
- Logs aufbewahrt min. 10 Jahre (Pflegedoku-Frist)
- Logs nicht löschbar durch System (Append-only)

---

## Verzeichnisstruktur

```
pflegeos/
├── apps/
│   ├── api/                  # FastAPI Backend
│   ├── care-app/             # SvelteKit Pflegekraft + Bewohner UI
│   └── public-site/          # SvelteKit/Static Landingpage
├── packages/
│   ├── llm/                  # OpenRouter-Wrapper, Budget-Guard, Anonymisierung
│   ├── voice/                # Whisper-Setup, Audio-Pipelines
│   └── compliance/           # Legal-Checks, DSGVO-Helfer
├── infra/
│   ├── docker-compose.yml
│   └── nginx.conf
├── scripts/
│   ├── daily_agent.sh        # Cron-Entry für täglichen Build-Loop
│   ├── legal_audit.py        # Monatlicher KI-Jurist
│   ├── process_contributions.py
│   └── post_update.py        # LinkedIn + X
├── contributions/
│   ├── inbox/                # neue Einreichungen
│   ├── processed/            # bearbeitet
│   └── public_log.md         # öffentlich sichtbar
├── reports/
│   ├── daily/                # YYYY-MM-DD.md
│   └── legal/                # YYYY-MM.md
├── tests/                    # Integrationstests
├── PRINCIPLES.md
├── AGENT_INSTRUCTIONS.md
├── ROADMAP.md
├── ARCHITECTURE.md           # (diese Datei)
├── CONVENTIONS.md
├── CHANGELOG.md
├── legal_requirements.yaml
├── Makefile
└── README.md
```

---

## VPS-Setup (One-Shot)

```bash
# Auf frisch provisioniertem Hetzner CX22 (Ubuntu 24.04)
ssh root@<vps-ip>

# 1. System härten
apt update && apt upgrade -y
apt install -y ufw fail2ban git docker.io docker-compose-v2
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
systemctl enable --now docker

# 2. Non-root user
adduser pflegeos && usermod -aG docker pflegeos
su - pflegeos

# 3. Repo
git clone https://github.com/lars495/pflegeos.git
cd pflegeos

# 4. Secrets
cp infra/.env.example infra/.env
# .env editieren: OPENROUTER_API_KEY, DB-Passwort, LinkedIn/X-Keys etc.

# 5. Erststart
make first-boot

# 6. TLS einrichten
make tls

# 7. Cron für täglichen Agent + monatlichen Audit
make install-cron
```

**Erwartete Erststart-Zeit:** ~15 Minuten (Docker-Pulls + Whisper-Modell-Download).

---

## Skalierungspfad

Aktuell 1 VPS → reicht für ~3 Einrichtungen mit je ~80 Bewohnern.

**Wenn mehr nötig:**
1. **Lesen skalieren:** Read-Replica der DB auf zweitem VPS
2. **Whisper skalieren:** dedizierter Inference-Server (CX32 mit GPU bei Hetzner kommt 2026)
3. **Mandantenfähigkeit:** PostgreSQL Row-Level-Security + Schema-per-Tenant
4. **Bei >10 Einrichtungen:** echte Multi-Region-Architektur, dann sind wir aber im Enterprise-Land
