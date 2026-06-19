// Vercel Serverless Function — erstellt GitHub Issue aus Formular-Einreichung.
// Läuft auf Vercel (kein Hetzner nötig, kein Mixed-Content-Problem).
// Hermes liest die Issues täglich via process_contributions.py und antwortet direkt.

const REPO = 'lars495/pflegeos';
const GITHUB_API = 'https://api.github.com';

const TYPE_EMOJI = { idea: '💡', legal: '📄', bug: '⚠️' };
const TYPE_NAME  = { idea: 'Idee oder Wunsch', legal: 'Gesetz, Standard oder Verordnung', bug: 'Problem oder Kritik' };

module.exports = async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.setHeader('Allow', 'POST');
    return res.status(200).end();
  }
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Nur POST erlaubt' });
  }

  const {
    type,
    title,
    body,
    source_url,
    submitter_name,
    submitter_email,
    consent_to_credit,
    consent_to_contact,
  } = req.body || {};

  // ── Validierung ──────────────────────────────────────────────────────────
  if (!type || !['idea', 'legal', 'bug'].includes(type)) {
    return res.status(400).json({ error: 'Ungültiger Beitrags-Typ (idea | legal | bug)' });
  }
  const t = String(title || '').trim();
  if (t.length < 5 || t.length > 200) {
    return res.status(400).json({ error: 'Titel: 5–200 Zeichen erforderlich' });
  }
  const b = String(body || '').trim();
  if (b.length < 20 || b.length > 10000) {
    return res.status(400).json({ error: 'Beschreibung: 20–10.000 Zeichen erforderlich' });
  }
  if (/\b\d{10,}\b/.test(t + b)) {
    return res.status(400).json({ error: 'Bitte keine Telefonnummern oder langen Ziffernfolgen einreichen' });
  }

  const token = process.env.GITHUB_FEEDBACK_TOKEN;
  if (!token) {
    return res.status(503).json({
      error: 'Feedback-Kanal noch nicht konfiguriert — bitte schreib direkt an lars@innovation-pflegen.de',
    });
  }

  // ── Issue-Text aufbauen ──────────────────────────────────────────────────
  let issueBody = `**Typ:** ${TYPE_EMOJI[type]} ${TYPE_NAME[type]}\n\n${b}`;

  const src = String(source_url || '').trim();
  if (src) {
    issueBody += `\n\n**Quelle / Link:** ${src}`;
  }

  const name  = String(submitter_name || '').trim();
  const email = String(submitter_email || '').trim();
  if (name || email) {
    issueBody += '\n\n---\n\n**Eingereicht von:** ';
    if (name && consent_to_credit) issueBody += name;
    else if (name) issueBody += '*(anonym auf Wunsch der Einreichenden)*';
    if (email && consent_to_contact) issueBody += ` · ${email}`;
  }

  issueBody += [
    '',
    '',
    '---',
    '',
    '*Eingereicht über [pflegeos.vercel.app](https://pflegeos.vercel.app)*',
    '*Hermes liest und beantwortet Community-Issues täglich.*',
  ].join('\n');

  // ── GitHub Issue erstellen ───────────────────────────────────────────────
  let ghRes;
  try {
    ghRes = await fetch(`${GITHUB_API}/repos/${REPO}/issues`, {
      method: 'POST',
      headers: {
        Authorization:          `Bearer ${token}`,
        Accept:                 'application/vnd.github+json',
        'Content-Type':         'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent':           'PflegeOS-Feedback/1.0',
      },
      body: JSON.stringify({
        title:  `[Community] ${t}`,
        body:   issueBody,
        labels: ['community-feedback', `type:${type}`],
      }),
    });
  } catch (err) {
    console.error('[contribute] GitHub fetch error:', err.message);
    return res.status(502).json({ error: 'Verbindungsfehler — bitte später erneut versuchen' });
  }

  // Falls Labels noch nicht existieren → ohne Labels erneut versuchen
  if (ghRes.status === 422) {
    console.warn('[contribute] Labels existieren noch nicht — erstelle Issue ohne Labels');
    ghRes = await fetch(`${GITHUB_API}/repos/${REPO}/issues`, {
      method: 'POST',
      headers: {
        Authorization:          `Bearer ${token}`,
        Accept:                 'application/vnd.github+json',
        'Content-Type':         'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent':           'PflegeOS-Feedback/1.0',
      },
      body: JSON.stringify({ title: `[Community] ${t}`, body: issueBody }),
    });
  }

  if (!ghRes.ok) {
    const txt = await ghRes.text().catch(() => '');
    console.error(`[contribute] GitHub API ${ghRes.status}:`, txt.slice(0, 300));
    return res.status(502).json({ error: 'Beitrag konnte nicht gespeichert werden — bitte später versuchen' });
  }

  const issue = await ghRes.json();
  console.log(`[contribute] Issue #${issue.number} erstellt: ${issue.html_url}`);

  return res.status(202).json({
    id:          `#${issue.number}`,
    received_at: new Date().toISOString(),
    message:     `Danke für deinen Beitrag! Hermes liest ihn täglich und antwortet direkt auf GitHub Issue #${issue.number}. Du kannst den Status hier verfolgen:`,
    issue_url:   issue.html_url,
  });
};
