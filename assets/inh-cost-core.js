/* True Total Cost — the arithmetic. No DOM, no network, no clock.
 *
 * WHY THE UNKNOWN-kW PATH IS FIRST IN THIS FILE
 * 92 of 139 priced SKUs (66.2%) publish no rated power. That is the MAJORITY
 * state, so it is designed here as a state with its own name, copy and
 * downstream consequences — not as the failure branch of the happy path. The
 * known-kW case falls out of it.
 *
 * THE FIVE RULES THIS FILE ENFORCES, each from a standing ruling
 *   1. Installation cost is NEVER published. No estimate, no range, no default.
 *      It is a reader input from their own electrician's quote.
 *   2. Freight is three flat tiers: $0 / $600 / $1,800. Never weight-derived.
 *   3. The $1,800 is InHouse's delivery and assembly. Electrician labour is
 *      third-party and is never summed into it.
 *   4. kW is never derived from volts x amps. That is the breaker's capacity,
 *      not the heater's draw. There is deliberately no function here that does it.
 *   5. An unresolved ZIP renders a coverage gap. It never falls back to the EIA
 *      national average or a census-division aggregate — those live in
 *      `energy.non_fallback_reference` and nothing in this file reads that key.
 *
 * NO VALUE IS EVER DEFAULTED INTO EXISTENCE. There is not one `|| 0` or `?? 0`
 * on a money path in this file. Absence takes a named branch and travels to the
 * page as a state, because a zero that means "we do not know" is the exact bug
 * `scripts/lint_missing_values.py` exists for.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(); }
  else { root.INHCost = factory(); }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var WEEKS_PER_YEAR = 52;
  var YEARS = 5;

  /* ---------------------------------------------------------------- money -- */
  function cents(x) { return Math.round(x * 100) / 100; }

  /* ------------------------------------------------------------------ ZIP -- */
  /* Returns a STATE or a named gap. Five outcomes, no sixth, and none of them
   * is a guess. `multi_state` and `territory` are separate from `unresolved`
   * because they are different facts: two answers, no answer in the dataset,
   * and no ZCTA at all. */
  function resolveZip(raw, zipTable) {
    var s = typeof raw === "string" ? raw.trim() : "";
    if (!/^\d{5}$/.test(s)) {
      return { status: "malformed", zip: s,
               reason: "a US ZIP is five digits" };
    }
    if (Object.prototype.hasOwnProperty.call(zipTable.multi_state, s)) {
      return { status: "multi_state", zip: s, states: zipTable.multi_state[s],
               reason: "this ZIP straddles a state line, and the two states have "
                       + "different electricity rates" };
    }
    if (Object.prototype.hasOwnProperty.call(zipTable.territories, s)) {
      return { status: "territory", zip: s, states: zipTable.territories[s],
               reason: "US territories have no row in the EIA residential price "
                       + "dataset. That is a gap, not a case for a national figure" };
    }
    var r = zipTable.ranges, lo = 0, hi = r.length - 1;
    var n = parseInt(s, 10);  /* missing-ok: s was proved /^\d{5}$/ above */
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (n < r[mid][0]) { hi = mid - 1; }
      else if (n > r[mid][1]) { lo = mid + 1; }
      else { return { status: "ok", zip: s, state: r[mid][2] }; }
    }
    return { status: "unresolved", zip: s,
             reason: "no ZCTA covers this ZIP. PO-box-only and single-building "
                     + "ZIPs are real ZIPs with no Census area, so they do not "
                     + "resolve" };
  }

  function rateFor(state, tables) {
    var rates = tables.energy.rates_cents_per_kwh;
    if (!Object.prototype.hasOwnProperty.call(rates, state)) { return null; }
    return rates[state];
  }

  /* -------------------------------------------------------- the kW state -- */
  /* THE ORDER OF RESORT, and it is the whole design:
   *   1. the catalogue states a rating          -> "published"
   *   2. it does not, and the reader typed one  -> "reader"
   *   3. it does not, and the reader has not    -> "invite"
   *   4. it does not, and the reader declined   -> "declined"
   * There is no fifth branch that estimates from a similar model, a class
   * average, or amperage. */
  function powerState(product, input) {
    if (product && product.kw && product.kw.v !== null && product.kw.v !== undefined) {
      return { state: "published", kw: product.kw.v, source: product.kw.src,
               fetched_at: product.kw.at, span: product.kw.span };
    }
    var reason = product && product.kw ? product.kw.reason : "NO_PRODUCT_SELECTED";
    if (input.readerKw !== null && input.readerKw !== undefined) {
      return { state: "reader", kw: input.readerKw,
               source: "reader-supplied, from your own spec plate or manual",
               fetched_at: null, catalogue_reason: reason };
    }
    if (input.declinedKw === true) {
      return { state: "declined", kw: null, catalogue_reason: reason };
    }
    return { state: "invite", kw: null, catalogue_reason: reason,
             manual: product ? product.manual : null };
  }

  /* --------------------------------------------------------- running cost -- */
  /* kilowatts x hours x sessions per week x weeks x the state rate.
   * Published 2026-09-09 and unchanged since; `tables.session` carries it. */
  function runningCost(power, zip, input, tables) {
    var line = { id: "running", label: "Running cost, per year", amount: null };
    if (power.state === "declined") {
      line.state = "excluded";
      line.why = "You chose not to supply a rating, so running cost is left out "
               + "of the total rather than guessed.";
      return line;
    }
    if (power.state === "invite") {
      line.state = "invite";
      line.why = "This manufacturer does not publish a rated power for this "
               + "model, so nobody selling it can compute what it costs to run — "
               + "including us.";
      line.manual = power.manual;
      return line;
    }
    if (zip.status !== "ok") { line.state = "zip_gap"; line.why = zip.reason; return line; }
    var rate = rateFor(zip.state, tables);
    if (rate === null) {
      line.state = "no_rate";
      line.why = "the EIA residential dataset has no row for " + zip.state;
      return line;
    }
    var hours = input.sessionMinutes / 60;
    var kwh = power.kw * hours * input.sessionsPerWeek * WEEKS_PER_YEAR;
    line.state = "computed";
    line.amount = cents(kwh * rate / 100);
    line.per_session = cents(power.kw * hours * rate / 100);
    line.kwh_per_year = Math.round(kwh * 10) / 10;
    line.kw = power.kw;
    line.kw_state = power.state;
    line.rate_cents = rate;
    line.us_state = zip.state;
    line.source = tables.energy.dataset + ", period " + tables.energy.latest_period;
    line.fetched_at = tables.energy.fetched_at;
    line.formula = tables.session.formula;
    return line;
  }

  /* --------------------------------------------------------------- freight -- */
  function freightLine(input, tables) {
    var tiers = tables.freight.tiers, chosen = null;
    for (var i = 0; i < tiers.length; i++) {
      if (tiers[i].tier === input.freightTier) { chosen = tiers[i]; }
    }
    if (chosen === null) {
      return { id: "freight", label: "Delivery", amount: null, state: "unchosen",
               why: "pick how it should arrive" };
    }
    var line = { id: "freight", label: "Delivery", amount: cents(chosen.usd),
                 state: "included", tier: chosen.tier,
                 source: tables.freight.source + " — " + tables.freight.basis,
                 fetched_at: tables.freight.fetched_at };
    /* Shown even when it is nothing. "$0 curbside — included in your price"
     * beats hiding the line: a reader who cannot see the line cannot tell
     * whether delivery is free or simply unaccounted for. */
    if (chosen.usd === 0) { line.note = "included in your price"; }
    if (chosen.tier === "inside_and_assembled") {
      line.note = "InHouse delivery and assembly. Electrician labour is "
                + "third-party and is never inside this figure.";
    }
    return line;
  }

  /* ------------------------------------------- reader-entered, or omitted -- */
  /* Installation, foundation and maintenance share one shape and one ruling:
   * this store does not publish a number for any of them, so each is either the
   * reader's own figure or an explicit omission. No midpoint. No range. */
  function readerLine(id, label, value, whyAbsent, note) {
    if (value === null || value === undefined) {
      return { id: id, label: label, amount: null, state: "omitted", why: whyAbsent };
    }
    return { id: id, label: label, amount: cents(value), state: "reader",
             source: "your own figure", note: note };
  }

  /* ----------------------------------------------------------------- total -- */
  function compute(input, tables, zipTable) {
    var product = input.product !== null && input.product !== undefined
                ? input.product : null;
    var zip = resolveZip(input.zip, zipTable);
    var power = powerState(product, input);
    var lines = [];

    /* purchase price: the catalogue's, or the reader's own if they typed one
     * for a model we do not carry. Never both. */
    if (product !== null && product.price && product.price.v !== null) {
      lines.push({ id: "price", label: "Purchase price", amount: cents(product.price.v),
                   state: "published", source: product.price.src,
                   fetched_at: product.price.at });
    } else if (input.manualPrice !== null && input.manualPrice !== undefined) {
      lines.push({ id: "price", label: "Purchase price", amount: cents(input.manualPrice),
                   state: "reader", source: "your own figure" });
    } else {
      lines.push({ id: "price", label: "Purchase price", amount: null,
                   state: "omitted", why: "pick a model, or type a price" });
    }

    lines.push(freightLine(input, tables));
    lines.push(readerLine("electrical", "Electrical work",
      input.electricalQuote,
      "We do not publish an installation cost. Every page that quotes one has "
      + "estimated it. Enter your electrician's quote and it goes in the total.",
      "third-party, never inside the delivery fee"));
    lines.push(readerLine("foundation", "Foundation or pad",
      input.foundationCost,
      product !== null && product.io === "outdoor"
        ? "An outdoor cabin needs a level base. No source in this catalogue "
          + "states what yours costs, so enter it or it stays out."
        : "Not applicable to an indoor unit, and not priced for an outdoor one "
          + "unless you enter it."));
    lines.push(readerLine("maintenance", "Maintenance, per year",
      input.maintenancePerYear,
      "No source we hold publishes a maintenance figure for these units, so "
      + "there is nothing here to put a number against."));

    var running = runningCost(power, zip, input, tables);
    lines.push(running);

    /* THE TOTAL SUMS WHAT IS KNOWN AND NAMES WHAT IT LEFT OUT. A partial total
     * that says what it excludes beats a complete total that is wrong. */
    var RECURRING = { running: true, maintenance: true };
    var oneOff = 0, perYear = 0, excluded = [], recurringKnown = 0, recurringTotal = 0;
    for (var i = 0; i < lines.length; i++) {
      var L = lines[i];
      if (RECURRING[L.id] === true) { recurringTotal += 1; }
      if (L.amount === null) {
        excluded.push({ id: L.id, label: L.label, why: L.why });
        continue;
      }
      if (RECURRING[L.id] === true) { perYear += L.amount; recurringKnown += 1; }
      else { oneOff += L.amount; }
    }
    var fiveYear = cents(oneOff + perYear * YEARS);
    var sessions = input.sessionsPerWeek * WEEKS_PER_YEAR * YEARS;

    return {
      zip: zip,
      power: power,
      lines: lines,
      excluded: excluded,
      complete: excluded.length === 0,
      one_off_usd: cents(oneOff),
      /* $0.00 a year is a MEASUREMENT when both recurring lines were supplied as
       * zero, and an ABSENCE when neither was supplied at all. The page must be
       * able to tell them apart, so the count travels with the sum instead of
       * the reader being shown a zero that means "we do not know". */
      per_year_usd: recurringKnown > 0 ? cents(perYear) : null,
      recurring_lines_known: recurringKnown,
      recurring_lines_total: recurringTotal,
      five_year_usd: fiveYear,
      sessions_over_five_years: sessions,
      cost_per_session_usd: sessions > 0 ? cents(fiveYear / sessions) : null,
      years: YEARS,
      weeks_per_year: WEEKS_PER_YEAR
    };
  }

  function defaults(tables) {
    return {
      product: null, manualPrice: null, zip: "",
      freightTier: null,
      sessionsPerWeek: tables.session.sessions_per_week_default,
      sessionMinutes: tables.session.minutes_default,
      readerKw: null, declinedKw: false,
      electricalQuote: null, foundationCost: null, maintenancePerYear: null
    };
  }

  return { compute: compute, resolveZip: resolveZip, rateFor: rateFor,
           powerState: powerState, runningCost: runningCost, defaults: defaults,
           WEEKS_PER_YEAR: WEEKS_PER_YEAR, YEARS: YEARS, cents: cents };
});
