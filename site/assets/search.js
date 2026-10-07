// Zabandan index search. Matches titles, poets and form, and the full text of every poem:
// Urdu script, Roman transliteration and English translations. Roman matching ignores
// diacritics and common spelling variants, so "khwahish" finds "ḳhvāhish".
(function () {
  var input = document.getElementById("q");
  var count = document.getElementById("count");
  var empty = document.getElementById("empty");
  var rows = Array.from(document.querySelectorAll("#entries li"));
  var INDEX = JSON.parse(document.getElementById("search-data").textContent);
  var byId = {};
  INDEX.forEach(function (p) { byId[p.id] = p; });

  // Latin: lowercase, strip diacritics, smooth spelling variants of Roman Urdu.
  function foldLatin(s) {
    return s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
      .replace(/['’`.]/g, "").replace(/-/g, " ").replace(/w/g, "v").replace(/ee/g, "i").replace(/oo/g, "u")
      .replace(/aa/g, "a").replace(/ii/g, "i").replace(/uu/g, "u").replace(/\s+/g, " ").trim();
  }
  // Urdu: drop vowel marks and zero-width characters, unify Arabic and Persian letter forms.
  function foldUrdu(s) {
    return s.replace(/[\u064B-\u065F\u0670\u06D4\u200C-\u200F]/g, "")
      .replace(/[يى]/g, "ی").replace(/ك/g, "ک").replace(/[ةه]/g, "ہ").replace(/ۂ/g, "ہ").replace(/ۓ/g, "ے")
      .replace(/\s+/g, " ").trim();
  }
  var hasUrdu = function (s) { return /[؀-ۿ]/.test(s); };

  // Pre-fold each poem's searchable lines once.
  INDEX.forEach(function (p) {
    p.folded = p.lines.map(function (l) { return hasUrdu(l.text) ? foldUrdu(l.text) : foldLatin(l.text); });
    p.head = foldLatin(p.meta) + " " + foldUrdu(p.meta_ur);
  });

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  // Highlight the query in the original line when it matches directly; otherwise show the line plain.
  function snippet(text, raw) {
    var i = text.toLowerCase().indexOf(raw.toLowerCase());
    if (i < 0) return escapeHtml(text);
    return escapeHtml(text.slice(0, i)) + "<mark>" + escapeHtml(text.slice(i, i + raw.length)) + "</mark>" + escapeHtml(text.slice(i + raw.length));
  }

  function run() {
    var raw = input.value.trim();
    var urduQ = hasUrdu(raw);
    var q = urduQ ? foldUrdu(raw) : foldLatin(raw);
    var shown = 0;
    rows.forEach(function (li) {
      var p = byId[li.dataset.id], hit = li.querySelector(".hit");
      if (!q) { li.hidden = false; hit.hidden = true; shown++; return; }
      var inHead = p.head.indexOf(q) >= 0;
      // Prefer a line where the query starts a word; fall back to a match inside a word.
      var line = -1, k;
      for (k = 0; k < p.folded.length && line < 0; k++) if ((" " + p.folded[k]).indexOf(" " + q) >= 0) line = k;
      for (k = 0; k < p.folded.length && line < 0; k++) if (p.folded[k].indexOf(q) >= 0) line = k;
      li.hidden = !(inHead || line >= 0);
      if (!li.hidden) shown++;
      if (line >= 0 && !inHead) {
        var l = p.lines[line];
        hit.innerHTML = '<span class="where">' + escapeHtml(l.where) + ":</span> " +
          (hasUrdu(l.text) ? '<span class="ur" lang="ur">' + snippet(l.text, raw) + "</span>" : snippet(l.text, raw));
        hit.hidden = false;
      } else hit.hidden = true;
    });
    count.textContent = q ? shown + " of " + rows.length + (rows.length === 1 ? " poem" : " poems")
                          : rows.length + (rows.length === 1 ? " poem" : " poems");
    empty.hidden = shown > 0;
  }

  input.addEventListener("input", run);
  var params = new URLSearchParams(location.search);
  if (params.get("q")) input.value = params.get("q");
  run();
})();
