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
  var MIN_SCALE = 0.25;
  var MAX_SCALE = 8;
  var sources = new WeakMap();
  var views = new WeakMap();

  function currentTheme() {
    return document.documentElement.classList.contains("dark") ? "dark" : "neutral";
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function applyTransform(view) {
    view.node.style.transform =
      "translate(" + view.x + "px, " + view.y + "px) scale(" + view.scale + ")";
  }

  // Zoom around a point given in viewport coordinates, keeping that point fixed.
  function zoomAt(view, x, y, factor) {
    var scale = clamp(view.scale * factor, MIN_SCALE, MAX_SCALE);
    if (scale === view.scale) {
      return;
    }
    var contentX = (x - view.x) / view.scale;
    var contentY = (y - view.y) / view.scale;
    view.scale = scale;
    view.x = x - contentX * scale;
    view.y = y - contentY * scale;
    applyTransform(view);
  }

  function zoomCenter(view, factor) {
    zoomAt(view, view.viewport.clientWidth / 2, view.viewport.clientHeight / 2, factor);
  }

  function resetView(view) {
    var width = view.viewport.clientWidth;
    view.scale = 1;
    view.x = view.width < width ? (width - view.width) / 2 : 0;
    view.y = 0;
    applyTransform(view);
  }

  function fitView(view) {
    var width = view.viewport.clientWidth;
    var height = view.viewport.clientHeight;
    if (!width || !height || !view.width || !view.height) {
      return;
    }
    view.scale = clamp(Math.min(width / view.width, height / view.height, 1), MIN_SCALE, MAX_SCALE);
    view.x = (width - view.width * view.scale) / 2;
    view.y = (height - view.height * view.scale) / 2;
    applyTransform(view);
  }

  // Give the SVG its natural (viewBox) size so Mermaid no longer shrinks large
  // diagrams to fit the article width.
  function measure(view) {
    var svg = view.node.querySelector("svg");
    if (!svg) {
      view.svg = null;
      return false;
    }
    view.svg = svg;
    var box = svg.viewBox && svg.viewBox.baseVal;
    var width = box && box.width ? box.width : svg.getBoundingClientRect().width;
    var height = box && box.height ? box.height : svg.getBoundingClientRect().height;
    if (!width || !height) {
      return false;
    }
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    svg.style.width = width + "px";
    svg.style.height = height + "px";
    svg.style.maxWidth = "none";
    view.width = width;
    view.height = height;
    return true;
  }

  function bindView(view) {
    var viewport = view.viewport;
    var toolbar = view.toolbar;

    toolbar.addEventListener("click", function (event) {
      var button = event.target.closest("[data-mermaid-zoom]");
      if (!button) {
        return;
      }
      var action = button.getAttribute("data-mermaid-zoom");
      if (action === "in") {
        zoomCenter(view, 1.25);
      } else if (action === "out") {
        zoomCenter(view, 0.8);
      } else if (action === "reset") {
        resetView(view);
      } else if (action === "fit") {
        fitView(view);
      }
    });

    // Ctrl/Cmd + wheel (and trackpad pinch) zooms the chart without zooming the page.
    viewport.addEventListener(
      "wheel",
      function (event) {
        if (!event.ctrlKey && !event.metaKey) {
          return;
        }
        event.preventDefault();
        var delta = event.deltaY;
        if (event.deltaMode === 1) {
          delta *= 16;
        } else if (event.deltaMode === 2) {
          delta *= 100;
        }
        var rect = viewport.getBoundingClientRect();
        zoomAt(
          view,
          event.clientX - rect.left,
          event.clientY - rect.top,
          clamp(Math.exp(-delta * 0.002), 0.5, 2)
        );
      },
      { passive: false }
    );

    var dragging = false;
    var pointerId = null;
    var startX = 0;
    var startY = 0;
    var originX = 0;
    var originY = 0;

    viewport.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) {
        return;
      }
      dragging = true;
      pointerId = event.pointerId;
      startX = event.clientX;
      startY = event.clientY;
      originX = view.x;
      originY = view.y;
      viewport.setPointerCapture(pointerId);
      viewport.classList.add("is-dragging");
      event.preventDefault();
    });

    viewport.addEventListener("pointermove", function (event) {
      if (!dragging || event.pointerId !== pointerId) {
        return;
      }
      view.x = originX + event.clientX - startX;
      view.y = originY + event.clientY - startY;
      applyTransform(view);
    });

    function endDrag(event) {
      if (!dragging || event.pointerId !== pointerId) {
        return;
      }
      dragging = false;
      pointerId = null;
      viewport.classList.remove("is-dragging");
    }

    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", endDrag);
  }

  function zoomButton(action, label, title) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "mermaid-zoom-button";
    button.setAttribute("data-mermaid-zoom", action);
    button.setAttribute("aria-label", title);
    button.setAttribute("title", title);
    button.textContent = label;
    return button;
  }

  function ensureView(node) {
    var view = views.get(node);
    if (view) {
      return view;
    }

    var wrapper = document.createElement("div");
    wrapper.className = "mermaid-zoom";

    var toolbar = document.createElement("div");
    toolbar.className = "mermaid-zoom-toolbar";
    toolbar.appendChild(zoomButton("out", "\u2212", "Zoom out"));
    toolbar.appendChild(zoomButton("reset", "1:1", "Actual size"));
    toolbar.appendChild(zoomButton("in", "+", "Zoom in"));
    toolbar.appendChild(zoomButton("fit", "Fit", "Fit diagram in view"));

    var viewport = document.createElement("div");
    viewport.className = "mermaid-zoom-viewport";
    viewport.setAttribute("title", "Drag to pan. Ctrl/Cmd + scroll to zoom.");

    var canvas = document.createElement("div");
    canvas.className = "mermaid-zoom-canvas";

    node.parentNode.insertBefore(wrapper, node);
    canvas.appendChild(node);
    viewport.appendChild(canvas);
    wrapper.appendChild(toolbar);
    wrapper.appendChild(viewport);

    view = {
      node: node,
      wrapper: wrapper,
      toolbar: toolbar,
      viewport: viewport,
      canvas: canvas,
      svg: null,
      width: 0,
      height: 0,
      scale: 1,
      x: 0,
      y: 0,
    };
    views.set(node, view);
    bindView(view);
    return view;
  }

  function enhance(nodes) {
    nodes.forEach(function (node) {
      if (!node.querySelector("svg")) {
        return;
      }
      var view = ensureView(node);
      if (measure(view)) {
        resetView(view);
      }
    });
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
    if (result && typeof result.then === "function") {
      // Per-diagram errors render an error graphic; still enhance what did render.
      result.then(
        function () {
          enhance(nodes);
        },
        function () {
          enhance(nodes);
        }
      );
    } else {
      enhance(nodes);
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
