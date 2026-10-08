"""Round 4: text-link edits (link only, nothing else) and the A8 mid-word quote trim."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import electrical_build as eb  # noqa: E402
import promote_r4_apply as pa  # noqa: E402
import verified_build as vb  # noqa: E402


def test_snip_flags_only_a_real_mid_word_cut():
    text = "x" * 50 + " Manual CARBON MODEL SAUNA FOR INDOOR USE ONLY 120VAC 15AMP Dedicated Circuit Required"
    m = re.search(r"15AMP", text)
    s = vb.snip(text, m, pad=60)
    assert s.mid is (text[m.start() - 60 - 1].isalnum() and text[m.start() - 60].isalnum())
    m2 = re.search(r"120VAC", "SAUNA 120VAC 15AMP")
    assert vb.snip("SAUNA 120VAC 15AMP", m2).mid is False          # window starts at 0: never mid-word


def test_a8_trims_only_flagged_quotes():
    sn = "ARBON MODEL SAUNA SAUNA IS FOR INDOOR USE ONLY Two 120VAC 15AMP Separate Dedicated Circuits Required Carefully"
    f = {"value": 15.0, "evidence": {"snippet": sn}}
    assert eb.quote(f, "stated_amperage", set())["text"].startswith("ARBON")
    f["evidence"]["snippet_starts_mid_word"] = True
    q = eb.quote(f, "stated_amperage", set())
    assert q["text"].startswith("MODEL SAUNA") and q["lead"] is True


def test_exactly_the_eight_listed_quotes_were_trimmed():
    data = json.loads((ROOT / "assets/inh-electrical-data.json").read_text())
    starts = {m["handle"]: [s["quote"]["text"] for s in m["statements"]] for m in data["models"]}
    for bad in ("UNA –", "N MODEL SAUNAS", "ARBON MODEL", "DEL SAUNA FOR", "FRARED MODEL", "5°F ELECTRICAL", "ATURE 130"):
        assert not any(t.startswith(bad) for ts in starts.values() for t in ts), bad


def _e(before, anchor, target="/pages/sauna-electrical-requirements", page_type="article", after=None):
    i = before.index(anchor)
    return {"before_text": before, "anchor": anchor, "target": target, "page_type": page_type,
            "after_text": after or before[:i] + f'<a href="{target}">{anchor}</a>' + before[i + len(anchor):]}


def test_edit_html_inserts_the_link_and_nothing_else():
    src = "<p>Most cabins need a <strong>dedicated circuit</strong> and a 240V circuit here.</p>"
    e = _e(" and a 240V circuit here.", "240V circuit")
    new, tag = pa.edit_html(src, e)
    assert new == src.replace("240V circuit", tag)
    assert new.replace(tag, "240V circuit") == src


def test_edit_html_uses_the_approved_position_when_the_anchor_repeats():
    before = "FD-3 needs a dedicated 240V circuit; FD-5 needs a 240V circuit too."
    e = _e(before, "240V circuit")                                  # approved: the FIRST occurrence
    new, tag = pa.edit_html(f"<p>{before}</p>", e)
    assert new.index(tag) < new.index("FD-5")


def test_edit_html_refuses_an_ambiguous_location():
    src = "<p>Needs a dedicated circuit.</p><p>Needs a dedicated circuit.</p>"
    with pytest.raises(ValueError):
        pa.edit_html(src, _e("Needs a dedicated circuit.", "dedicated circuit"))


def test_edit_html_never_edits_inside_an_existing_link():
    src = '<p><a href="/x">dedicated circuit</a></p>'
    with pytest.raises(ValueError):
        pa.edit_html(src, _e("dedicated circuit", "dedicated circuit"))


def test_edit_rich_splits_a_plain_node_around_the_link():
    doc = {"type": "root", "children": [{"type": "list", "children": [{"type": "list-item", "children": [
        {"type": "text", "value": "Electrical Requirements: 120V/20amp"}]}]}]}
    e = {"before_text": "Electrical Requirements: 120V/20amp", "anchor": "Electrical Requirements", "target": "/pages/x",
         "node_path": [0, 0, 0]}
    new, _ = pa.edit_rich(json.dumps(doc), e)
    kids = json.loads(new)["children"][0]["children"][0]["children"]
    assert kids[0] == {"type": "link", "url": "/pages/x", "title": None, "children": [{"type": "text", "value": "Electrical Requirements"}]}
    assert kids[1] == {"type": "text", "value": ": 120V/20amp"}


def test_edit_rich_refuses_a_partial_link_inside_a_bold_node():
    """Linking part of a bold label splits <strong> in the rendered HTML: more than the link (4 reverted)."""
    doc = {"type": "root", "children": [{"type": "paragraph", "children": [
        {"type": "text", "value": "Electrical Requirements:", "bold": True}]}]}
    e = {"before_text": "Electrical Requirements:", "anchor": "Electrical Requirements", "target": "/pages/x", "node_path": [0, 0]}
    with pytest.raises(ValueError):
        pa.edit_rich(json.dumps(doc), e)
    e["anchor"] = "Electrical Requirements:"           # the WHOLE marked node: the link wraps it, nothing splits
    e["before_text"] = "Electrical Requirements:"
    new, _ = pa.edit_rich(json.dumps(doc), e)
    assert json.loads(new)["children"][0]["children"] == [{"type": "link", "url": "/pages/x", "title": None,
                                                            "children": [{"type": "text", "value": "Electrical Requirements:", "bold": True}]}]


def test_calculator_help_text_gains_only_the_link():
    s = (ROOT / "sections/true-total-cost.liquid").read_text()
    assert s.count('href="/pages/sauna-electrical-requirements"') == 1
    assert '<a href="/pages/sauna-electrical-requirements">rating its manufacturer publishes</a>; most publish none.' in s


def test_llms_txt_keeps_its_content_and_adds_two_sections():
    s = (ROOT / "templates/llms.txt.liquid").read_text()
    for h in ("## Verified Sauna Database", "## Electrical requirements", "## Cost", "## How records are verified", "## For agents"):
        assert s.count(h) == 1, h
    for page in ("sauna-electrical-requirements", "sauna-heater-size-calculator", "6-kw-sauna-heater-breaker-size",
                 "8-kw-sauna-heater-breaker-size", "infrared-sauna-dedicated-circuit", "sauna-electrical-methodology", "sauna-cost"):
        assert f"{{{{ agents.store_url }}}}/pages/{page})" in s, page
