# Learnings — Was dieses Experiment herausfindet

> PflegeOS ist ein Experiment: Kann eine KI mit offenen Modellen und maximal
> 1 € pro Tag eine personenzentrierte Pflegesoftware bauen? Diese Datei ist
> das Erkenntnis-Log — chronologisch, ehrlich, auch die Fehlschläge.
> **Gerade die Fehlschläge.**
>
> Denn die eigentliche Botschaft dieses Projekts ist: *So würde man ein
> echtes Produkt nicht entwickeln.* Was ein echtes Produkt anders bräuchte,
> sammeln wir am Ende dieser Datei.

---

## L1 · Ein Modell ohne Augen baut blind (26.05.–19.06.)

**Was passiert ist:** Der erste Build-Agent gab dem Modell die Roadmap und
sagte „bau das Feature mit dem höchsten Score". Ein einziger LLM-Aufruf,
keine Möglichkeit, bestehende Dateien zu lesen. Ergebnis: **24 Läufe,
0 Features.** Der generierte Code referenzierte Module, die es nie gab,
und Importe, die nie stimmen konnten.

**Erkenntnis:** Code-Generierung ohne Lesezugriff auf den bestehenden Code
ist strukturell zum Scheitern verurteilt — unabhängig von der Modellgröße.
Ein Mensch, der eine Datei schreiben soll, ohne das Projekt öffnen zu
dürfen, würde genauso scheitern.

## L2 · Infrastruktur-Fehler tarnen sich als Modell-Schwäche (Juni)

**Was passiert ist:** Wochenlang lautete die Diagnose „das Modell ist zu
schwach". Tatsächlich schrieb der Agent seine Dateien auf den Host, aber
die Tests liefen in einem Docker-Container **ohne Zugriff auf diese
Dateien**. Selbst perfekter Code wäre jeden Tag verworfen worden. Das
Test-Verzeichnis war nicht einmal im Container-Image enthalten.

