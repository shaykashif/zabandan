// Zabandan reader. The whole poem sits in one framed page; tapping a word opens a card
// beside it with the word's meaning in that couplet, any cultural context or double
// meaning that translation loses, and the couplet's translation. On wide screens a gold
// branch grows from the word to the card; on narrow screens the card slides up from the
// bottom. Data comes from the JSON in #poem-data.
(function () {
  var D = JSON.parse(document.getElementById("poem-data").textContent);
  var page = document.getElementById("poem");
  var layout = document.getElementById("layout");
  var aside = document.getElementById("aside");
  var svg = document.getElementById("branch");
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var wide = matchMedia("(min-width: 960px)");
  var NS = "http://www.w3.org/2000/svg";
  var order = [];          // every word button in reading order, for arrow-key navigation
  var current = null;      // { c, u, btn }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function ur(tag, cls, text) {
    var e = el(tag, (cls ? cls + " " : "") + "ur", text);
    e.lang = "ur";
    return e;
  }
  var STAR = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M9 9h14v14H9z"/><path d="M16 6.1L25.9 16L16 25.9L6.1 16z"/></svg>';

  // ── The poem ───────────────────────────────────────────
  D.blocks.forEach(function (c, ci) {
    if (D.form === "nazm" && ci > 0 && c.stanza !== D.blocks[ci - 1].stanza) {
      var br = el("div", "stanza-break");
      br.innerHTML = STAR;
      br.setAttribute("role", "separator");
      page.append(br);
    }
    c.byId = {};
    c.phrasesOf = {};
    c.notesOf = {};
    c.btns = {};
    c.units.forEach(function (u) { c.byId[u.id] = u; c.phrasesOf[u.id] = []; c.notesOf[u.id] = []; });
    (c.phrases || []).forEach(function (p) { (p.units || []).forEach(function (id) { if (c.phrasesOf[id]) c.phrasesOf[id].push(p); }); });
    (c.context_notes || []).forEach(function (n) { n.units.forEach(function (id) { if (c.notesOf[id]) c.notesOf[id].push(n); }); });

    var sec = el("section", "couplet");
    sec.id = "c" + (ci + 1);
    sec.setAttribute("aria-label", "Couplet " + (ci + 1));
    sec.append(el("span", "c-num", String(ci + 1)));
    c.words.forEach(function (_, li) {
      var p = el("p", "line-ur");
      p.lang = "ur";
      c.units.filter(function (u) { return u.line === li; })
        .sort(function (a, b) { return a.start - b.start; })
        .forEach(function (u, k) {
          if (k) p.append(" ");
          var b = el("button", "u", u.ur);
          b.type = "button";
          b.setAttribute("aria-label", u.ur + ", " + u.roman);
          b.setAttribute("aria-expanded", "false");
          if (c.notesOf[u.id].length) b.classList.add("noted");
          b.addEventListener("click", function () {
            if (current && current.btn === b) close(); else open(c, u, b);
          });
          c.btns[u.id] = b;
          order.push({ c: c, u: u, btn: b });
          p.append(b);
        });
      sec.append(p);
      var rp = el("p", "line-roman", (c.roman || [])[li] || "");
      rp.lang = "ur-Latn";
      sec.append(rp, el("p", "line-en", (c.poetic || [])[li] || ""));
    });
    page.append(sec);
  });

  // ── The translation column ─────────────────────────────
  // On wide screens the space beside the poem carries each line's translation, level with its
  // Urdu line: the poetic English, with the word-for-word English in grey beneath it. Tapping a
  // word-for-word English word opens the card for its Urdu word. (On narrow screens the poetic
  // line sits under the Urdu instead, and the word-for-word stays in the card.)
  var sideLines = [];
  D.blocks.forEach(function (c, ci) {
    var urLines = page.querySelectorAll("#c" + (ci + 1) + " .line-ur");
    c.words.forEach(function (_, li) {
      var box = el("div", "side-line");
      box.append(el("p", "sl-poetic", (c.poetic || [])[li] || ""));
      var lit = el("p", "sl-literal");
      ((c.literal || [])[li] || []).forEach(function (s, k) {
        if (k) lit.append(" ");
        var sp = el("span", "seg", s.text), us = s.units || [];
        if (us.length) {
          sp.classList.add("linked");
          sp.addEventListener("click", function (e) {
            e.stopPropagation();
            var t = c.byId[us[0]];
            if (t) open(c, t, c.btns[t.id], true);
          });
        }
        lit.append(sp);
      });
      box.append(lit);
      aside.append(box);
      if (urLines[li]) sideLines.push({ el: box, line: urLines[li] });
    });
  });
  // Centre each translation on its Urdu line; if one would run into the one above (a long
  // translation, or Roman lines switched off), push it down just enough to clear it.
  function alignLiterals() {
    if (!wide.matches) return;
    var top = aside.getBoundingClientRect().top, floor = 0;
    sideLines.forEach(function (l) {
      var r = l.line.getBoundingClientRect(), h = l.el.offsetHeight;
      var y = Math.max(Math.round(r.top - top + (r.height - h) / 2), floor);
      l.el.style.top = y + "px";
      floor = y + h + 10;
    });
  }

  // ── The card ───────────────────────────────────────────
  var card = el("div", "card");
  card.hidden = true;
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-label", "Translation");
  aside.append(card);

  function fill(c, u) {
    card.textContent = "";
    var x = el("button", "close", "×");
    x.type = "button";
    x.setAttribute("aria-label", "Close translation");
    x.addEventListener("click", function () { var b = current && current.btn; close(); if (b) b.focus(); });
    card.append(x);

    var head = el("div", "card-word");
    head.append(ur("span", "cw-ur", u.ur), el("span", "cw-roman", u.roman));
    card.append(head);
    card.append(el("p", "cw-gloss", u.gloss));
    if (u.base) card.append(el("p", "cw-base", "Usual sense: " + u.base));

    c.phrasesOf[u.id].forEach(function (p) {
      var words = p.units.map(function (id) { return c.byId[id]; }).filter(Boolean)
        .sort(function (a, b) { return a.line - b.line || a.start - b.start; });
      var box = el("p", "cw-phrase");
      box.append(ur("span", null, words.map(function (w) { return w.ur; }).join(" … ")),
        " " + words.map(function (w) { return w.roman; }).join(" … ") + ": " + p.gloss);
      card.append(box);
    });

    c.notesOf[u.id].forEach(function (n) {
      var box = el("div", "cw-note");
      box.append(el("span", "cw-note-kind", n.kind.charAt(0).toUpperCase() + n.kind.slice(1)), el("p", null, n.text));
      card.append(box);
    });

    var tr = el("div", "card-couplet");
    var label = "Couplet " + (D.blocks.indexOf(c) + 1);
    if (D.form === "nazm") label += " · stanza " + (c.stanza + 1);
    tr.append(el("span", "cc-label", label));
    var related = {};
    c.phrasesOf[u.id].forEach(function (p) { p.units.forEach(function (id) { related[id] = true; }); });
    var lit = el("div", "cc-literal");
    (c.literal || []).forEach(function (line) {
      var p = el("p");
      (line || []).forEach(function (s, k) {
        if (k) p.append(" ");
        var sp = el("span", "seg", s.text), us = s.units || [];
        if (us.indexOf(u.id) >= 0) sp.classList.add("sel");
        else if (us.some(function (id) { return related[id]; })) sp.classList.add("rel");
        if (us.length) {
          sp.classList.add("linked");
          sp.tabIndex = 0;
          sp.setAttribute("role", "button");
          var go = function () { var t = c.byId[us[0]]; if (t) open(c, t, c.btns[t.id], true); };
          sp.addEventListener("click", go);
          sp.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
        }
        p.append(sp);
      });
      lit.append(p);
    });
    tr.append(el("span", "cc-sub", "Word for word"), lit);
    card.append(tr);
  }

  // ── Opening, placing and the branch ────────────────────
  function rel(r, base) { return { left: r.left - base.left, top: r.top - base.top, right: r.right - base.left, bottom: r.bottom - base.top, width: r.width, height: r.height }; }

  function place(animate) {
    if (!current) return;
    if (!wide.matches) { svg.textContent = ""; card.style.top = ""; return; }
    var base = layout.getBoundingClientRect();
    var w = rel(current.btn.getBoundingClientRect(), base);
    var a = rel(aside.getBoundingClientRect(), base);
    var h = card.offsetHeight;
    var top = Math.max(0, Math.min(w.top - 18, layout.offsetHeight - h));
    card.style.top = (top - a.top) + "px";

    // Branch: from just under the word, down a little, then across to the card's edge.
    var sx = w.left + w.width / 2, sy = w.top + w.height * 0.8;
    var ex = a.left - 6, ey = top + 34;
    svg.setAttribute("viewBox", "0 0 " + base.width + " " + base.height);
    svg.setAttribute("width", base.width);
    svg.setAttribute("height", base.height);
    svg.textContent = "";
    var path = document.createElementNS(NS, "path");
    path.setAttribute("d", "M" + sx + " " + sy + " C " + sx + " " + (sy + 34) + ", " + (ex - 90) + " " + ey + ", " + ex + " " + ey);
    path.setAttribute("class", "b-main");
    svg.append(path);
    var len = path.getTotalLength();

    // A small twig off the branch, two thirds of the way along, curling upward.
    var p0 = path.getPointAtLength(len * 0.66);
    var twig = document.createElementNS(NS, "path");
    twig.setAttribute("d", "M" + p0.x + " " + p0.y + " q 4 -10 14 -13");
    twig.setAttribute("class", "b-twig");
    svg.append(twig);
    var bud = document.createElementNS(NS, "circle");
    bud.setAttribute("cx", sx); bud.setAttribute("cy", sy); bud.setAttribute("r", 2.4);
    bud.setAttribute("class", "b-bud");
    svg.append(bud);

    if (animate && !reduce) {
      path.style.strokeDasharray = len;
      path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 420, easing: "cubic-bezier(.3,.6,.3,1)", fill: "both" });
      twig.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, delay: 300, fill: "both" });
      bud.animate([{ transform: "scale(0)", transformOrigin: sx + "px " + sy + "px" }, { transform: "scale(1)", transformOrigin: sx + "px " + sy + "px" }], { duration: 180, fill: "both" });
    }
  }

  function open(c, u, btn, fromCard) {
    if (current) {
      current.btn.classList.remove("sel");
      current.btn.setAttribute("aria-expanded", "false");
      Object.keys(current.c.btns).forEach(function (id) { current.c.btns[id].classList.remove("rel"); });
    }
    current = { c: c, u: u, btn: btn };
    btn.classList.add("sel");
    btn.setAttribute("aria-expanded", "true");
    // The other words of the expression this word belongs to get a lighter highlight.
    c.phrasesOf[u.id].forEach(function (p) { p.units.forEach(function (id) { if (id !== u.id && c.btns[id]) c.btns[id].classList.add("rel"); }); });

    var wasHidden = card.hidden;
    fill(c, u);
    card.hidden = false;
    document.body.classList.add("card-open");
    place(true);
    if (!reduce) {
      // On a wide screen the card fades in as the branch reaches it.
      if (wasHidden) card.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, delay: wide.matches ? 220 : 0, easing: "ease-out", fill: "backwards" });
    }
    if (fromCard) btn.focus({ preventScroll: true });
  }

  function close() {
    if (!current) return;
    current.btn.classList.remove("sel");
    current.btn.setAttribute("aria-expanded", "false");
    Object.keys(current.c.btns).forEach(function (id) { current.c.btns[id].classList.remove("rel"); });
    current = null;
    document.body.classList.remove("card-open");
    if (reduce) { card.hidden = true; svg.textContent = ""; return; }
    var main = svg.querySelector(".b-main");
    if (main) {
      var len = main.getTotalLength();
      main.style.strokeDasharray = len;
      main.animate([{ strokeDashoffset: 0 }, { strokeDashoffset: len }], { duration: 300, delay: 120, easing: "ease-in", fill: "both" });
      svg.querySelectorAll(".b-twig,.b-bud").forEach(function (n) { n.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: "both" }); });
    }
    card.hidden = true;
    setTimeout(function () { if (!current) svg.textContent = ""; }, 440);
  }

  // Keyboard: Escape closes; the left and right arrows step through the words in reading
  // order (Urdu runs right to left, so left is the next word).
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && current) { var b = current.btn; close(); b.focus(); return; }
    if (!current || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    if (document.activeElement && document.activeElement.tagName === "INPUT") return;
    var i = order.findIndex(function (o) { return o.btn === current.btn; });
    var j = i + (e.key === "ArrowLeft" ? 1 : -1);
    if (j < 0 || j >= order.length) return;
    e.preventDefault();
    open(order[j].c, order[j].u, order[j].btn);
    order[j].btn.focus();
  });
  // Clicking the empty page closes the card.
  document.addEventListener("click", function (e) {
    if (current && !card.contains(e.target) && !e.target.closest(".u") && !e.target.closest(".tgl") && !e.target.closest(".seg.linked")) close();
  });
  function relayout() { alignLiterals(); place(false); }
  addEventListener("resize", relayout);
  wide.addEventListener("change", relayout);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(relayout);

  // Roman, English and literal-column toggles, remembered per visitor where storage is available.
  [["t-roman", "no-roman"], ["t-english", "no-english"], ["t-literal", "no-literal"]].forEach(function (pair) {
    var t = document.getElementById(pair[0]), key = "zabandan." + pair[1], off = false;
    if (!t) return;
    try { off = localStorage.getItem(key) === "1"; } catch (e) {}
    function apply() { document.body.classList.toggle(pair[1], off); t.setAttribute("aria-pressed", String(!off)); relayout(); }
    t.addEventListener("click", function () { off = !off; apply(); try { localStorage.setItem(key, off ? "1" : "0"); } catch (e) {} });
    apply();
  });

  if (location.hash && document.querySelector(location.hash)) document.querySelector(location.hash).scrollIntoView();
})();
