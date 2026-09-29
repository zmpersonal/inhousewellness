"""Go-live: the hub must render one row per active entry, as a logged-out visitor sees it, and
every page write must keep its template. From the 2026-09-29 hub report (a staff browser on a
preview of an older theme saw the default page template: title and body only)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_deploy as vd  # noqa: E402
import verified_golive as g  # noqa: E402

A, B = "sauna/x/a", "sauna/y/b"


def hub(ids, count=None):
    rows = "".join(f'<tr data-heat="t" data-cap="2" data-brand="X" data-inh-id="{i}"><td>x</td></tr>' for i in ids)
    return f'<strong data-inhv="model-count">{len(ids) if count is None else count}</strong><table>{rows}</table>'


FALLBACK = ('<h1>Verified Sauna Database</h1><div class="rte"><p>This page lists every model in the InHouse '
            'Wellness Verified Sauna Database.</p></div>')


def test_the_default_page_template_fallback_fails():
    assert "not rendered" in g.hub_rows_problem(FALLBACK, [A, B])


def test_fewer_rows_than_active_entries_fails():
    assert "1 rows for 2" in g.hub_rows_problem(hub([A]), [A, B])


def test_the_wrong_rows_fail():
    assert g.hub_rows_problem(hub([A, "sauna/z/c"]), [A, B])


def test_a_count_disagreeing_with_the_rows_fails():
    assert g.hub_rows_problem(hub([A, B], count=131), [A, B])


def test_exactly_the_active_entries_passes():
    assert g.hub_rows_problem(hub([B, A]), [A, B]) is None


def test_a_live_check_refuses_a_preview_url():
    with pytest.raises(SystemExit):
        g.visitor_get("https://inhousewellness.com/pages/sauna-database?preview_theme_id=1")


def test_a_page_write_sets_the_template_and_halts_if_it_does_not_read_back():
    sent = []

    def q(query, v=None):
        if "pageUpdate" in query:
            sent.append(v["p"])
            return {"pageUpdate": {"page": {"id": "p"}, "userErrors": []}}
        return {"page": {"id": "p", "isPublished": True, "templateSuffix": None}}   # Shopify dropped it

    with pytest.raises(SystemExit):
        vd.page_update_checked(q, "p", {"isPublished": True}, "inh-verified-hub")
    assert sent[0]["templateSuffix"] == "inh-verified-hub"


def test_every_page_update_in_the_launch_path_goes_through_the_checked_writer():
    import ast
    for f in ("scripts/verified_golive.py",):
        tree = ast.parse((ROOT / f).read_text())
        raw = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "PAGE_UPDATE_M"]
        assert raw == [], f"{f} calls pageUpdate directly"
