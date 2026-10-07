// Theme toggle, as on shaykas.com. The choice is stored per site, so the subdomain keeps its own.
(function () {
  var root = document.documentElement, btn = document.querySelector(".theme"), meta = document.querySelector('meta[name="theme-color"]');
  if (!btn) return;
  function apply(t, save) {
    root.dataset.theme = t;
    var dark = t === "dark";
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    btn.title = dark ? "Light mode" : "Dark mode";
    if (meta) meta.content = dark ? "#151412" : "#f6f2e6";
    if (save) try { localStorage.setItem("theme", t); } catch (e) {}
  }
  apply(root.dataset.theme === "dark" ? "dark" : "light");
  btn.addEventListener("click", function () { apply(root.dataset.theme === "dark" ? "light" : "dark", true); });
})();
