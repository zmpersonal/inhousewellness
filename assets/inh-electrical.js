/* Sauna electrical tool (Round 1). Data: assets/inh-electrical-data.json, built by
   scripts/electrical_build.py from the InHouse Wellness Verified Sauna Database.

   What this file may show, and nothing else:
   - what a manufacturer states, quoted verbatim with grade, source and date;
   - heater current draw, amps = kW x 1000 / volts, ONLY from a rated kW and a voltage that are
     both sourced or both typed by the reader, and always labelled as calculated;
   - each manufacturer's heater-sizing chart applied separately, never blended.
   It never computes a breaker, a wire gauge or a code minimum, never derives kW from volts x
   amps, and turns home inputs into questions, never verdicts. Same inputs, same output: nothing
   here reads the clock or a random source. */
(function () {
  "use strict";
  var root = document.querySelector('[data-inhe="tool"]');
  if (!root) return;
  document.documentElement.classList.add("inhe-js");
  var $ = function (sel) { return root.querySelector(sel); };   /* re-bound below once the sheet moves */
  var DATA = null;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /* A reader's field is a number or it is missing. "" is missing, never 0. */
  function readNum(v) {
    if (v === null || v === undefined || String(v).trim() === "") return null;
    var n = parseFloat(String(v).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  }
  /* Up to d decimals, trailing zeros dropped: 6 -> "6", 8.3 -> "8.3". Amps use toFixed(1) directly. */
  function fmt(n, d) { var s = n.toFixed(d); return s.indexOf(".") < 0 ? s : s.replace(/0+$/, "").replace(/\.$/, ""); }
  function radio(form, name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : null;
  }

  /* ---------------------------------------------------------- statements -- */
  function quoteHtml(s) {
    var q = s.quote;
    return '<span class="inhe-quote">' + (q.lead ? "…" : "") + "“" + esc(q.text) + "”" + (q.trail ? "…" : "") + "</span>";
  }
  function provHtml(s) {
    var kind = s.source_type === "manufacturer_manual" ? "manual" : "manufacturer page";
    var pg = s.page ? ", p. " + esc(s.page) : "";
    var grade = s.grade === "documented" ? "Documented" : "Listed";
    return '<span class="inhe-prov"><span class="inhv-grade">' + grade + "</span> · " +
      '<a href="' + esc(s.source_url) + '" rel="nofollow noopener" target="_blank">' + kind + pg + "</a> · verified " + esc(s.verified) + "</span>";
  }
  function stmtList(list) {
    return '<dl class="inhe-stmts">' + list.map(function (s) {
      return '<div class="inhe-stmt"><dt>' + esc(s.labels.join(" · ")) + "</dt><dd>" + quoteHtml(s) + provHtml(s) + "</dd></div>";
    }).join("") + "</dl>";
  }
  function manualLink(url) {
    return url ? ' <a href="' + esc(url) + '" rel="nofollow noopener" target="_blank">Open the manufacturer\'s manual</a>.' : "";
  }

  /* ------------------------------------------------------------- heater -- */
  /* `basis` says where the two inputs came from, in words. */
  function drawHtml(kw, volts, basis) {
    var amps = kw * 1000 / volts;
    return '<div class="inhe-stmt" data-inhe="draw"><dt>Heater current draw (calculated from rated kW and voltage)</dt><dd>' +
      '<span class="inhe-calc">' + amps.toFixed(1) + " A</span>" +
      '<span class="inhe-calc-label">' + fmt(kw, 2) + " kW × 1000 ÷ " + fmt(volts, 0) + " V. " + basis + " " +
      'This is what the heater draws, not a breaker size. <a href="/pages/sauna-electrical-methodology">How it is calculated</a></span></dd></div>';
  }
  function readerInputs() {
    var f = $('[data-inhe="electrical-form"]');
    return { kw: readNum($('[data-inhe="kw"]').value), volts: readNum(radio(f, "volts")) };
  }
  function heaterCard(m) {
    var h = m && m.heater;
    var inp = readerInputs();
    var out = '<section class="inhe-card" data-inhe="heater"><h3>Heater</h3><dl>';
    if (h) {
      out += '<div class="inhe-stmt"><dt>Rated heater power</dt><dd><span class="inhv-v">' + fmt(h.kw, 2) + " kW</span>" +
        (h.kw_quote ? quoteHtml({ quote: h.kw_quote }) : "") +
        provHtml({ grade: h.kw_grade, source_type: "", source_url: h.kw_source_url, verified: h.kw_verified, page: null }) + "</dd></div>";
      if (h.draw_amps !== null && h.draw_amps !== undefined && h.volts) {
        out += drawHtml(h.kw, h.volts, "Both inputs come from the manufacturer.");
      } else if (inp.volts !== null) {
        out += drawHtml(h.kw, inp.volts, "The rated kW is the manufacturer's; the voltage is the one you entered.");
      } else {
        out += '<div class="inhe-stmt"><dt>Heater current draw</dt><dd>The heater\'s voltage isn\'t stated in the sources we\'ve verified. ' +
          "Choose it above from the heater's spec plate or manual to see the current draw." + manualLink(m.manual_url) + "</dd></div>";
      }
    } else if (inp.kw !== null && inp.volts !== null) {
      out += drawHtml(inp.kw, inp.volts, "Both inputs are the figures you entered.");
    } else {
      out += '<div class="inhe-stmt"><dt>Rated heater power</dt><dd><span class="inhe-missing">Not stated in the sources we\'ve verified.</span> ' +
        "Read it off the heater's spec plate or the manual and enter it above, with the voltage, to see the heater's current draw." +
        (m ? manualLink(m.manual_url) : "") + " Without the rated power, the current draw can't be calculated, and it is never estimated from a similar model.</dd></div>";
    }
    return out + "</dl></section>";
  }

  /* ---------------------------------------------------------- electrical -- */
  function homeQuestions() {
    var q = [
      "Does this sauna need its own dedicated circuit, and does the manufacturer's manual call for GFCI protection?",
      "Does my main panel have the capacity for this load, and does it need a load calculation?",
      "Are there enough open breaker spaces for the circuit or circuits this sauna needs?",
      "Does this installation need a permit and an inspection where I live?"
    ];
    var panel = readNum($('[data-inhe="panel"]').value);
    var slots = readNum($('[data-inhe="slots"]').value);
    var notes = [];
    if (panel !== null) notes.push("My main panel is rated " + fmt(panel, 0) + " A. Given my existing appliances, is a load calculation needed before adding this sauna?");
    if (slots !== null) notes.push("I count " + fmt(slots, 0) + " open breaker space" + (slots === 1 ? "" : "s") + ". Is that enough for what this sauna needs?");
    /* The reader's own figures replace the generic version of the same question. */
    return notes.concat(q.filter(function (x, i) { return !((i === 1 && panel !== null) || (i === 2 && slots !== null)); }));
  }

  function selected() {
    var v = $('[data-inhe="model"]').value;
    if (!v) return { kind: "manual" };
    if (v.indexOf("p:") === 0) {
      var p = DATA.unmapped_inh_products.filter(function (x) { return x.handle === v.slice(2); })[0];
      return { kind: "unmapped", product: p };
    }
    return { kind: "model", model: DATA.models.filter(function (x) { return x.handle === v; })[0] };
  }

  function renderElectrical() {
    var sel = selected();
    var res = $('[data-inhe="result"]');
    var html = "";
    var m = sel.kind === "model" ? sel.model : null;
    if (m) {
      var circ = m.statements.filter(function (s) { return s.about_circuit; });
      /* The heater card shows the rated-power quote; it is not repeated under other values. */
      var other = m.statements.filter(function (s) {
        return !s.about_circuit && !(m.heater && s.labels.length === 1 && s.labels[0] === "Heater power");
      });
      html += '<h2 class="inhv-h2"><a href="' + esc(m.url) + '">' + esc(m.title) + "</a></h2>";
      html += '<section class="inhe-card" data-inhe="circuit"><h3>What the manufacturer states about the circuit</h3>';
      if (circ.length) {
        html += stmtList(circ);
      } else {
        html += '<p data-inhe="no-circuit">' + esc(DATA.lines.no_circuit) + manualLink(m.manual_url) + "</p>";
      }
      if (m.gap) {
        html += '<p class="inhe-note" data-inhe="gap">Our verified record doesn\'t include this model\'s circuit amperage yet. ' +
          '<a href="' + esc(m.gap.doc_url) + '" rel="nofollow noopener" target="_blank">See the manufacturer\'s manual, p. ' + esc(m.gap.page) + "</a>.</p>";
      }
      html += "</section>";
      if (other.length) html += '<section class="inhe-card" data-inhe="other"><h3>Other values the manufacturer states</h3>' + stmtList(other) + "</section>";
      if (m.heater || m.heat_type !== "infrared") html += heaterCard(m);
    } else if (sel.kind === "unmapped") {
      html += '<h2 class="inhv-h2">' + esc(sel.product.title) + "</h2>";
      html += '<section class="inhe-card" data-inhe="unmapped"><p>This sauna is sold by InHouse Wellness. ' +
        (sel.product.reason === "not_live" ? "Its record in the " + esc(DATA.db_name) + " is not published yet"
          : "It is not yet in the " + esc(DATA.db_name)) +
        ", so we have no verified manufacturer statement about its circuit to show. Check the manufacturer's installation manual; " +
        "your electrician sizes the circuit to your local code.</p>" +
        "<p>Enter the heater's rated power and voltage from its spec plate or manual above to see the heater's current draw.</p></section>";
      html += heaterCard(null);
    } else {
      var inp = readerInputs();
      if (inp.kw === null && inp.volts === null) {
        res.innerHTML = '<p class="inhe-note">Pick a sauna, or enter a heater\'s rated power and voltage.</p>';
        $('[data-inhe="sheet"]').innerHTML = "";
        return;
      }
      html += '<section class="inhe-card" data-inhe="manual"><h3>Your heater</h3><p>No model is selected, so no manufacturer statement is shown. ' +
        "Check the heater's installation manual for its circuit requirement; your electrician sizes the circuit to your local code.</p></section>";
      html += heaterCard(null);
    }
    html += '<p><button type="button" class="inhe-btn" data-inhe="print">Print the electrician sheet</button></p>';
    res.innerHTML = html;
    var pb = res.querySelector('[data-inhe="print"]');
    if (pb) pb.addEventListener("click", function () { window.print(); });
    renderSheet(sel);
  }

  function renderSheet(sel) {
    var m = sel.kind === "model" ? sel.model : null;
    var title = m ? m.title : (sel.kind === "unmapped" ? sel.product.title : "Sauna heater entered by hand");
    var h = '<h2>Electrician sheet: ' + esc(title) + "</h2><p>From InHouse Wellness, data updated " + esc(DATA.updated) +
      (m ? '. Model page: <a href="https://inhousewellness.com' + esc(m.url) + '">inhousewellness.com' + esc(m.url) + "</a>" : "") + ".</p>";
    if (m) {
      var circ = m.statements.filter(function (s) { return s.about_circuit; });
      h += "<h3>What the manufacturer states about the circuit</h3>";
      h += circ.length ? stmtList(circ) : "<p>" + esc(DATA.lines.no_circuit) + "</p>";
      if (m.manual_url) h += '<p>Manual: <a href="' + esc(m.manual_url) + '">' + esc(m.manual_url) + "</a></p>";
      var other = m.statements.filter(function (s) {
        return !s.about_circuit && !(m.heater && s.labels.length === 1 && s.labels[0] === "Heater power");
      });
      if (other.length) h += "<h3>Other values the manufacturer states</h3>" + stmtList(other);
    }
    var hc = (m && !m.heater && m.heat_type === "infrared") ? "" : heaterCard(m).replace(/<\/?section[^>]*>/g, "");
    h += hc;
    h += "<h3>Questions for your electrician</h3><ol>" + homeQuestions().map(function (q) { return "<li>" + esc(q) + "</li>"; }).join("") + "</ol>";
    h += "<p>" + esc(DATA.lines.local_code) + "</p>";
    $('[data-inhe="sheet"]').innerHTML = h;
  }

  /* -------------------------------------------------------------- sizing -- */
  var FT3_PER_M3 = 35.3147, M2_PER_FT2 = 0.09290304, M3_PER_FT3 = 0.0283168;
  var STD = [4.5, 6, 8, 9, 10.5];

  function applyChart(ch, room) {
    var notes = [];
    var vol = room.vol;
    var glassFt2 = room.glass;
    var nonIns = room.walls === "uninsulated" ? Math.max(room.wallArea, glassFt2) : glassFt2;
    var addFt3 = 0;
    if (room.walls === "log") {
      if (ch.log_walls) vol = vol * ch.log_walls.multiply_volume;
      else notes.push("This chart does not adjust for log walls.");
    }
    var area = glassFt2;
    if (room.walls === "uninsulated") {
      if (ch.uninsulated_walls && ch.uninsulated_walls.same_rule_as_glass) area = nonIns;
      else notes.push("This chart does not adjust for uninsulated walls.");
    }
    if (ch.glass && area > 0) {
      var areaU = ch.glass.area_unit === "m2" ? area * M2_PER_FT2 : area;
      var addU = areaU * ch.glass.per_area;
      addFt3 = ch.glass.volume_unit === "m3" ? addU * FT3_PER_M3 : addU;
    } else if (!ch.glass && glassFt2 > 0) {
      notes.push("This chart states no adjustment for glass.");
    }
    if (room.place === "outdoor") notes.push("This chart does not adjust for an outdoor sauna.");
    var effFt3 = vol + addFt3;
    var eff = ch.unit === "m3" ? effFt3 * M3_PER_FT3 : effFt3;
    var unitLabel = ch.unit === "m3" ? "m³" : "cu ft";
    var rows = [], text = "";
    if (ch.method === "divide_by_50_next_size") {
      var kwCalc = effFt3 / 50;
      var pick = ch.rows.filter(function (r) { return r.kw >= kwCalc - 1e-9; })[0];
      rows = pick ? [pick] : [];
      text = pick ? fmt(pick.kw, 1) + " kW" : "No heater in this chart covers this room";
      notes.unshift(fmt(effFt3, 0) + " cu ft ÷ 50 = " + fmt(kwCalc, 2) + " kW, then the next heater size up.");
    } else if (ch.method === "max_only") {
      var first = ch.rows.filter(function (r) { return r.max >= effFt3; })[0];
      rows = first ? [first] : [];
      text = first ? fmt(first.kw, 1) + " kW or larger" : "No heater in this chart covers this room";
      notes.unshift("Scandia publishes maximum room sizes only, so it sets no upper limit.");
    } else {
      rows = ch.rows.filter(function (r) { return r.min <= eff + 1e-9 && eff <= r.max + 1e-9; });
      if (rows.length) {
        var lo = rows[0].kw, hi = rows[rows.length - 1].kw;
        text = (lo === hi ? fmt(lo, 1) : fmt(lo, 1) + "–" + fmt(hi, 1)) + " kW";
      } else {
        text = "No heater in this chart covers " + fmt(eff, 1) + " " + unitLabel;
      }
    }
    return { ch: ch, eff: eff, unitLabel: unitLabel, addFt3: addFt3, rows: rows, text: text, notes: notes };
  }

  function andList(xs) { return xs.length < 2 ? xs.join("") : xs.slice(0, -1).join(", ") + " and " + xs[xs.length - 1]; }
  function stepsBetween(a, b) { return STD.filter(function (s) { return s > a + 1e-9 && s <= b + 1e-9; }).length; }

  function renderSizing() {
    var f = $('[data-inhe="sizing-form"]');
    var L = readNum($('[data-inhe="len"]').value), W = readNum($('[data-inhe="wid"]').value), H = readNum($('[data-inhe="hgt"]').value);
    var G = readNum($('[data-inhe="glass"]').value);
    var res = $('[data-inhe="result"]');
    if (L === null || W === null || H === null) {
      res.innerHTML = '<p class="inhe-note">Enter the room\'s inside length, width and height.</p>';
      $('[data-inhe="sheet"]').innerHTML = "";
      return;
    }
    var room = { vol: L * W * H, glass: G === null ? 0 : G, wallArea: 2 * (L + W) * H,
      walls: radio(f, "walls"), place: radio(f, "place") };
    var results = DATA.charts.map(function (ch) { return applyChart(ch, room); });
    var h = '<p data-inhe="volume">Room volume: ' + fmt(L, 1) + " × " + fmt(W, 1) + " × " + fmt(H, 1) + " ft = <strong>" + fmt(room.vol, 0) +
      " cu ft</strong> (" + fmt(room.vol * M3_PER_FT3, 2) + " m³).</p>";
    h += '<p class="inhe-note">Each heater maker\'s own chart, applied separately with its own rules. They are not averaged.</p>';
    h += '<ul class="inhe-charts" data-inhe="charts">' + results.map(function (r) {
      var ch = r.ch;
      var models = r.rows.map(function (x) { return esc(x.model); }).join(", ");
      return '<li class="inhe-chart" data-chart="' + esc(ch.id) + '"><strong>' + esc(ch.maker) + '</strong> <span class="inhe-chart-kw">' + esc(r.text) + "</span>" +
        (models && !ch.method ? ' <span class="inhe-note">(' + models + ")</span>" : "") +
        '<span class="inhe-prov">Room as this chart counts it: ' + fmt(r.eff, r.unitLabel === "m³" ? 2 : 0) + " " + r.unitLabel +
        '. <a href="' + esc(ch.url) + '" rel="nofollow noopener" target="_blank">' + esc(ch.document) + "</a>, " + esc(ch.table_page) + "</span>" +
        (r.notes.length ? '<span class="inhe-prov">' + r.notes.map(esc).join(" ") + "</span>" : "") + "</li>";
    }).join("") + "</ul>";
    if (room.glass > 0) {
      var byGlass = results.filter(function (r) { return r.ch.glass; }).map(function (r) { return esc(r.ch.maker) + " about " + fmt(r.addFt3, 0) + " cu ft"; });
      var none = results.filter(function (r) { return !r.ch.glass; }).map(function (r) { return esc(r.ch.maker); });
      h += '<p class="inhe-flag" data-inhe="glass-diverge">For ' + fmt(room.glass, 1) + " sq ft of glass these charts add different amounts of room volume: " +
        byGlass.join(", ") + (none.length ? "; " + andList(none) + " make no glass adjustment" : "") + ".</p>";
    }
    var ranged = results.filter(function (r) { return !r.ch.excluded_from_spread && r.rows.length; });
    if (ranged.length) {
      var lo = Math.min.apply(null, ranged.map(function (r) { return r.rows[0].kw; }));
      var hi = Math.max.apply(null, ranged.map(function (r) { return r.rows[r.rows.length - 1].kw; }));
      if (stepsBetween(lo, hi) > 1) h += '<p class="inhe-flag" data-inhe="spread">These charts differ by more than one heater size for this room.</p>';
      var matches = DATA.models.filter(function (m) { return m.heater && m.heater.kw >= lo - 1e-9 && m.heater.kw <= hi + 1e-9; });
      if (matches.length) {
        h += "<h3>Saunas in the database with a heater from " + fmt(lo, 1) + " to " + fmt(hi, 1) + " kW</h3><ul>" + matches.map(function (m) {
          return '<li><a href="/pages/sauna-electrical-requirements?model=' + encodeURIComponent(m.handle) + '">' + esc(m.title) + "</a> (" + fmt(m.heater.kw, 1) + " kW)</li>";
        }).join("") + "</ul>";
      }
    }
    res.innerHTML = h;
    $('[data-inhe="sheet"]').innerHTML = "";
  }

  /* ---------------------------------------------------------------- wiring -- */
  function mode() { return root.getAttribute("data-mode"); }
  function render() {
    if (mode() === "sizing") renderSizing(); else renderElectrical();
    $('[data-inhe="local"]').textContent = DATA.lines.local_code;
  }
  function fillPicker() {
    var sel = $('[data-inhe="model"]');
    var brands = {};
    DATA.models.forEach(function (m) { (brands[m.brand] = brands[m.brand] || []).push(m); });
    Object.keys(brands).sort().forEach(function (b) {
      var g = document.createElement("optgroup");
      g.label = b;
      brands[b].forEach(function (m) { var o = document.createElement("option"); o.value = m.handle; o.textContent = m.title; g.appendChild(o); });
      sel.appendChild(g);
    });
    if (DATA.unmapped_inh_products.length) {
      var g2 = document.createElement("optgroup");
      g2.label = "Sold by InHouse Wellness, no published database record yet";
      DATA.unmapped_inh_products.forEach(function (p) { var o = document.createElement("option"); o.value = "p:" + p.handle; o.textContent = p.title; g2.appendChild(o); });
      sel.appendChild(g2);
    }
  }
  function applyParams() {
    var u = new URLSearchParams(window.location.search);
    var model = u.get("model"), product = u.get("product");
    if (product) model = DATA.product_to_model[product] || ("p:" + product);
    if (model && $('[data-inhe="model"] option[value="' + CSS.escape(model) + '"]')) $('[data-inhe="model"]').value = model;
    if (u.get("kw")) $('[data-inhe="kw"]').value = u.get("kw");
    var v = u.get("v");
    if (v) { var r = root.querySelector('input[name="volts"][value="' + CSS.escape(v) + '"]'); if (r) r.checked = true; }
    ["len", "wid", "hgt", "glass"].forEach(function (k) { if (u.get(k)) $('[data-inhe="' + k + '"]').value = u.get(k); });
    ["walls", "place"].forEach(function (k) {
      var val = u.get(k);
      if (val) { var r = root.querySelector('input[name="' + k + '"][value="' + CSS.escape(val) + '"]'); if (r) r.checked = true; }
    });
  }

  /* The sheet lives directly under <body> so print CSS can drop everything else (see the CSS). */
  var sheetEl = root.querySelector('[data-inhe="sheet"]');
  if (sheetEl) document.body.appendChild(sheetEl);
  $ = function (sel) { return sel === '[data-inhe="sheet"]' ? sheetEl : root.querySelector(sel); };

  fetch(root.getAttribute("data-src"), { credentials: "omit" })
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (d) {
      DATA = d;
      $('[data-inhe="updated"]').textContent = "Last updated " + d.updated;
      fillPicker();
      applyParams();
      $('[data-inhe="app"]').hidden = false;
      root.addEventListener("input", render);
      root.addEventListener("change", render);
      render();
    })
    .catch(function () {
      /* The fallback stays visible: it links every answer page. Nothing is guessed. */
      document.documentElement.classList.remove("inhe-js");
    });
})();
