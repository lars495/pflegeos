// Formular-Einreichung → Vercel Serverless Function → GitHub Issue → Hermes antwortet.

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
    var sourceUrl = (fd.get('source_url') || '').trim();

    var payload = {
      type:              fd.get('type'),
      title:             (fd.get('title')          || '').trim(),
      body:              (fd.get('body')            || '').trim(),
      source_url:        sourceUrl || null,
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
        // Pflegende sehen keine GitHub-Sprache — nur eine warme Bestätigung
        var msg = '✓ Danke! Hermes hat deinen Beitrag erhalten und antwortet in den nächsten 24 Stunden.';
        if (data.issue_url) {
          msg += ' <a href="' + data.issue_url + '" target="_blank" rel="noopener" style="font-size:.9em">'
               + 'Beitrag &amp; Antwort ansehen →</a>';
        }
        setStatus(msg, 'ok');
        form.reset();
      } else if (r.status === 429) {
        setStatus('Bitte etwas später erneut versuchen.', 'error');
      } else {
        setStatus(data.error || 'Etwas hat nicht geklappt — bitte später erneut versuchen.', 'error');
      }
    } catch (err) {
      setStatus('Verbindungsfehler — bitte Seite neu laden und nochmal versuchen.', 'error');
    } finally {
      btn.disabled = false;
    }
  });
})();
