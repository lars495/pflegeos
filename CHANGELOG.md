# CHANGELOG

> Für Pflegekräfte und Bewohner verständlich, nicht nur für Entwickler.

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

### Was morgen kommt
- Bewohner-Profil mit Biografie (höchster Personenzentrierungs-Score in Phase 1)
- Login + Rollen-Modell
- Erstes echtes Deployment auf den VPS
