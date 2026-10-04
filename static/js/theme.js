// Light/dark theme toggle. The initial class is set inline in <head> to avoid
// a flash; this file only wires up the toggle buttons.
(function () {
  "use strict";

  function applyTheme(dark) {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch (error) {
      /* storage unavailable; ignore */
    }
    document.dispatchEvent(new CustomEvent("themechange", { detail: { dark: dark } }));
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        applyTheme(!document.documentElement.classList.contains("dark"));
      });
    });
  });
})();
