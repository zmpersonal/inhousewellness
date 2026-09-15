#!/usr/bin/env python3
"""Prove the runner can do what the job is about to ask of it -- BEFORE it asks.

WHY THIS EXISTS
Three consecutive Actions failures had one shape: something that exists on the
dev host was absent on the runner, and the absence surfaced at the point of use
rather than at the start.

    run 1/2  scripts/fetch_zip_state.py, src/power_parse.py  -- on the branch,
             not on the ref that was dispatched
    run 3    pytest                                          -- in requirements
             on the dev host, not in the workflow's hand-written install list

Each was fixed as an instance. The class was not: the runner's environment was
a hand-maintained GUESS at what the code needs, kept in a different file from
the code, and the guess was only tested by running the expensive work first.
Run 3 spent 17 seconds of other people's bandwidth, refreshed all 13 datasets
cleanly, passed the shrink floor and the lint -- and threw the whole thing away
on `No module named pytest`.

So the guess is gone. requirements.txt is now the single declaration of what
this repo needs, every workflow installs from it, and these checks assert that
the declaration, the code and the workflows still agree. They are stdlib-only
and take milliseconds, so they run first, on a bare interpreter, before any
install and before any network call.

    --deps            every third-party import in the tree is declared in
                      requirements.txt (closes the run-3 class)
    --workflow-paths  every .py a workflow names exists in this checkout
                      (closes the run-1/2 class)
    --stdlib-only     named files import stdlib + local only -- an ASSERTED
                      invariant, replacing "we happened not to pip install"
    --imports         (post-install) every declared requirement imports
    --self-test       every check above fires against a known-bad input,
                      because a guard that has never failed is not a guard

Exit 0 clean, 1 with every problem named. No check here is a substitute for the
test suite; they are the cheap checks that must pass before it is worth running.
"""
import argparse
import ast
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Distribution name -> import name, ONLY where they differ. The default rule
# (hyphens to underscores) already covers imageio-ffmpeg -> imageio_ffmpeg, so
# this map stays a short list of genuine exceptions rather than a second
# inventory that can drift from requirements.txt.
DIST_TO_IMPORT = {"python-dotenv": "dotenv"}

# Files that must never grow a third-party import. Both reach outside this repo
# -- one crawls other companies' servers, the other writes to a live Shopify
# theme -- and a dependency that fails to install must not be able to strand
# either of them mid-flight.
STDLIB_ONLY = [
    "scripts/fetch_manufacturer_specs.py",
    "scripts/verify_theme_asset_path.py",
    "src/power_parse.py",
    # Reaches Shopify, and runs in the deploy workflow's gate step BEFORE any
    # pip install. Same rule as the crawler: a script that leaves this repo has
    # its stdlib-only property asserted by AST, never by "it happened to run on
    # a bare interpreter once, in a job that installed nothing".
    "scripts/deploy_theme_files.py",
    "scripts/deploy_pages.py",
    "scripts/deploy_redirects.py",
    # Round 4's read-only comparison. It reaches Shopify, and it runs in a
    # workflow that installs nothing at all -- so its stdlib-only property is
    # asserted here rather than inferred from that job happening to install
    # nothing today. Same correction as the pytest one that discarded a refresh.
    "scripts/diff_themes.py",
    "scripts/rollback_calculator.py",
]


def normalize(dist):
    """PEP 503 name normalisation, so Python-Dotenv and python_dotenv agree."""
    return re.sub(r"[-_.]+", "-", dist).lower()


def local_module_names(root):
    """Module names that resolve inside this repo, so they are never mistaken
    for a missing third-party package. scripts/ counts: several scripts import
    each other by stem after a sys.path insert."""
    names = {"src", "scripts", "tests"}
    for sub in ("src", "scripts", "tests"):
        for p in (root / sub).glob("*.py"):
            names.add(p.stem)
    return names


def imports_of(source):
    """Top-level module name of every import in a source string."""
    out = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def third_party_imports(source, local):
    return {m for m in imports_of(source)
            if m not in sys.stdlib_module_names and m not in local}


def declared(req_text):
    """dist -> import name, from a requirements file. Comments, blank lines and
    version specifiers are stripped; anything unparseable is reported rather
    than skipped, because a requirement this cannot read is one it cannot
    check."""
    out, bad = {}, []
    for raw in req_text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not m:
            bad.append(line)
            continue
        dist = m.group(1)
        key = normalize(dist)
        out[key] = DIST_TO_IMPORT.get(key, key.replace("-", "_"))
    return out, bad


def py_files(root):
    for sub in ("src", "scripts", "tests"):
        yield from sorted((root / sub).glob("*.py"))


def check_deps(root):
    """Every third-party import in the tree is declared in requirements.txt."""
    problems = []
    req = root / "requirements.txt"
    if not req.exists():
        return ["requirements.txt is missing -- there is no declaration to check against"]
    decl, bad = declared(req.read_text())
    problems += [f"requirements.txt: cannot parse {line!r}" for line in bad]
    satisfied = set(decl.values())
    local = local_module_names(root)
    users = {}
    for p in py_files(root):
        try:
            for m in third_party_imports(p.read_text(), local):
                users.setdefault(m, []).append(str(p.relative_to(root)))
        except SyntaxError as e:
            problems.append(f"{p.relative_to(root)}: will not parse -- {e}")
    for mod in sorted(users):
        if mod not in satisfied:
            problems.append(
                f"import {mod!r} (in {', '.join(sorted(users[mod]))}) is not declared "
                f"in requirements.txt -- it exists on the dev host and will be "
                f"absent on a runner")
    return problems


