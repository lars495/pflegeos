# Principles · Die drei Säulen

> Diese Datei ist verbindlich. Jeder Beitrag — von Mensch oder KI — wird daran gemessen. Bei Konflikt zwischen einer Säule und einer Anforderung gewinnt die Säule.

---

## 1. Personenzentrierung

**Bewohner:innen sind Menschen mit Biografie, nicht Fälle.**

Was das im Code bedeutet:

- Jede Bewohner-Ansicht beginnt mit Biografie und aktueller Stimmung, nicht mit Diagnose oder Pflegegrad.
- Selbstbestimmung schlägt institutionelle Routine. Wenn ein Bewohner um 11 Uhr aufstehen will und der Schichtplan 7 Uhr vorsieht, ist der Schichtplan flexibel — nicht der Bewohner.
- Wünsche werden niemals als "unrealistisch" verworfen. Sie bleiben sichtbar, auch wenn unerfüllbar — als Auftrag, Wege zu suchen.
- Sprache: Bewohner werden gefragt, nicht über sie verfügt. UI-Texte in der zweiten Person an den Bewohner, nie in der dritten.
- Bei Demenz oder Nicht-Einwilligungsfähigkeit gilt der **mutmaßliche Wille** (§ 1901a Abs. 2 BGB) — nicht das, was Angehörige oder Pflegekräfte für richtig halten.

**Schnelltest:** Würde die Bewohnerin Frau Müller, wenn sie das Feature heute sehen würde, sagen *"Das bin ich"* — oder *"So sieht man mich"*? Wenn Letzteres: Feature überarbeiten.

---

## 2. Empowerment

**Pflegekräfte gestalten Prozesse. KI dient ihnen, niemals umgekehrt.**

Was das im Code bedeutet:

- KI-Output wird **nie** ohne explizite Bestätigung einer Pflegekraft Teil der Pflegedokumentation. Kein Auto-Save, kein Default-Akzept.
- Pflegekräfte entwerfen Pflegeplanungen — KI prüft auf gesetzliche Vollständigkeit. Nicht umgekehrt (Template ausfüllen).
- Reflexion ist Pflicht-Funktion, nicht Beiwerk: nach jeder Schicht 60 Sekunden Sprache zu "Was lief gut, was nicht".
- Pflegekräfte stimmen über Features ab, die als nächstes gebaut werden. Ihre Stimme zählt im Roadmap-Scoring.
- Wissens-Wiki ist peer-curated — kein Manager schreibt Anleitungen, Pflegekräfte schreiben sie.
- KI macht **keine Vorgesetzten-Beobachtung**. Reflexionen, Lernpunkte und Skill-Daten gehören der Pflegekraft, nicht der Einrichtung.

**Schnelltest:** Spart das Feature einer Pflegekraft 10 Minuten Doku — oder gibt es ihr Gestaltungsmacht über ihre Arbeit? Beides ist gut, aber wenn nur Ersteres: Feature ist Effizienz, nicht Empowerment. Bewusst kennzeichnen.

---

## 3. Offenheit

**Die Community trägt Ideen und Gesetzeswissen bei.**

Was das im Code bedeutet:

- Jede Person kann Ideen und juristische Dokumente einreichen (pflegeos.de/contribute).
- Eingereichte Beiträge werden vom täglichen Agenten gelesen, klassifiziert und beantwortet — keine Einreichung verschwindet.
- Bei Ablehnung wird die Begründung öffentlich dokumentiert.
- Akzeptierte Beiträge werden im CHANGELOG namentlich verdankt (mit Einwilligung des Einsenders).
- Roadmap ist öffentlich. Was die KI als nächstes bauen wird, ist transparent.
- Code ist Open Source (Lizenz TBD, voraussichtlich AGPL-3.0).
- Tägliches Update auf LinkedIn/X ist verpflichtend — nicht Marketing, sondern Rechenschaft.

**Schnelltest:** Könnte eine Pflegekraft aus einer fremden Einrichtung heute Abend einen Beitrag schicken, der morgen im Code landet? Wenn nicht: Offenheit ist verletzt.

---

## Konflikte zwischen den Säulen

Wenn Säulen miteinander kollidieren — was selten, aber vorkommt — gilt:

1. **Personenzentrierung** schlägt alles. Auch Empowerment der Pflegekraft, auch Community-Wünsche.
2. **Empowerment** schlägt Offenheit. Pflegekräfte überschreiben Community-Vorschläge, die ihrer Arbeit widersprechen.
3. **Offenheit** ist das Fundament, aber das schwächste Veto.

Beispiel: Community wünscht sich "Bewohner-Tracking per GPS-Armband, um Weglaufen zu verhindern." → Verstößt gegen Personenzentrierung (Würde, Freiheit). → Wird mit öffentlicher Begründung abgelehnt.

---

## Was diese Software NICHT sein wird

- Keine Überwachungssoftware für Pflegekräfte.
- Kein Effizienz-Maximierungstool, das menschliche Zuwendung wegrationalisiert.
- Kein Werkzeug, das Bewohnerautonomie aus Sicherheitsgründen einschränkt.
- Keine geschlossene Plattform, die Daten in eine US-Cloud schiebt.
- Kein "KI-Pflegeassistent", der Pflegekräfte ersetzen soll. KI ersetzt Doku-Last, nicht Menschen.

---

*Diese Datei ändert sich nur durch bewusste Entscheidung — nicht durch das tägliche Build. Der Agent darf sie zitieren, aber nicht eigenständig editieren.*
