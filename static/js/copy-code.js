// Adds a "Copy" button to every code block in generated wiki content.
(function () {
  "use strict";

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand("copy");
        resolve();
      } catch (error) {
        reject(error);
      } finally {
        document.body.removeChild(area);
      }
    });
  }

  function addButton(pre) {
    var code = pre.querySelector("code");
    if (!code || pre.querySelector(".copy-code-button")) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code-button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code to clipboard");

    button.addEventListener("click", function () {
      copyText(code.innerText).then(
        function () {
          button.textContent = "Copied";
          button.classList.add("is-copied");
        },
        function () {
          button.textContent = "Failed";
        }
      );
      window.setTimeout(function () {
        button.textContent = "Copy";
        button.classList.remove("is-copied");
      }, 1500);
    });

    pre.appendChild(button);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".wiki-content pre").forEach(addButton);
  });
})();
