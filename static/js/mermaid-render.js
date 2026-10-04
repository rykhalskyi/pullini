// Renders Mermaid diagram blocks in generated wiki content.
//
// The diagram source is untrusted (it comes from third-party repositories), so
// Mermaid runs in "strict" security mode, which escapes labels and disables
// interactive callbacks. Rendering is scoped to the wiki container so it can
// never reach the rest of the application. This script is only loaded on pages
// that actually contain a diagram.
(function () {
  "use strict";

  var SELECTOR = ".wiki-content .mermaid";
  var sources = new WeakMap();

  function currentTheme() {
    return document.documentElement.classList.contains("dark") ? "dark" : "neutral";
  }

  function diagramNodes() {
    return Array.prototype.slice.call(document.querySelectorAll(SELECTOR));
  }

  function render(nodes) {
    if (!nodes.length || typeof window.mermaid === "undefined") {
      return;
    }
    nodes.forEach(function (node) {
      if (!sources.has(node)) {
        sources.set(node, node.textContent);
      }
    });
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: currentTheme(),
      fontFamily: "inherit",
    });
    var result = window.mermaid.run({ nodes: nodes });
    if (result && typeof result.catch === "function") {
      // Per-diagram errors render an error graphic; swallow the rejected promise.
      result.catch(function () {});
    }
  }

  function renderAll() {
    render(diagramNodes());
  }

  function rerender() {
    diagramNodes().forEach(function (node) {
      var source = sources.get(node);
      if (source === undefined) {
        return;
      }
      node.removeAttribute("data-processed");
      node.textContent = source;
    });
    renderAll();
  }

  document.addEventListener("themechange", rerender);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll);
  } else {
    renderAll();
  }
})();
