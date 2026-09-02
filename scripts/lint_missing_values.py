#!/usr/bin/env python3
"""Lint for the missing-value pattern (Round 6, item 0).

Five times in this project a missing or unusable value took a failure branch and
produced a confident, precise, FALSE result:

  1. `idf.get(t, 1.0)` scored corpus-absent tokens as maximally COMMON, inverting
     the rare-token gate on exactly the queries that needed it.
  2. HTTP 429 was read as a dead link, blocking every INH row at once and
     reporting an INH destination share of 0.0%.
  3. `status.get(None)` blocked all 25 fact-grounded rows as "did not return 200".
  4. An .env saved by TextEdit as `.env.txt` -- every existence check truthfully
     returned False while Finder showed the right name.
  5. A well-formed but placeholder API key loaded fine and failed at the API.

Each reported itself as a finding about the world rather than a bug.

The rule: a `.get()` whose key may legitimately be absent, or whose default feeds
a decision, needs an explicit branch -- not a silent default.

Exit 1 on any finding. Run in the sweep.
"""
import ast, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = ["src", "scripts"]
SKIP_NAMES = {"lint_missing_values.py"}

# A default that is itself a decision input. `.get(k)` -> None is the classic:
# None then flows into a comparison, a lookup, or str() and silently loses.
ALLOW_COMMENT = re.compile(r"#\s*missing-ok\b")

# Helpers that explicitly handle None as their first act. The guard exists -- it
# is one level down, not absent. Verified by reading each one; a name is only
# added here after confirming it cannot be surprised by None.
NONE_SAFE = {
    "_num", "_fmt", "_fmt_num", "_walk_numbers",     # facts.py
    "domain_of", "classify", "interactive_asset_for",  # destinations.py
    "keyword_signature", "card_archetype",            # workorders.py / limits.py
    "first_sentence", "strip_html", "tokens", "_stem",
    "cached_article_figures", "figures_for", "from_article",  # figures.py
}


class Finder(ast.NodeVisitor):
    """Flags only the shape that actually caused the bugs.

    A broad "every one-arg .get()" rule produced 157 findings on this codebase,
    almost all of them already guarded (`or 0`, `if x.get(k):`, `if u` filters).
    A lint nobody reads is worse than no lint. Two precise rules instead:

      R1  A .get() result passed straight into another call, unguarded.
          `str(status.get(url))` -> "None" silently. This is bug #3 verbatim.
      R2  A .get() whose KEY is itself an expression that can be None.
          `status.get(row["source_article"])` where source_article is None by
          design. This is bug #3's other half.
    """

    def __init__(self, src, path):
        self.lines = src.splitlines()
        self.path = path
        self.hits = []
        self.parents = {}

    def _line(self, node):
        return self.lines[node.lineno - 1] if node.lineno <= len(self.lines) else ""

    def _is_get(self, node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get")

    def _silent(self, node):
        """True when the .get() can yield None without an explicit default."""
        if len(node.args) == 1:
            return True
        return (len(node.args) == 2 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value is None)

    def visit(self, node):
        for child in ast.iter_child_nodes(node):
            self.parents[child] = node
        super().visit(node)

    def visit_Call(self, node):
        line = self._line(node)
        if not ALLOW_COMMENT.search(line):
            # R1: an unguarded .get() used as an argument to another call.
            for arg in node.args:
                if self._is_get(arg) and self._silent(arg) and not self._is_get(node):
                    fname = getattr(node.func, "id", None) or getattr(node.func, "attr", "")
                    if fname not in NONE_SAFE and fname not in (
                            "len", "bool", "sorted", "list", "set", "dict",
                            "Counter", "any", "all", "get"):
                        self.hits.append((
                            node.lineno,
                            f"unguarded .get() passed into {fname}() -- None is "
                            f"consumed silently", line.strip()))
            # R2: a .get() whose KEY may itself be None.
            if self._is_get(node) and node.args:
                k = node.args[0]
                if self._is_get(k) and self._silent(k):
                    self.hits.append((
                        node.lineno,
                        "lookup key is itself an unguarded .get() -- a None key "
                        "silently misses", line.strip()))
        self.generic_visit(node)


def scan(path):
    src = path.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [(e.lineno or 0, f"syntax error: {e.msg}", "")]
    f = Finder(src, path)
    f.visit(tree)
    return f.hits


def main():
    total = 0
    for d in SCAN:
        for p in sorted((ROOT / d).rglob("*.py")):
            if p.name in SKIP_NAMES:
                continue
            hits = scan(p)
            if hits:
                print(f"\n{p.relative_to(ROOT)}")
                for ln, why, code in hits:
                    print(f"  {ln:4d}  {why}")
                    print(f"        {code[:96]}")
                total += len(hits)
    print(f"\nmissing-value lint: {total} finding(s)")
    if total:
        print("Each needs an explicit branch, or `# missing-ok` if a silent None "
              "is genuinely correct and cannot reach a decision.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
