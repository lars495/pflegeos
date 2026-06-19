// Formular-Einreichung → Vercel Serverless Function → GitHub Issue → Hermes antwortet.
// Kein Backend auf Hetzner nötig, kein Mixed-Content-Problem.

(function () {
  var form   = document.getElementById('contribute-form');
  var status = document.getElementById('form-status');
  if (!form) return;

  function setStatus(msg, kind) {
    status.innerHTML = msg;
    status.className = kind || '';
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    setStatus('Wird gesendet…', '');

    var fd = new FormData(form);
    var payload = {
      type:              fd.get('type'),
      title:             (fd.get('title')          || '').trim(),
      body:              (fd.get('body')            || '').trim(),
      submitter_name:    (fd.get('submitter_name')  || '').trim() || null,
      submitter_email:   (fd.get('submitter_email') || '').trim() || null,
      consent_to_credit:  fd.get('consent_to_credit')  === 'on',
      consent_to_contact: fd.get('consent_to_contact') === 'on',
    };

    var btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    try {
      var r = await fetch('/api/contribute', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      });

      var data = await r.json().catch(function () { return {}; });

      if (r.status === 202 || r.ok) {
        var msg = data.message || 'Danke! Dein Beitrag wurde gespeichert und wird in den nächsten 24 Stunden bearbeitet.';
        if (data.issue_url) {
          msg += ' <a href="' + data.issue_url + '" target="_blank" rel="noopener">'
               + 'Status auf GitHub verfolgen →</a>';
        }
        setStatus(msg, 'ok');
        form.reset();
      } else if (r.status === 429) {
        setStatus('Bitte etwas später erneut versuchen — Tageslimit erreicht.', 'error');
      } else {
        setStatus(data.error || ('Fehler ' + r.status + ' — bitte später erneut versuchen.'), 'error');
      }
    } catch (err) {
      setStatus('Verbindungsfehler: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
    }
  });
})();
