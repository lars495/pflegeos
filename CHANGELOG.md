# CHANGELOG

> Für Pflegekräfte und Bewohner verständlich, nicht nur für Entwickler.

---

## 2026-05-27 — Tag 1 · Stack läuft

### Live
- **Hetzner-Server** in Falkenstein bezogen (CPX22, 3 vCPU, 4 GB RAM, 80 GB SSD)
- **System gehärtet:** ufw, fail2ban, automatische Sicherheits-Patches, root-SSH deaktiviert
- **Docker-Stack steht:** PostgreSQL+pgvector, Redis, API (FastAPI), Public Site
- **API-Healthcheck** antwortet, **Budget-Guard** funktioniert ($0/$1.10 heute)
- **OpenRouter** mit 48,80 $ Saldo verbunden

### Noch nicht
- Autonomer Agent-Runner (Entscheidung morgen: Claude Code CLI vs. eigener Python-Agent)
- Custom-Domain für API/Care-App (Public Site läuft auf pflegeos.vercel.app)
- Erstes echtes Feature — das baut der Agent morgen

---

## 2026-05-26 — Tag 0 · Grundstein

### Neu
- **Projekt gestartet.** Repository mit drei Säulen: Personenzentrierung, Empowerment, Offenheit.
- **Master-Prompt für den autonomen Agenten** geschrieben. Ab morgen baut die KI täglich weiter.
- **Roadmap** mit vier Phasen veröffentlicht. Pflegeplan-Canvas ist das Herzstück (Phase 2).
- **Contribute-Seite** im Entwurf: Jede Person kann Ideen oder Gesetze einreichen.
- **Budget-Wächter** gebaut: Die KI darf maximal 1 € pro Tag ausgeben. Hartes Limit.
- **KI-Jurist** angelegt: Einmal im Monat prüft ein stärkeres Modell, ob alle Gesetze noch eingehalten sind und sucht nach neuen Verordnungen.

### Hinter den Kulissen
- Tech-Stack festgelegt: Hetzner VPS in Deutschland, PostgreSQL mit pgvector statt Pinecone (DSGVO!), Whisper läuft lokal.
- Docker-Compose-Stack mit nginx + TLS-Routing vorbereitet.
- 16 rechtliche Anforderungen initial in `legal_requirements.yaml` aufgenommen — von SGB XI über DSGVO Art. 9 bis zu DNQP-Expertenstandards.

### Live
- **Public Site:** https://pflegeos.vercel.app
- **Repository:** https://github.com/lars495/pflegeos

### Was morgen kommt
- Bewohner-Profil mit Biografie (höchster Personenzentrierungs-Score in Phase 1)
- Login + Rollen-Modell
- Erstes echtes Deployment auf den Hetzner-VPS
