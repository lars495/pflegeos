# PflegeOS

> Eine Pflegesoftware für stationäre Langzeitpflege in Deutschland — gebaut für Menschen, nicht für Bürokratie.

🌐 **Live:** [pflegeos.vercel.app](https://pflegeos.vercel.app) · 📜 **Lizenz:** [AGPL-3.0](./LICENSE)

[🇩🇪 Deutsch](#deutsch) · [🇬🇧 English](#english)

---

## Deutsch

PflegeOS ist ein offenes Experiment: Eine Pflegesoftware, die von einer KI autonom weiterentwickelt wird — Tag für Tag, mit einem Budget von 1 € pro Tag. Drei Werte tragen das Projekt:

1. **Personenzentrierung** — Bewohner:innen sind Menschen mit Biografie, nicht Fälle.
2. **Empowerment** — Pflegekräfte gestalten Prozesse. KI dient ihnen, niemals umgekehrt.
3. **Offenheit** — Die Community trägt Ideen und Gesetzeswissen bei.

### Mitwirken
- **Idee einreichen:** [pflegeos.vercel.app#mitmachen](https://pflegeos.vercel.app#mitmachen) — Formular live, Backend folgt sobald der VPS steht. Bis dahin: <lars@innovation-pflegen.de>
- **Gesetz/Verordnung hochladen:** gleiche URL, Formularfeld "Art deines Beitrags" → Gesetz
- **Code beitragen:** Fork & PR — siehe [CONVENTIONS.md](./CONVENTIONS.md). Beiträge stehen unter AGPL-3.0.

### Tägliches Update
Die KI baut jeden Tag etwas Neues und postet, was sie gelernt hat. Folge mit:
- Mastodon: *@pflegeos — Handle folgt in Kürze, automatisches tägliches Update*
- LinkedIn: *(persönliche Posts des Betreibers)*

### Was hier wichtig ist zu lesen
| Datei | Was darin steht |
|---|---|
| [PRINCIPLES.md](./PRINCIPLES.md) | Die drei Säulen — verbindlich für jede Designentscheidung |
| [AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md) | Der Master-Prompt für den autonomen Build-Agenten |
| [ROADMAP.md](./ROADMAP.md) | Was als nächstes gebaut wird, mit Begründung |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Tech Stack + VPS-Setup |
| [CONVENTIONS.md](./CONVENTIONS.md) | Code-Stil, Commit-Format, PR-Regeln |
| [legal_requirements.yaml](./legal_requirements.yaml) | Was deutsches Pflegerecht von der Software verlangt |

---

## English

PflegeOS is an open experiment: care home software that is developed autonomously by an AI — day by day, on a 1 €/day budget. Three values carry the project:

1. **Person-centeredness** — Residents are people with biographies, not cases.
2. **Empowerment** — Care workers design processes. AI serves them, never the other way around.
3. **Openness** — The community contributes ideas and legal knowledge.

The project targets German stationary long-term care (`stationäre Langzeitpflege`) and is bound by German law. The codebase is English, the user-facing UI is German.

### License
AGPL-3.0. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

### Status
🌱 **Day 0 done.** Public site live at [pflegeos.vercel.app](https://pflegeos.vercel.app). Backend, autonomous build loop and legal-audit cron start once the VPS is provisioned.
