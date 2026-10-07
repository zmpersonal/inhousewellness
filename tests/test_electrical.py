"""Electrical tool, Round 1 Part B. Offline: reads the committed build outputs and the dataset.

The guarantees under test (Part B §1): only manufacturer-stated circuits are shown, verbatim; no
breaker size, wire gauge or code minimum can render; the one calculation (heater current draw)
uses a sourced kW and voltage and is labelled; kW is never derived from volts x amps.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import electrical_build as eb  # noqa: E402
import electrical_deploy as ed  # noqa: E402

DATA = json.loads((ROOT / "assets/inh-electrical-data.json").read_text())
RECORDS = {}
for _r in json.loads((ROOT / "data/verified/saunas.json").read_text())["records"]:
    RECORDS[_r["inh_id"]] = _r
HANDLES = {v["handle"]: k for k, v in json.loads((ROOT / "data/verified/handles.json").read_text())["handles"].items()}
PAGES = {p.stem: p.read_text() for p in (ROOT / "data/electrical/pages").glob("*.html")}
CODE_FILES = ["assets/inh-electrical.js", "sections/inh-electrical-tool.liquid", "sections/inh-electrical-page.liquid",
              "templates/page.inh-electrical-tool.json", "templates/page.inh-electrical-page.json"]


def snippets(rec):
    out = []

    def walk(x):
        if isinstance(x, dict):
            sn = (x.get("evidence") or {}).get("snippet")
            if sn:
                out.append(sn)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rec["electrical"])
    return out


def test_build_is_deterministic_and_committed():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/electrical_build.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_self_tests():
    eb.self_test()
    ed.self_test()


def test_every_quote_is_a_verbatim_substring_of_its_evidence():
    n = 0
    for m in DATA["models"]:
        sn = snippets(RECORDS[HANDLES[m["handle"]]])
        for s in m["statements"]:
            assert any(s["quote"]["text"] in x for x in sn), (m["handle"], s["quote"]["text"])
            n += 1
    assert n > 100


def test_no_quote_carries_a_hazard_warning_or_a_wire_size():
    for m in DATA["models"]:
        for s in m["statements"]:
            t = s["quote"]["text"]
            assert not eb.FEAR.search(t), (m["handle"], t)
            assert not re.search(r"\bAWG\b|wire (?:size|gauge)|\d+/\d+ wire", t, re.I), (m["handle"], t)


def test_line_table_quotes_name_this_model_and_no_other():
    for m in DATA["models"]:
        own = eb.own_model_numbers(RECORDS[HANDLES[m["handle"]]])
        for s in m["statements"]:
            text = s["quote"]["text"]
            toks = set(eb.MODEL_TOKEN.findall(text))
            # r3 D2 (approved 2026-10-07): another model may appear ONLY as a co-label inside the one
            # parenthesised label that names this model, closing the quote ("…Required
            # (DYN-6115-05/DYN-6215-05)"). Anywhere else it still fails, as before.
            trail = re.search(r"\(([^()]*)\)\s*$", text)
            colabel = set(eb.MODEL_TOKEN.findall(trail.group(1))) if trail else set()
            if not (colabel & own):
                colabel = set()
            outside = set(eb.MODEL_TOKEN.findall(text[:trail.start()] if (trail and colabel) else text))
            assert toks <= own | colabel and outside <= own, (m["handle"], toks - own)


def test_d2_trailing_label_regression():
    """DYN-6215-05 is 15 A and DYN-6315-05 is 20 A on the same Dynamic cover; neither may take the other's."""
    sn = ("SAUNA IS FOR INDOOR USE ONLY 120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05) "
          "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05) Carefully and thoroughly")
    f = lambda v: {"value": v, "evidence": {"snippet": sn}}  # noqa: E731
    assert eb.quote(f(15.0), "stated_amperage", {"DYN-6215-05"})["text"].endswith("(DYN-6115-05/DYN-6215-05)")
    assert eb.quote(f(20.0), "stated_amperage", {"DYN-6215-05"}) is None
    assert eb.quote(f(20.0), "stated_amperage", {"DYN-6315-05"})["text"] == "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05)"
    assert eb.quote(f(15.0), "stated_amperage", {"DYN-6315-05"}) is None
    lucca = next(m for m in DATA["models"] if m["handle"] == "dynamic-lucca-elite-2-person")
    assert lucca["circuit_stated"] and any("15AMP" in s["quote"]["text"] for s in lucca["statements"])


def test_current_draw_only_from_sourced_kw_and_voltage_and_kw_is_never_derived():
    for m in DATA["models"]:
        rec = RECORDS[HANDLES[m["handle"]]]
        h = m["heater"]
        if h is None:
            assert rec["electrical"]["heater_kw"]["value"] is None
            continue
        assert h["kw"] == rec["electrical"]["heater_kw"]["value"]          # never volts x amps
        if "draw_amps" in h:
            v, f = eb.heater_voltage(rec["electrical"])
            assert v and f["source_url"] == h["volts_source_url"]
            assert h["draw_amps"] == round(h["kw"] * 1000 / h["volts"], 1)


