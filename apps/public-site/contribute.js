// Minimal Contribute Form Submission
// Posts to /v1/contribute on the API.

(function () {
  const API_BASE = (window.PFLEGEOS_API || "").trim();
  const form = document.getElementById("contribute-form");
  const status = document.getElementById("form-status");
  if (!form) return;

  // Day-0-Hinweis: Backend ist noch nicht live.
  if (!API_BASE) {
    const banner = document.createElement("p");
    banner.className = "error";
    banner.style.marginTop = "0";
    banner.textContent =
      "ℹ️ Das Backend ist noch nicht online. Du kannst das Formular trotzdem ausfüllen — sobald wir live sind, kommt es an. Bis dahin: gerne per Mail an lars@innovation-pflegen.de.";
    form.parentNode.insertBefore(banner, form);
  }

  function setStatus(msg, kind) {
    status.textContent = msg;
    status.className = kind || "";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus("Wird gesendet…", "");

    const fd = new FormData(form);
    const payload = {
      type: fd.get("type"),
      title: (fd.get("title") || "").toString().trim(),
      body: (fd.get("body") || "").toString().trim(),
      submitter_name: (fd.get("submitter_name") || "").toString().trim() || null,
      submitter_email: (fd.get("submitter_email") || "").toString().trim() || null,
      consent_to_credit: fd.get("consent_to_credit") === "on",
      consent_to_contact: fd.get("consent_to_contact") === "on",
    };

    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;

    if (!API_BASE) {
      setStatus(
        "Backend ist noch nicht live. Bitte sende deinen Beitrag vorerst an lars@innovation-pflegen.de — danke!",
        "error"
      );
      button.disabled = false;
      return;
    }

    try {
      const r = await fetch(`${API_BASE}/v1/contribute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (r.status === 202 || r.ok) {
        const data = await r.json();
        setStatus(
          data.message ||
            "Danke! Dein Beitrag wurde gespeichert und wird in den nächsten 24 Stunden bearbeitet.",
          "ok"
        );
        form.reset();
      } else if (r.status === 429) {
        setStatus("Bitte versuche es später erneut — Tageslimit erreicht.", "error");
      } else {
        const txt = await r.text();
        setStatus(`Fehler ${r.status}: ${txt.slice(0, 200)}`, "error");
      }
    } catch (err) {
      setStatus(`Verbindungsfehler: ${err.message}`, "error");
    } finally {
      button.disabled = false;
    }
  });
})();