def check_stdlib_only(root, rels):
    problems = []
    local = local_module_names(root)
    for rel in rels:
        p = root / rel
        if not p.exists():
            problems.append(f"{rel}: listed as stdlib-only but the file is missing")
            continue
        extra = third_party_imports(p.read_text(), local)
        if extra:
            problems.append(
                f"{rel}: must import stdlib + local only, but imports "
                f"{', '.join(sorted(extra))}")
    return problems


# Any repo-relative .py a workflow names, and any -r requirements file. Data
# paths are deliberately NOT checked: most are outputs a run has yet to write,
# and asserting those exist would fail every first run.
WF_PY = re.compile(r"\b((?:scripts|src|tests)/[\w./-]+\.py)\b")
WF_REQ = re.compile(r"-r\s+([\w./-]+\.txt)\b")


def check_workflow_text(root, name, text):
    problems = []
    for rx, kind in ((WF_PY, "script"), (WF_REQ, "requirements file")):
        for rel in sorted(set(rx.findall(text))):
            if not (root / rel).exists():
                problems.append(
                    f"{name}: names the {kind} {rel}, which is not in this checkout "
                    f"-- actions/checkout takes the dispatched ref, so a file that "
                    f"lives only on another branch is simply absent here")
    return problems


def check_workflow_paths(root):
    problems = []
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return ["no .github/workflows directory"]
    for p in sorted(wf.glob("*.yml")) + sorted(wf.glob("*.yaml")):
        problems += check_workflow_text(root, p.name, p.read_text())
    return problems


def check_imports(root):
    """Post-install: every declared requirement actually imports here."""
    import importlib.util
    decl, _ = declared((root / "requirements.txt").read_text())
    problems = []
    for dist, mod in sorted(decl.items()):
        try:
            found = importlib.util.find_spec(mod) is not None
        except (ImportError, ValueError):
            found = False
        print(f"  {dist:22s} import {mod:18s} {'ok' if found else 'NOT IMPORTABLE'}")
        if not found:
            problems.append(f"{dist} is declared but {mod!r} does not import -- "
                            f"the install did not deliver it")
    return problems


def self_test(root):
    """Each check, fired at an input it must reject. A check that has only ever
    been run against a passing tree has not been tested."""
    fails = []
    with tempfile.TemporaryDirectory() as td:
        fake = pathlib.Path(td)
        for sub in ("src", "scripts", "tests"):
            (fake / sub).mkdir()
        (fake / "requirements.txt").write_text("pytest>=8.0\n")
        (fake / "scripts" / "thing.py").write_text("import json\nimport notarealpkg\n")
        got = check_deps(fake)
        if not any("notarealpkg" in g for g in got):
            fails.append("--deps did not flag an undeclared import")

        (fake / "src" / "bare.py").write_text("import requests\n")
        got = check_stdlib_only(fake, ["src/bare.py"])
        if not any("requests" in g for g in got):
            fails.append("--stdlib-only did not flag a third-party import")
        if not check_stdlib_only(fake, ["src/absent.py"]):
            fails.append("--stdlib-only did not flag a missing file")

        got = check_workflow_text(fake, "x.yml", "run: python scripts/nope.py\n")
        if not got:
            fails.append("--workflow-paths did not flag a script absent from the checkout")
        if check_workflow_text(fake, "x.yml", "run: python scripts/thing.py\n"):
            fails.append("--workflow-paths flagged a script that is present")
        # An output path must NOT be treated as a precondition.
        if check_workflow_text(fake, "x.yml", "--out data/facts/not_yet.json\n"):
            fails.append("--workflow-paths wrongly demanded a data output exist")

    d, bad = declared("# c\n\nPython_Dotenv==1.0\nimageio-ffmpeg>=0.4\n!!\n")
    if d.get("python-dotenv") != "dotenv":
        fails.append("the dist->import map did not resolve python-dotenv")
    if d.get("imageio-ffmpeg") != "imageio_ffmpeg":
        fails.append("the default hyphen rule did not resolve imageio-ffmpeg")
    if not bad:
        fails.append("an unparseable requirement line was silently skipped")
    return fails


CHECKS = {
    "deps": ("dependency parity: imports vs requirements.txt", check_deps),
    "workflow-paths": ("workflow paths: every .py a workflow names is here",
                       check_workflow_paths),
    "stdlib-only": ("stdlib-only invariant on the outward-reaching scripts",
                    lambda root: check_stdlib_only(root, STDLIB_ONLY)),
    "imports": ("post-install: every declared requirement imports", check_imports),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in CHECKS:
        ap.add_argument(f"--{name}", action="store_true")
    ap.add_argument("--static", action="store_true",
                    help="deps + workflow-paths + stdlib-only: everything that "
                         "runs on a bare interpreter, before any install")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test(ROOT)
        if fails:
            sys.exit("HALT: preflight's own controls did not fire:\n  " + "\n  ".join(fails))
        print("preflight self-test: every check fires against a known-bad input")
        return

    wanted = [n for n in CHECKS if getattr(args, n.replace("-", "_"))]
    if args.static:
        wanted = ["deps", "workflow-paths", "stdlib-only"]
    if not wanted:
        ap.error("pick at least one check, or --static, or --self-test")

    problems = []
    for name in wanted:
        label, fn = CHECKS[name]
        print(f"{label}:")
        found = fn(ROOT)
        for f in found:
            print(f"  FAIL  {f}")
        if not found:
            print("  ok")
        problems += found
    if problems:
        sys.exit(f"\nHALT: preflight found {len(problems)} problem(s). Every one of "
                 f"these would otherwise have surfaced later in the job, after the "
                 f"expensive work.")
    print("\npreflight: clean")


if __name__ == "__main__":
    main()