def test_no_code_based_breaker_or_wire_value_can_render():
    """Our own code holds no constant or arithmetic that produces a breaker or wire size; page bodies
    mention a breaker amperage only inside a manufacturer quote."""
    forbidden = re.compile(r"\b1\.25\b|125\s*%|\bAWG\b|ampacity|310\.16|240\.6|424\.\d|422\.\d|code[- ]based|below code", re.I)
    for f in CODE_FILES + ["scripts/electrical_build.py"]:
        src = (ROOT / f).read_text()
        hits = [ln for ln in src.splitlines() if forbidden.search(ln) and not ln.strip().startswith(("#", "//", "/*", "*"))]
        hits = [h for h in hits if "forbidden" not in h]
        assert not hits, (f, hits)
    js = (ROOT / "assets/inh-electrical.js").read_text()
    assert "kw * 1000 / volts" in js and js.count("* 1000") == 1      # the one calculation, once
    for name, body in PAGES.items():
        outside = re.sub(r'<span class="inhe-quote">.*?</span>', "", body, flags=re.S)
        assert not re.search(r"breaker[^.<]{0,25}\b\d{2}\s*a(mps?)?\b|\b\d{2}\s*a(mps?)?\b[^.<]{0,25}breaker", outside, re.I), name
        assert not re.search(r"\b\d{1,2}\s*AWG\b", outside, re.I), name


def test_every_page_carries_the_local_code_line_and_a_date():
    for name in ("6-kw-sauna-heater-breaker-size", "8-kw-sauna-heater-breaker-size", "infrared-sauna-dedicated-circuit",
                 "sauna-electrical-methodology", "sauna-electrical-requirements"):
        assert eb.LOCAL_CODE_LINE in PAGES[name], name
        assert f"Last updated {DATA['updated']}" in PAGES[name], name


def test_answer_sentences_agree_with_their_tables():
    six = [m for m in DATA["models"] if m["heater"] and m["heater"]["kw"] == 6.0]
    eight = [m for m in DATA["models"] if m["heater"] and m["heater"]["kw"] == 8.0]
    assert len(six) == 15 and len(eight) == 14
    for name, sel in (("6-kw-sauna-heater-breaker-size", six), ("8-kw-sauna-heater-breaker-size", eight)):
        body = PAGES[name]
        assert body.count("<tr><th scope=\"row\">") == len(sel)
        nums = [int(x) for x in re.findall(r"(?:manufacturers of |; |the other )(\d+)", re.search(r'class="inhe-answer">([^<]+)', body).group(1))]
        assert sum(nums) == len(sel), (name, nums)
        stated = sum(1 for m in sel if m["circuit_stated"])
        rest = re.search(r"for the other (\d+)", body)
        assert (int(rest.group(1)) if rest else 0) == len(sel) - stated
    assert "11 of the 14 listed models are from Salus." in PAGES["8-kw-sauna-heater-breaker-size"]


def test_part_a_models_render_no_flag():
    """The 18 models Part A found below a 125% reading render their stated circuit like any other."""
    for name in ("6-kw-sauna-heater-breaker-size", "8-kw-sauna-heater-breaker-size"):
        # Anchored on the flag PHRASES, not on words that ordinary prose uses ("quoted below").
        assert not re.search(r"below (?:the )?code|code minimum|125\s*%|\bflagged\b|conflicts? with", PAGES[name], re.I)


def test_gap_models_never_read_not_stated_alone():
    gaps = {g["handle"] for g in json.loads((ROOT / "data/electrical/known-gaps.json").read_text())["gaps"]}
    for m in DATA["models"]:
        if m["handle"] in gaps:
            assert m["gap"] and m["gap"]["doc_url"].startswith("https://")


def test_unmapped_products_are_never_given_a_model():
    mapped = set(DATA["product_to_model"])
    assert not mapped & {p["handle"] for p in DATA["unmapped_inh_products"]}
    # Shape, not a literal: the counts move every time the database gains a record (CLAUDE.md, "never
    # assert a literal value from refreshed data"; this test pinned 74/25 in Round 1 and broke in r3).
    reasons = [p["reason"] for p in DATA["unmapped_inh_products"]]
    assert set(reasons) <= {"no_record", "not_live"}
    priced = {x["handle"] for x in json.loads((ROOT / "data/cost-tables.json").read_text())["rows"]
              if x["fields"]["price_usd"]["value"] is not None}
    listed = [p["handle"] for p in DATA["unmapped_inh_products"]]
    assert len(listed) == len(set(listed))
    assert set(listed) == priced - set(DATA["product_to_model"])


def test_sizing_charts_are_well_formed_and_never_blended():
    for ch in DATA["charts"]:
        assert ch["url"].startswith("https://") and ch["table_page"]
        kws = [r["kw"] for r in ch["rows"]]
        assert kws == sorted(kws)
        for r in ch["rows"]:
            assert r["min"] is None or r["min"] < r["max"]
    # Code, not prose: strip comments and string literals ("They are not averaged." is copy), then
    # assert no reduction across charts exists.
    js = (ROOT / "assets/inh-electrical.js").read_text()
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
    code = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', code)
    assert not re.search(r"\.reduce\(|average|mean\(", code, re.I)


def test_deploy_guards_refuse_main_and_round13():
    assert ed.target_refusal("167150092355", "167150092355", "MAIN")
    assert ed.target_refusal(ed.ROUND13, "1", "UNPUBLISHED")
    assert ed.target_refusal("2", "1", "UNPUBLISHED") is None


def test_repo_inh_verified_sections_are_unchanged_by_this_round():
    """The model-page and hub links are patched into the PREVIEW theme's copies at deploy time, so
    the repo's copies keep matching MAIN (CLAUDE.md governance)."""
    for f in ("sections/inh-verified-model.liquid", "sections/inh-verified-hub.liquid"):
        assert 'data-inhe=' not in (ROOT / f).read_text()


@pytest.mark.parametrize("name", ["6-kw-sauna-heater-breaker-size", "8-kw-sauna-heater-breaker-size", "infrared-sauna-dedicated-circuit"])
def test_answer_pages_need_no_javascript(name):
    assert "<table" in PAGES[name] and "<script" not in PAGES[name]
