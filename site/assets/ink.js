// NOT LOADED: switched off in scripts/build_site.py until the mid-animation freeze is fixed.
// Ink: when a page loads, every letter is drawn by ink tendrils, starting from blank paper.
// Fine threads grow out across the space each letter will occupy, sketching it like a web;
// the letter's own strokes fill in along them; then the outer threads withdraw and leave the
// clean letter. All the text on the page does this at once.
//
// How: SVG filters, each with two masks swept by SMIL.
//   threads: the ridges of a turbulence (two octaves, so they run on and branch), kept inside a halo round the letters whose
//            reach grows and then shrinks back to nothing; coloured from the letters.
//   strokes: the glyphs themselves, revealed where an arrival value (slow noise plus the
//            same ridges, so ink travels along the threads) has been passed by a sweep.
// Both thresholds are hard, so everything stays crisp. Four filters with different networks
// and slightly staggered starts keep neighbouring words from filling identically; each is
// removed when its text is complete, so resting text is untouched.
(function () {
  var root = document.documentElement;
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.zbInkReady = true;
  if (reduce || !root.classList.contains("js-ink")) return;

  var DUR = 1500;     // ms from blank paper to complete letters
  var START = 60;     // ms after the script runs
  var STAGGER = 140;  // the four networks start up to this far apart
  var NETWORKS = 4;

  // Everything that inks in, in one list (site.css hides the same set until it does).
  var PAGE = [
    ".top a", ".masthead h1", ".masthead .ur", ".intro p", ".search label", "#count", ".label", ".list li",
    ".poem-title", ".poem-ur", ".poem-roman", ".poem-by", ".reader-bar .hint", ".tgl", ".aside-head",
    ".page .c-num", ".page .u", ".line-roman", ".line-en", ".sl-poetic", ".sl-literal",
    ".provenance p", ".credit p", "main > p"
  ].join(",");

  function anim(attr, values, keyTimes, splines) {
    return '<animate attributeName="' + attr + '" values="' + values + '" keyTimes="' + keyTimes + '" dur="' + DUR +
      'ms" begin="indefinite" fill="freeze" calcMode="spline" keySplines="' + splines + '"/>';
  }

  function network(i) {
    var seed = 1 + Math.floor(Math.random() * 900);
    var reach = "0;7;6;0", reachT = "0;0.4;0.62;1", reachS = "0.2 0.7 0.3 1;0.4 0 0.6 1;0.5 0 0.5 1";
    return '<filter id="zb-ink-' + i + '" x="-12%" y="-50%" width="124%" height="200%" color-interpolation-filters="sRGB">' +
      // the network: thin ridges of a fine turbulence (a ridge is where it is near 0)
      '<feTurbulence type="turbulence" baseFrequency="0.06 0.075" numOctaves="2" seed="' + seed + '" result="vein"/>' +
      '<feColorMatrix in="vein" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -7 0 0 0 1" result="l0"/>' +
      '<feComponentTransfer in="l0" result="lines"><feFuncA type="linear" slope="5" intercept="-1.2"/></feComponentTransfer>' +
      // threads: the network inside a halo round the letters that grows out and back
      '<feMorphology in="SourceAlpha" operator="dilate" radius="0" result="halo">' + anim("radius", reach, reachT, reachS) + "</feMorphology>" +
      '<feComposite in="lines" in2="halo" operator="in" result="tmask"/>' +
      '<feMorphology in="SourceGraphic" operator="dilate" radius="1" result="col">' + anim("radius", "1;8;7;1", reachT, reachS) + "</feMorphology>" +
      '<feComposite in="col" in2="tmask" operator="in" result="threads"/>' +
      // strokes: arrival = slow noise + the ridges, so ink reaches the glyph along the threads
      '<feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="' + (seed + 3) + '" result="start"/>' +
      '<feComposite in="start" in2="vein" operator="arithmetic" k1="0" k2="0.55" k3="0.45" k4="0" result="mix"/>' +
      '<feColorMatrix in="mix" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1.6 0 0 0 1.25" result="early"/>' +
      '<feComponentTransfer in="early" result="smask"><feFuncA type="linear" slope="10" intercept="-10">' +
      anim("intercept", "-10;-10;1;1", "0;0.22;0.92;1", "0 0 1 1;0.3 0.1 0.4 1;0 0 1 1") + "</feFuncA></feComponentTransfer>" +
      '<feComposite in="SourceGraphic" in2="smask" operator="in" result="strokes"/>' +
      '<feMerge><feMergeNode in="threads"/><feMergeNode in="strokes"/></feMerge>' +
      "</filter>";
  }

  var svgNS = "http://www.w3.org/2000/svg";
  var host = document.createElementNS(svgNS, "svg");
  host.setAttribute("aria-hidden", "true");
  host.setAttribute("width", "0");
  host.setAttribute("height", "0");
  host.style.position = "absolute";
  var markup = "";
  for (var i = 0; i < NETWORKS; i++) markup += network(i);
  host.innerHTML = markup;
  document.body.prepend(host);

  var els = Array.from(document.querySelectorAll(PAGE)).filter(function (el) { return !el.closest(".card"); });
  els.forEach(function (el) {
    el.style.filter = "url(#zb-ink-" + Math.floor(Math.random() * NETWORKS) + ")";
    el.classList.add("ink-run");
  });
  var last = 0;
  host.querySelectorAll("filter").forEach(function (f) {
    var at = START + Math.round(Math.random() * STAGGER);
    last = Math.max(last, at);
    setTimeout(function () { f.querySelector("animate").beginElement(); }, at);
  });
  setTimeout(function () {
    els.forEach(function (el) {
      el.style.filter = "";
      el.classList.remove("ink-run");
      el.classList.add("ink-done");
    });
    host.remove();
  }, last + DUR + 60);
})();
