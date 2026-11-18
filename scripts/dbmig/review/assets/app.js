// dbmig review: table filters and live reload (no remote resources, no data sent anywhere).
(function () {
  "use strict";
  function rowsOf(id) { var t = document.getElementById(id); return t ? t.tBodies[0].rows : []; }
  function apply(id) {
    var q = (document.querySelector('[data-filter="' + id + '"]') || {}).value || "";
    var st = (document.querySelector('[data-status="' + id + '"]') || {}).value || "";
    q = q.toLowerCase();
    Array.prototype.forEach.call(rowsOf(id), function (tr) {
      var text = tr.textContent.toLowerCase();
      var okQ = !q || text.indexOf(q) >= 0;
      var okS = !st || Array.prototype.some.call(tr.querySelectorAll(".b"), function (b) {
        return b.textContent === st;
      });
      tr.classList.toggle("hide", !(okQ && okS));
    });
  }
  document.querySelectorAll("[data-filter]").forEach(function (el) {
    el.addEventListener("input", function () { apply(el.getAttribute("data-filter")); });
  });
  document.querySelectorAll("[data-status]").forEach(function (el) {
    el.addEventListener("change", function () { apply(el.getAttribute("data-status")); });
  });
  var failed = document.querySelector("[data-failed-only]");
  var blockFilter = document.querySelector("[data-filter-blocks]");
  function blocks() {
    var only = failed && failed.checked;
    var q = blockFilter ? blockFilter.value.toLowerCase() : "";
    document.querySelectorAll(".test").forEach(function (b) {
      var show = (!only || b.getAttribute("data-failed") === "1") &&
        (!q || b.querySelector("h3").textContent.toLowerCase().indexOf(q) >= 0);
      b.classList.toggle("hide", !show);
    });
  }
  if (failed) failed.addEventListener("change", blocks);
  if (blockFilter) blockFilter.addEventListener("input", blocks);
  // Live reload only when served by `./dbmig review --serve` (loopback).
  if (location.protocol === "http:" && (location.hostname === "127.0.0.1" || location.hostname === "localhost")) {
    var root = document.querySelector('link[rel="stylesheet"]').getAttribute("href").replace("assets/app.css", "");
    var last = null;
    setInterval(function () {
      fetch(root + "version.txt", { cache: "no-store" }).then(function (r) { return r.text(); }).then(function (v) {
        if (last && v !== last) location.reload();
        last = v;
      }).catch(function () {});
    }, 2000);
  }
})();
