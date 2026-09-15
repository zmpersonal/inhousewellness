"""The runner-parity checks, run as part of the ordinary suite.

Putting these here matters as much as putting them in the workflows. Three
Actions failures in a row were all "exists on the dev host, absent on the
runner", and every one of them was discoverable from the repo alone, before a
runner was ever involved. A check that only runs in CI is a check that finds
the problem after the push; these find it before.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preflight import (  # noqa: E402
    STDLIB_ONLY, check_deps, check_stdlib_only, check_workflow_paths,
    check_workflow_text, declared, self_test,
)


def test_preflight_controls_fire():
    """Every check rejects a known-bad input. A guard that has never failed has
    not been tested, so this runs before any of the checks are trusted below."""
    assert self_test(ROOT) == []


def test_every_third_party_import_is_declared():
    """The run-3 class: pytest was in requirements.txt and not in the workflow's
    hand-written install list. The list is gone; this asserts the manifest is
    complete, so no workflow needs one."""
    assert check_deps(ROOT) == []


def test_every_script_a_workflow_names_exists():
    """The run-1/2 class: actions/checkout takes the ref you dispatch on, so a
    workflow that landed on main while its scripts sat on a branch checked out a
    tree without them. A workflow and the scripts it calls must land together."""
    assert check_workflow_paths(ROOT) == []


def test_outward_reaching_scripts_stay_stdlib_only():
    """Asserted, not inferred. Two workflows used to prove this by running the
    script on a bare interpreter before any pip install — true only while the
    job happened to install nothing, and fetch-manufacturer-specs.yml now
    installs pytest. The invariant is real; the proof had to stop depending on
    the environment."""
    assert check_stdlib_only(ROOT, STDLIB_ONLY) == []


def test_requirements_parses_cleanly():
    decl, bad = declared((ROOT / "requirements.txt").read_text())
    assert bad == [], f"unparseable requirement lines: {bad}"
    assert "pytest" in decl and "playwright" in decl


@pytest.mark.parametrize("dist,mod", [("python-dotenv", "dotenv"),
                                      ("imageio-ffmpeg", "imageio_ffmpeg"),
                                      ("anthropic", "anthropic")])
def test_dist_to_import_name(dist, mod):
    """python-dotenv imports as `dotenv`. Getting this wrong would make the
    post-install check report a package as missing when it is installed — a
    false alarm is as corrosive here as a miss."""
    decl, _ = declared(f"{dist}\n")
    assert decl[dist] == mod


def test_workflow_path_check_ignores_data_outputs():
    """data/facts/manufacturer_specs.json does not exist until the first run
    writes it. Demanding it would fail every first run."""
    assert check_workflow_text(ROOT, "x.yml", "--out data/facts/nothing_yet.json") == []