**Erkenntnis:** In autonomen Systemen sind Umgebungsfehler von
Fähigkeitsfehlern äußerlich nicht zu unterscheiden. Wer die Fehlerlogs
nicht liest, zieht die bequeme Schlussfolgerung („KI zu dumm") statt der
richtigen („Testumgebung kaputt"). Das passierte uns — den Betreibern —
über Wochen.

## L3 · Stille Fehler brauchen einen Totmannschalter (20.06.–07.07.)

**Was passiert ist:** Der Agent konnte 18 Tage lang seine Ergebnisse nicht
zu GitHub pushen (ein Push-Fehler wurde im Code verschluckt, jeder Folgetag
staute sich dahinter). **Niemand bemerkte es.** Von außen sah das Projekt
tot aus; intern lief es jede Nacht brav weiter.

**Erkenntnis:** Ein autonomes System braucht eine Instanz, die bemerkt,
wenn es verstummt. Seit 07.07. prüft ein täglicher Heartbeat, ob der
Tagesbericht erschienen ist, und schlägt sonst öffentlich Alarm
(GitHub-Issue + Mail). Der Ausfall wäre damit nach 24 Stunden aufgefallen
statt nach 18 Tagen.

## L4 · Das Spezifikations-Paradox (07.07.)

**Was passiert ist:** Umstellung auf Micro-Tasks: Ein starkes Modell
(Claude) zerlegt die Roadmap in kleinste Arbeitspakete mit exakten
Feldlisten, Signaturen und — entscheidend — **fertig geschriebenen Tests**.
Das billige Modell (Hermes 4 70B) implementiert nur noch. Die Spezifikation
von T001 enthielt praktisch die komplette Lösung.

**Erkenntnis:** Um ein kleines Modell zuverlässig zu machen, muss man die
Aufgabe so präzise beschreiben, dass die Beschreibung fast die Arbeit ist.
Die Denk-/Tipp-Verteilung liegt bei etwa **95 % teures Modell, 5 % billiges
Modell**. Das „1-€-Wunder" ist also ehrlicherweise ein Arbeitsteilungs-Wunder
— die Intelligenz steckt in der Vorbereitung. Für ein Experiment ist das
eine saubere Erkenntnis; als Produktstrategie wäre es Selbstbetrug.

## L5 · Kleine Modelle scheitern an Formaten, nicht an Logik (08.–14.07.)

**Was passiert ist:** Auch mit perfekten Tasks: drei Tage rot an T001, drei
Tage rot an T010. Ursachen: (a) wieder ein Umgebungsfehler — das
Deploy-Skript starb seit Ende Mai an einer Shell-Falle (`set -o pipefail`),
das Test-Image war 6 Wochen alt; (b) Hermes legt Markdown-Zäune
(```` ```python ````) um seinen Code, die als erste Zeile in der Datei
landeten → Syntaxfehler. Die Logik des generierten Codes war
dagegen weitgehend richtig.

**Erkenntnis:** Der Werkzeugkasten muss den Marotten kleiner Modelle
entgegenkommen (Zäune abstreifen, Syntax sofort prüfen, Fehler in klaren
Worten zurückspiegeln) statt Perfektion zu erwarten. JSON mit escaptem
Code hatten wir aus demselben Grund schon zuvor abgeschafft.

## L6 · Der erste Erfolg — und was er gekostet hat (14.07.)

**Was passiert ist:** Nach den Fixes aus L5: **T001 grün im zweiten
Versuch.** Erster Versuch rot, Fehlerprotokoll ging automatisch zurück ans
Modell, zweiter Versuch saß. Das Bewohner-Modell (Biografie, Werte, Wünsche
im Mittelpunkt) existiert jetzt — geschrieben von Hermes 4 70B für
**0,001 $**. Die Eskalationsstufe (Hermes 4 405B ab Versuch 3) hatte am
Vortag für unter 1 Cent mitgearbeitet.

**Erkenntnis:** Der Reparatur-Kreislauf (Test rot → Log ans Modell →
neuer Versuch) ist der eigentliche Hebel — nicht das erste Ergebnis.
Und: Das Tagesbudget von 1,10 $ wird zu **etwa 1 % ausgeschöpft**. Die
Budget-Grenze, um die das Experiment gebaut wurde, ist für diese
Architektur nicht bindend.

## L7 · Ein Experiment ohne Publikum ist ein Hobby (Juli)

**Was passiert ist:** Sieben Wochen lang versprach das Projekt „tägliche
öffentliche Updates" — gepostet wurde nie. Die Tagesberichte liegen im
Repo, aber niemand liest sie. Die eigenen Prinzipien (PRINCIPLES.md,
Säule 3) waren damit nach dem projekteigenen Schnelltest verletzt.

**Erkenntnis:** Rechenschaft ist keine Infrastruktur-Frage, sondern eine
Gewohnheits-Frage. Konsequenz: automatisches Mastodon-Posting (offenes
Netzwerk zu offenem Projekt) + täglich vorformulierter LinkedIn-Text für
den menschlichen Betreiber.

---

## Was ein echtes Produkt anders bräuchte

Dieses Projekt ist bewusst **kein Produkt**. Wer Pflegesoftware ernsthaft
entwickelt, müsste mindestens Folgendes anders machen — die Liste wächst
mit jedem Learning:

1. **Sicherheit vor Features.** Login, Rollen, Verschlüsselung und
   Audit-Log kämen vor dem ersten Datenmodell — nicht als „spätere Phase".
   Hier speichern Endpoints Biografien ohne jede Authentifizierung
   (vertretbar nur, weil nie echte Daten eingegeben werden dürfen).
2. **Betroffene entwerfen mit.** Pflegekräfte und Bewohner:innen gehörten
   von Woche 1 an in den Design-Prozess — nicht als spätere Feedback-Geber
   auf Fertiges. Ein Prinzipien-Dokument ersetzt keine echte Partizipation.
3. **Menschen prüfen jede Zeile.** KI-generierter Code in einem
   Medizin-nahen Kontext bräuchte systematisches menschliches Code-Review,
   Haftungsklärung und QM-Prozesse (MDR-Abgrenzung, DiGA-Fragen).
4. **Datenportabilität und Interoperabilität von Tag 1** (Export komplett
   als offenes Format; Anschluss an bestehende Systeme), sonst reproduziert
   man den Lock-in, den man etablierten Anbietern vorwirft.
5. **Betrieb ist mehr als Deployen.** Backups mit Wiederherstellungs-Tests,
   Monitoring, Incident-Prozesse, Support — der unsichtbare Teil, der in
   diesem Experiment monatelang kaputt sein konnte, ohne dass es jemandem
   schadete. Bei echten Bewohnerdaten wäre jeder dieser Ausfälle ein
   meldepflichtiger Vorfall gewesen.

---

*Dieses Log wird fortlaufend ergänzt — von den Betreibern und vom Agenten.
Korrekturen und Widerspruch ausdrücklich willkommen:
[Beitrag einreichen](https://pflegeos.vercel.app/#mitmachen).*
