/* INH Verified hub: optional filters layered on a server-rendered table.
   Without this script the table is complete and the filter bar stays hidden.
   Options are read from the rows themselves, so the script never holds a value. */
(function () {
  var hub = document.querySelector('[data-inhv="hub"]');
  if (!hub) return;
  var bar = hub.querySelector('[data-inhv="filters"]');
  var rows = Array.prototype.slice.call(hub.querySelectorAll('[data-inhv="table"] tbody tr'));
  var status = hub.querySelector('[data-inhv="filter-status"]');
  if (!bar || !rows.length) return;
  var keys = ['heat', 'cap', 'brand'];
  var selects = {};
  keys.forEach(function (k) {
    var sel = bar.querySelector('[data-filter="' + k + '"]');
    selects[k] = sel;
    var seen = {};
    rows.forEach(function (r) { var v = r.getAttribute('data-' + k); if (v) seen[v] = true; });
    Object.keys(seen).sort(function (a, b) { return a.localeCompare(b, undefined, { numeric: true }); })
      .forEach(function (v) {
        var o = document.createElement('option');
        o.value = v;
        o.textContent = k === 'heat' ? v.charAt(0).toUpperCase() + v.slice(1) : v;
        sel.appendChild(o);
      });
    sel.addEventListener('change', apply);
  });
  function apply() {
    var shown = 0;
    rows.forEach(function (r) {
      var match = keys.every(function (k) { var v = selects[k].value; return !v || r.getAttribute('data-' + k) === v; });
      r.hidden = !match;
      if (match) shown++;
    });
    status.textContent = 'Showing ' + shown + ' of ' + rows.length + ' models.';
  }
  bar.hidden = false;
})();
