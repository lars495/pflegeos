// PflegeOS Sandbox — interaktive Demo-Logik
// Keine echten Daten, kein Backend.

(function () {
  // ── Tab-Navigation ─────────────────────────────────────────
  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var tabId = this.dataset.tab;
      document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
      document.querySelectorAll(".tab-content").forEach(function (c) { c.classList.remove("active"); });
      this.classList.add("active");
      var content = document.getElementById("tab-" + tabId);
      if (content) content.classList.add("active");
    });
  });

  // ── Stimmungs-Auswahl ──────────────────────────────────────
  document.querySelectorAll(".mood-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".mood-btn").forEach(function (b) { b.classList.remove("active"); });
      this.classList.add("active");
      showToast("Stimmung gespeichert ✓ (Demo)");
    });
  });

  // ── KI-Vorschlag annehmen/ablehnen/besprechen ───────────────
  window.acceptAI = function () {
    showToast("✓ KI-Vorschlag übernommen — wird Teil des Pflegeplans.");
    document.querySelector(".ai-action-row").innerHTML =
      "<span style='color:var(--accent);font-size:.9rem'>✓ Übernommen von Pflegekraft</span>";
  };
  window.rejectAI = function () {
    showToast("✗ KI-Vorschlag abgelehnt. Begründung kann vermerkt werden.");
    document.querySelector(".ai-action-row").innerHTML =
      "<span style='color:var(--conflict);font-size:.9rem'>✗ Abgelehnt</span>";
  };
  window.discussAI = function () {
    showToast("💬 Thema wird für nächste Teambesprechung markiert.");
  };

  // ── Konflikt lösen ─────────────────────────────────────────
  window.resolveConflict = function () {
    document.querySelector(".conflict-box").innerHTML =
      "<h3 style='color:var(--accent)'>✓ Gelöst</h3>" +
      "<p>Dienstplan angepasst: Körperpflege bei Frau Bergmann ab 07:45 Uhr.</p>" +
      "<p style='font-size:.85rem;color:var(--muted)'>Dokumentiert von K. Maier, 27.05.2026</p>";
  };

  // ── Biografie ausklappen ────────────────────────────────────
  window.expandBio = function () {
    var p = document.querySelector(".profile-block.bio p");
    p.textContent +=
      " In ihrer Freizeit malte Maria aquarelle Landschaften — ihre " +
      "Bilder hängen noch heute in ihrer Wohnung, aus der Sabine einen " +
      "gerahmt mitgebracht hat. Sie spricht gerne über ihre Klassen, " +
      "erinnert sich an viele Schüler beim Namen.";
    document.querySelector(".btn-secondary").style.display = "none";
  };

  // ── Audio-Mockup ────────────────────────────────────────────
  window.playMock = function () {
    showToast("▶ (Demo) Sprachaufnahme wird lokal auf dem VPS gehört — verlässt Deutschland nicht.");
  };

  // ── Übergabe-Aufnahme ───────────────────────────────────────
  var recording = false;
  window.toggleRecording = function () {
    var micArea = document.getElementById("mic-area");
    var micLabel = document.getElementById("mic-label");
    var transcription = document.getElementById("transcription");

    if (!recording) {
      recording = true;
      micArea.classList.add("recording");
      micLabel.textContent = "⏺ Aufnahme läuft… (Demo: nochmal tippen zum Stoppen)";
    } else {
      recording = false;
      micArea.classList.remove("recording");
      micArea.style.display = "none";
      transcription.style.display = "block";
    }
  };

  window.confirmHandover = function () {
    showToast("✓ Übergabe gespeichert. Nächste Schicht kann sie lesen.");
    document.querySelector(".handover-confirm").innerHTML =
      "<span style='color:var(--accent)'>✓ Gespeichert um 14:32 Uhr · K. Maier</span>";
  };

  window.editHandover = function () {
    showToast("✏️ (Demo) Im echten System kann hier direkt editiert werden.");
  };

  // ── Reflexion speichern ─────────────────────────────────────
  window.saveReflection = function () {
    document.getElementById("reflection-insight").style.display = "block";
    showToast("💭 Reflexion gespeichert — nur für dich sichtbar.");
  };

  // ── Toast-Nachrichten ───────────────────────────────────────
  function showToast(msg) {
    var existing = document.querySelector(".sandbox-toast");
    if (existing) existing.remove();

    var toast = document.createElement("div");
    toast.className = "sandbox-toast";
    toast.textContent = msg;
    toast.style.cssText = [
      "position:fixed",
      "bottom:1.5rem",
      "left:50%",
      "transform:translateX(-50%)",
      "background:#1a1a1a",
      "color:#fff",
      "padding:.6rem 1.2rem",
      "border-radius:8px",
      "font-size:.9rem",
      "z-index:9999",
      "max-width:90vw",
      "text-align:center",
      "box-shadow:0 4px 12px rgba(0,0,0,.3)",
    ].join(";");

    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
  }

  // Link zur Sandbox von der Hauptseite aus
  var nav = document.querySelector("nav");
  if (nav && !window.location.pathname.includes("sandbox")) {
    var link = document.createElement("a");
    link.href = "/sandbox.html";
    link.textContent = "🧪 Sandbox";
    nav.appendChild(link);
  }
})();
