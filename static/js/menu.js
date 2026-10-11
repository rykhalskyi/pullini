// Account dropdown in the header: toggles the panel and closes it on an outside
// click or Escape. Uses data attributes so it is inert when no menu is present.
(function () {
  "use strict";

  function close(menu) {
    var button = menu.querySelector("[data-menu-button]");
    var panel = menu.querySelector("[data-menu-panel]");
    if (panel) panel.classList.add("hidden");
    if (button) button.setAttribute("aria-expanded", "false");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-menu]").forEach(function (menu) {
      var button = menu.querySelector("[data-menu-button]");
      var panel = menu.querySelector("[data-menu-panel]");
      if (!button || !panel) return;

      button.addEventListener("click", function (event) {
        event.stopPropagation();
        var isHidden = panel.classList.toggle("hidden");
        button.setAttribute("aria-expanded", isHidden ? "false" : "true");
      });

      panel.addEventListener("click", function (event) {
        event.stopPropagation();
      });

      document.addEventListener("click", function () {
        close(menu);
      });

      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") close(menu);
      });
    });
  });
})();
