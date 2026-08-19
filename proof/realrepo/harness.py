"""Pytest plumbing for the real-repo runs. No law of any kind lives here."""
import os, re, ast, sys, json, collections, subprocess

PY = sys.executable


def run_suite(repo, ignore):
    r = subprocess.run([PY, "-m", "pytest", "-q", "--tb=native", "-p", "no:randomly"]
                       + ignore, cwd=repo, capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    m = re.search(r"(\d+) failed", out)
    return (int(m.group(1)) if m else 0), out


def failing_nodes(out):
    return sorted(set(re.findall(r"^FAILED (\S+?)(?: |$)", out, re.M)))


def frames(out, repo, pkg):
    got = []
    for m in re.finditer(r'File "([^"]+)", line \d+, in (\w+)', out):
        p, fname = m.group(1), m.group(2)
        if pkg in p and "test" not in os.path.basename(p) and os.path.exists(p):
            rel = os.path.relpath(p, repo)
            if rel.endswith(".py"):
                got.append((rel[:-3].replace("/", "."), fname))
    return got


def targets(repo, out, cfg):
    """Which function? The traceback, then the failing TEST's own calls.

    Matching a function name out of a test name does not work -- toolz's
    test_reduce_by_init tests reduceby -- so the test body is parsed and the
    library functions it calls are read off directly."""
    got = list(reversed(frames(out, repo, cfg["pkg"])))
    defined = {}
    for mod in cfg["mods"]:
        pth = os.path.join(repo, mod.replace(".", "/") + ".py")
        if os.path.exists(pth):
            try:
                for nd in ast.walk(ast.parse(open(pth).read())):
                    if isinstance(nd, ast.FunctionDef):
                        defined.setdefault(nd.name, mod)
            except SyntaxError:
                pass
    called = collections.Counter()
    for node in failing_nodes(out):
        fpath, _, tname = node.partition("::")
        tname = tname.split("::")[-1]
        full = os.path.join(repo, fpath)
        if not os.path.exists(full):
            continue
        try:
            tree = ast.parse(open(full).read())
        except SyntaxError:
            continue
        for nd in ast.walk(tree):
            if isinstance(nd, ast.FunctionDef) and nd.name == tname:
                for c in ast.walk(nd):
                    if isinstance(c, ast.Call):
                        fn = c.func
                        nm = fn.id if isinstance(fn, ast.Name) else (
                             fn.attr if isinstance(fn, ast.Attribute) else None)
                        if nm in defined:
                            called[nm] += 1
    for nm, _ in called.most_common():
        pair = (defined[nm], nm)
        if pair not in got:
            got.append(pair)
    return got


REPOS = {"hard": dict(root=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "bugged"),
                      pkg="toolz",
                      mods=["toolz.itertoolz", "toolz.dicttoolz", "toolz.recipes",
                            "toolz.functoolz"],
                      ignore=["--ignore=toolz/tests/test_package.py"])}
