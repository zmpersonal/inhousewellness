/* True Total Cost — the page. Reads INHCost for every number; decides none.
 *
 * This file renders states. It does not compute money, it does not default a
 * missing value into a displayed one, and it never writes a figure the core did
 * not return. Where the core returns `amount: null` with a `why`, the page
 * prints the `why` — an omission a reader can read is the product here, not a
 * blemish on it.
 */
(function () {
  "use strict";

  function money(n) {
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2,
                                             maximumFractionDigits: 2 });
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text !== undefined && text !== null) { e.textContent = text; }
    return e;
  }
  /* A number typed into a box is a string until it is proved otherwise. An empty
   * box is ABSENT, not zero — `Number("") === 0` is exactly the missing-value
   * bug this project keeps finding, and it would put a free electrician into a
   * five-year total. */
  function readNumber(input) {
    if (!input) { return null; }
    var raw = String(input.value).replace(/[$,\s]/g, "");
    if (raw === "") { return null; }
    var n = Number(raw);
    if (!isFinite(n) || n < 0) { return null; }
    return n;
  }

  function provenance(line) {
    var bits = [];
    if (line.source) { bits.push(line.source); }
    if (line.fetched_at) { bits.push("fetched " + String(line.fetched_at).slice(0, 10)); }
    if (line.note) { bits.push(line.note); }
    return bits.join(" · ");
  }

  function init(root) {
    var tablesUrl = root.getAttribute("data-tables");
    var zipUrl = root.getAttribute("data-zip");
    var collectionUrl = root.getAttribute("data-collection");
    var out = root.querySelector("[data-region=out]");

    Promise.all([fetch(tablesUrl).then(function (r) { return r.json(); }),
                 fetch(zipUrl).then(function (r) { return r.json(); })])
      .then(function (both) { ready(root, both[0], both[1], collectionUrl); })
      .catch(function (err) {
        /* A failed asset load is said out loud. Rendering an empty calculator
         * would look like a catalogue with nothing in it. */
        out.textContent = "";
        out.appendChild(el("p", "ttc-gap",
          "The cost tables did not load, so nothing is computed here. " +
          "Reload, or read the figures on the methodology page. (" + err + ")"));
      });
  }

  function ready(root, tables, zipTable, collectionUrl) {
    var C = window.INHCost;
    var f = {
      model: root.querySelector("[name=model]"),
      price: root.querySelector("[name=manual_price]"),
      zip: root.querySelector("[name=zip]"),
      io: root.querySelector("[name=io]"),
      circuit: root.querySelector("[name=circuit]"),
      sessions: root.querySelector("[name=sessions]"),
      minutes: root.querySelector("[name=minutes]"),
      kw: root.querySelector("[name=reader_kw]"),
      decline: root.querySelector("[name=decline_kw]"),
      electrical: root.querySelector("[name=electrical]"),
      foundation: root.querySelector("[name=foundation]"),
      maintenance: root.querySelector("[name=maintenance]")
    };
    var byHandle = {};
    tables.products.forEach(function (p) {
      byHandle[p.h] = p;
      var o = el("option", null, p.t + (p.kw.v === null ? "" : "  —  " + p.kw.v + " kW"));
      o.value = p.h;
      f.model.appendChild(o);
    });
    root.querySelectorAll("[data-freight]").forEach(function (b) {
      b.addEventListener("change", render);
    });
    Object.keys(f).forEach(function (k) {
      if (f[k]) { f[k].addEventListener("input", render); f[k].addEventListener("change", render); }
    });

    function gather() {
      var input = C.defaults(tables);
      var handle = f.model.value;
      input.product = Object.prototype.hasOwnProperty.call(byHandle, handle)
                    ? byHandle[handle] : null;
      input.manualPrice = readNumber(f.price);
      input.zip = f.zip.value;
      var picked = root.querySelector("[data-freight]:checked");
      input.freightTier = picked ? picked.value : null;
      var s = readNumber(f.sessions);
      if (s !== null && s > 0) { input.sessionsPerWeek = s; }
      var m = readNumber(f.minutes);
      if (m !== null && m > 0) { input.sessionMinutes = m; }
      input.readerKw = readNumber(f.kw);
      input.declinedKw = f.decline.checked === true;
      input.electricalQuote = readNumber(f.electrical);
      input.foundationCost = readNumber(f.foundation);
      input.maintenancePerYear = readNumber(f.maintenance);
      return input;
    }

    function render() {
      var input = gather();
      var r = C.compute(input, tables, zipTable);
      var out = root.querySelector("[data-region=out]");
      out.textContent = "";

      out.appendChild(zipBanner(r, tables));
      if (r.power.state === "invite") { out.appendChild(invite(input, r)); }
      if (r.power.state === "reader") { out.appendChild(readerKwNote(r)); }
      out.appendChild(circuitNote(input, f.circuit.value));

      var table = el("table", "ttc-lines");
      var tb = el("tbody");
      r.lines.forEach(function (line) { tb.appendChild(lineRow(line)); });
      table.appendChild(tb);
      out.appendChild(table);

      out.appendChild(totals(r));
      if (r.excluded.length > 0) { out.appendChild(exclusions(r)); }
      if (collectionUrl) {
        var p = el("p", "ttc-cta");
        var a = el("a", null, "Browse every sauna in this table");
        a.href = collectionUrl;
        p.appendChild(a);
        out.appendChild(p);
      }
    }

    function lineRow(line) {
      var tr = el("tr", "ttc-line ttc-" + line.state);
      tr.setAttribute("data-line", line.id);
      tr.setAttribute("data-state", line.state);
      tr.appendChild(el("th", null, line.label));
      var td = el("td", "ttc-amount");
      if (line.amount === null) {
        td.appendChild(el("span", "ttc-absent", "not included"));
      } else {
        td.appendChild(el("span", "ttc-figure", money(line.amount)));
      }
      tr.appendChild(td);
      var note = el("td", "ttc-note");
      if (line.amount === null) {
        note.appendChild(el("span", "ttc-why", line.why));
      } else {
        note.appendChild(el("span", "ttc-prov", provenance(line)));
      }
      if (line.id === "running" && line.state === "computed") {
        note.appendChild(el("div", "ttc-sub",
          line.kw + " kW × " + (line.kwh_per_year / (line.kw)).toFixed(1)
          + " h/yr = " + line.kwh_per_year + " kWh at " + line.rate_cents
          + "¢/kWh (" + line.us_state + ") · " + money(line.per_session)
          + " a session"));
      }
      tr.appendChild(note);
      return tr;
    }

    function zipBanner(r, tables) {
      var z = r.zip;
      if (z.status === "ok") {
        var p = el("p", "ttc-zip-ok",
          z.zip + " resolves to " + z.state + ", where the EIA residential rate is "
          + C.rateFor(z.state, tables) + "¢/kWh (period "
          + tables.energy.latest_period + ").");
        return p;
      }
      if (z.status === "malformed" && z.zip === "") {
        return el("p", "ttc-zip-empty", "Enter a ZIP and the running cost line fills in.");
      }
      var g = el("div", "ttc-gap");
      g.setAttribute("data-state", "zip_gap");
      g.appendChild(el("strong", null, "No electricity rate for " + (z.zip || "that ZIP") + "."));
      g.appendChild(el("p", null, z.reason));
      g.appendChild(el("p", null,
        "We do not substitute the national average. It is 18.34¢/kWh and it is "
        + "not your rate — using it here would be a made-up local number wearing "
        + "a federal source's clothes. Everything that does not depend on your "
        + "rate is still computed below."));
      return g;
    }

    function invite(input, r) {
      var d = el("div", "ttc-invite");
      d.setAttribute("data-state", "invite");
      d.appendChild(el("strong", null, "This manufacturer does not publish a rated power."));
      d.appendChild(el("p", null,
        "We read 142 manuals, 3,569 pages, to try to find it. 90 of them state "
        + "what to wire and never what the unit draws. So we do not have a kW "
        + "for this model, and neither does anyone else selling it."));
      d.appendChild(el("p", null,
        "It is usually on the spec plate inside the cabin or on the first page "
        + "of the manual. Type it in and the running cost computes — the same "
        + "way the electrician's quote does."));
      if (r.power.manual) {
        var a = el("a", "ttc-manual", "Open this model's manual");
        a.href = r.power.manual;
        a.rel = "nofollow";
        d.appendChild(a);
      }
      return d;
    }

    function readerKwNote(r) {
      var d = el("div", "ttc-reader-kw");
      d.setAttribute("data-state", "reader_kw");
      d.appendChild(el("strong", null, "Running cost below uses YOUR figure, not ours."));
      d.appendChild(el("p", null,
        r.power.kw + " kW, as you entered it. Our catalogue has no rating for "
        + "this model, so nothing here is checking your number — it is labelled "
        + "reader-supplied everywhere it appears."));
      return d;
    }

    function circuitNote(input, circuit) {
      var d = el("div", "ttc-circuit");
      var p = input.product;
      var needs = [];
      if (p !== null) {
        if (p.volts && p.volts.v !== null) { needs.push(p.volts.v + "V"); }
        if (p.amps && p.amps.v !== null) { needs.push(p.amps.v + "A"); }
      }
      var what = needs.length > 0
        ? "This model states " + needs.join(" / ") + "."
        : "Our sources do not state the circuit this model needs.";
      if (circuit === "yes") {
        d.appendChild(el("p", null, what + " You say the circuit is already there, "
          + "so there may be nothing to pay. We still do not put a number on it: "
          + "whether an existing circuit is the right one is your electrician's call."));
      } else if (circuit === "no") {
        d.appendChild(el("p", null, what + " A new circuit is an electrician's "
          + "quote, and we do not publish a figure for it. Enter theirs below."));
      } else {
        d.appendChild(el("p", null, what + " Until you know, the electrical line "
          + "stays out of the total. No midpoint, no range."));
      }
      return d;
    }

    function totals(r) {
      var d = el("div", "ttc-total");
      d.setAttribute("data-state", r.complete ? "complete" : "partial");
      var h = el("p", "ttc-total-head",
        (r.complete ? "Five-year total" : "Five-year total, of what is known"));
      d.appendChild(h);
      var big = el("p", "ttc-total-figure", money(r.five_year_usd));
      big.setAttribute("data-value", String(r.five_year_usd));
      d.appendChild(big);
      var per = el("p", "ttc-per-session",
        money(r.cost_per_session_usd) + " a session"
        + (r.complete ? "" : ", of what is known") + ", over "
        + r.sessions_over_five_years + " sessions in five years");
      per.setAttribute("data-value", String(r.cost_per_session_usd));
      d.appendChild(per);
      /* Never "$0.00 a year". A zero the reader can see is a claim that nothing
       * recurs; when no recurring figure is known at all, say that instead. */
      var basis = r.per_year_usd === null
        ? money(r.one_off_usd) + " once. Nothing recurring is known — both the "
          + "running cost and the maintenance line are left out below."
        : money(r.one_off_usd) + " once, plus " + money(r.per_year_usd)
          + " a year for " + r.years + " years"
          + (r.recurring_lines_known < r.recurring_lines_total
             ? ", counting only the recurring lines that have a figure." : ".");
      d.appendChild(el("p", "ttc-total-basis", basis));
      return d;
    }

    function exclusions(r) {
      var d = el("div", "ttc-excluded");
      d.setAttribute("data-state", "exclusions");
      d.appendChild(el("strong", null, "What this total leaves out, and why"));
      var ul = el("ul");
      r.excluded.forEach(function (e) {
        var li = el("li");
        li.setAttribute("data-excluded", e.id);
        li.appendChild(el("b", null, e.label + ": "));
        li.appendChild(document.createTextNode(e.why));
        ul.appendChild(li);
      });
      d.appendChild(ul);
      return d;
    }

    render();
    root.setAttribute("data-ready", "true");
  }

  document.querySelectorAll("[data-inh-ttc]").forEach(init);
})();
