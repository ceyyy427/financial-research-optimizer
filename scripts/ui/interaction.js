/* Offline-only UI behavior. It filters and reveals saved artifacts; it never
 * calculates forecasts, risk, weights, or metrics in the browser. */
(function () {
  "use strict";
  var state = window.__FRO_UI_STATE__ || {};
  var message = document.querySelector("[data-ui-message]");
  function say(value) { if (message) message.textContent = value; }
  function setVisible(target) {
    document.querySelectorAll("[data-panel]").forEach(function (panel) {
      var active = target === "overview" || panel.dataset.panel === target;
      panel.hidden = !active;
      if (panel.tagName === "H2" && panel.nextElementSibling && !panel.nextElementSibling.dataset.panel) panel.nextElementSibling.hidden = !active;
    });
  }
  document.querySelectorAll("[data-tab]").forEach(function (tab) {
    tab.addEventListener("click", function () {
      state.active_tab = tab.dataset.tab;
      document.querySelectorAll("[data-tab]").forEach(function (item) { item.setAttribute("aria-selected", item === tab ? "true" : "false"); });
      setVisible(state.active_tab);
    });
  });
  function filter(field, value) {
    document.querySelectorAll("[data-" + field + "]").forEach(function (item) {
      item.hidden = value !== "all" && item.dataset[field] !== value;
    });
    state[field === "model" ? "selected_model" : "selected_source"] = value;
  }
  document.querySelectorAll("[data-ui-control]").forEach(function (control) {
    control.addEventListener("change", function () {
      var field = control.dataset.uiControl;
      if (field === "model" || field === "source") filter(field, control.value);
      else {
        state.time_range = control.value;
        var limit = control.value === "30d" ? 30 : control.value === "60d" ? 60 : control.value === "120d" ? 120 : Infinity;
        document.querySelectorAll(".chart").forEach(function (chart) {
          var marks = Array.from(chart.querySelectorAll("[data-index]"));
          var last = marks.reduce(function (value, mark) { return Math.max(value, Number(mark.dataset.index)); }, -1);
          marks.forEach(function (mark) { mark.hidden = limit !== Infinity && Number(mark.dataset.index) < Math.max(0, last - limit + 1); });
        });
        say("时间范围已筛选已保存图表标记；未重新计算指标。");
      }
    });
  });
  var themeButton = document.querySelector('[data-action="theme"]');
  if (themeButton) themeButton.addEventListener("click", function () {
    var next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    themeButton.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
    state.theme = next;
  });
  document.querySelectorAll("[data-sortable] th").forEach(function (header, index) {
    header.tabIndex = 0;
    function sort() {
      var table = header.closest("table"), body = table.tBodies[0];
      Array.from(body.rows).sort(function (a, b) { return a.cells[index].textContent.localeCompare(b.cells[index].textContent, undefined, {numeric: true}); }).forEach(function (row) { body.appendChild(row); });
      say("表格已按“" + header.textContent.trim() + "”排序；数据值未改变。");
    }
    header.addEventListener("click", sort); header.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); sort(); } });
  });
  document.querySelectorAll("[data-tooltip]").forEach(function (mark) { mark.setAttribute("tabindex", "0"); mark.addEventListener("focus", function () { say(mark.dataset.tooltip); }); mark.addEventListener("mouseenter", function () { say(mark.dataset.tooltip); }); });
  document.querySelectorAll('[data-action="scenario"]').forEach(function (button) { button.addEventListener("click", function () { say("情景重算需要通过 MCP/Python Runtime 创建新 scenario_id；原始结果不会被覆盖。"); }); });
  setVisible(state.active_tab || "overview");
})();
