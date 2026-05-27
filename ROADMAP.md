# Roadmap

> Lebende Datei. Der tägliche Agent wählt aus offenen Items das mit dem höchsten Score.
>
> **Score-Formel:** `(PZ × 3) + (EMP × 3) + (COM × 2) + (EFF × 1) − (KOM × 2)`
>
> Skalen: 0 = irrelevant, 5 = maximal. PZ = Personenzentrierung, EMP = Empowerment, COM = Compliance, EFF = Effizienz, KOM = Komplexität.

Status-Legende: ⏳ offen · 🔨 in Arbeit · ✅ fertig · ⛔ blockiert · ❌ verworfen

---

## Phase 1 — Fundament (Wochen 1–4)

Ziel: Lauffähiges System mit Bewohner-Profil (inkl. Biografie), Login, Community-Pipeline und Reflexions-Tool.

| Status | Feature | PZ | EMP | COM | EFF | KOM | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| ⏳ | Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte) | 5 | 1 | 3 | 1 | 2 | **21** |
| ⏳ | Reflexions-Tool (60-Sek-Sprache nach Schicht, lokal Whisper) | 2 | 5 | 0 | 0 | 3 | **15** |
| ⏳ | Login + Rollen (Bewohner, Pflegekraft, Leitung, Angehörige) + Audit-Log | 1 | 2 | 5 | 0 | 3 | **13** |
| ⏳ | Community-Contribute-Seite (pflegeos.de) live | 2 | 5 | 1 | 0 | 3 | **17** |
| ⏳ | Public Roadmap-Tracker (autogeneriert aus dieser Datei) | 1 | 1 | 0 | 1 | 1 | **5** |
| ⏳ | Stamm-Datenbankschema + Migrations-Setup | 0 | 0 | 4 | 0 | 2 | **4** |

## Phase 2 — Kollaborative Pflegeplanung (Wochen 5–10)

Ziel: Das Herzstück. Pflegeplan-Canvas mit vier Stimmen.

| Status | Feature | PZ | EMP | COM | EFF | KOM | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| ⏳ | Pflegeplan-Canvas Grundgerüst (4 Rollen, Versionen, Audit) | 5 | 5 | 4 | 2 | 4 | **32** |
| ⏳ | Bewohner-Sprachinterface (Whisper lokal, große Schrift, geduldig) | 5 | 2 | 2 | 1 | 3 | **20** |
| ⏳ | Angehörigen-Portal mit Einwilligungs-Workflow | 4 | 3 | 5 | 1 | 3 | **26** |
| ⏳ | "Tochter-Ich vs. Mutter-Wille" Zwei-Spalten-Eingabe | 5 | 3 | 5 | 0 | 2 | **30** |
| ⏳ | KI als sichtbare vierte Stimme (Vorschläge mit Quelle, abnehmbar) | 4 | 5 | 3 | 2 | 4 | **27** |
| ⏳ | Konflikt-Visualisierung (zeigt Spannungen, löst sie nicht auf) | 5 | 4 | 5 | 0 | 3 | **31** |
| ⏳ | Konsens-Bestätigung (Sprachaufnahme oder Signatur) | 5 | 3 | 5 | 0 | 3 | **28** |
| ⏳ | SIS-Themenfeld-Vollständigkeitscheck | 2 | 2 | 5 | 2 | 2 | **20** |
| ⏳ | Konsensgespräch-Workflow: Audio hochladen → strukturieren → bestätigen | 3 | 5 | 3 | 3 | 4 | **25** |

## Phase 3 — Gemeinschaftswissen (Wochen 11–18)

Ziel: Pflegekräfte werden Wissens-Eigentümer; semantische Suche über Verläufe.

| Status | Feature | PZ | EMP | COM | EFF | KOM | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| ⏳ | Pflegelabor (eigene Ideen testen, 4 Wochen, bewerten, übernehmen) | 4 | 5 | 2 | 1 | 4 | **24** |
| ⏳ | Wissens-Wiki Peer-Curated | 3 | 5 | 1 | 2 | 3 | **22** |
| ⏳ | pgvector + Semantische Suche über Biografien + Verläufe | 4 | 4 | 1 | 3 | 4 | **21** |
| ⏳ | Feature-Voting für Pflegekräfte (interne Roadmap-Stimmen) | 1 | 5 | 0 | 1 | 2 | **15** |
| ⏳ | Übergabe-Co-Pilot (Pflegekraft spricht → KI strukturiert → Pflegekraft bestätigt) | 3 | 5 | 3 | 4 | 3 | **28** |
| ⏳ | Anomalie-Erkennung (z. B. Gewichtsverlust-Trend) — als Vorschlag, nie Alarm | 4 | 3 | 2 | 3 | 4 | **20** |

## Phase 4 — Öffnung & Verbindung (Wochen 19–28)

Ziel: Familien-Portal, MDK-Export, Erinnerungsalbum.

| Status | Feature | PZ | EMP | COM | EFF | KOM | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| ⏳ | Familien-Portal (Updates, Erinnerungsalbum, Video-Calls) | 5 | 2 | 2 | 1 | 4 | **18** |
| ⏳ | Erinnerungsalbum mit Audio-Memoires | 5 | 1 | 0 | 1 | 3 | **13** |
| ⏳ | MDK-Audit-Export (automatisch nach Prüfschema) | 1 | 3 | 5 | 4 | 4 | **18** |
| ⏳ | Wunsch-Tracker (Wünsche werden nie vergessen, Sozialdienst sucht Wege) | 5 | 2 | 0 | 1 | 2 | **18** |
| ⏳ | Stimmungs-Check Bewohner (Emoji + Sprache, niedrigschwellig) | 5 | 1 | 0 | 1 | 2 | **15** |

## Phase 5 — Reife & Skalierung (Wochen 29+)

| Status | Feature | PZ | EMP | COM | EFF | KOM | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| ⏳ | Dienstplanung mit KI-Optimierung (KI schlägt vor, Team entscheidet) | 1 | 5 | 3 | 5 | 5 | **17** |
| ⏳ | Medikationsmanagement (AMWSL-konform) | 2 | 3 | 5 | 3 | 5 | **18** |
| ⏳ | Multi-Mandant (mehrere Einrichtungen) | 0 | 1 | 3 | 2 | 5 | **1** |
| ⏳ | Mobile App (offline-fähig, PWA-Erweiterung) | 2 | 3 | 1 | 3 | 4 | **12** |

---

## Cross-Cutting (laufend, nicht phasenspezifisch)

- ⏳ Monatlicher Legal-Audit (Cron, eigener Agent, eigenes Budget)
- ⏳ Tägliches Public Update (LinkedIn + X)
- ⏳ Barrierefreiheits-Audit (WCAG 2.1 AA) jede Woche
- ⏳ DSGVO-Verzeichnis (Verarbeitungstätigkeiten) automatisch aktuell halten

---

## Verworfene Ideen (für Transparenz)

*Noch keine. Dieser Abschnitt wächst mit der Zeit. Jede verworfene Idee braucht Begründung mit Bezug auf `PRINCIPLES.md`.*
