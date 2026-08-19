"""FIND THE REPOSITORY'S OWN SHAPE. Nothing here is specific to any project.

The first release hardcoded one library's module list and test command into the
proof scripts. A product cannot do that: it has to read the repository it is
pointed at.
"""
import ast, os, re, subprocess, sys, collections


def find_package(repo):
    """The importable package under `repo` -- the top-level directory with an
    __init__.py that is not a test or build directory."""
    skip = {"test", "tests", "docs", "doc", "build", "dist", "examples", "bench"}
    best = None
    for name in sorted(os.listdir(repo)):
        p = os.path.join(repo, name)
        if not os.path.isdir(p) or name.startswith(".") or name in skip:
            continue
        if os.path.exists(os.path.join(p, "__init__.py")):
            n = sum(1 for _, _, fs in os.walk(p) for f in fs if f.endswith(".py"))
            if best is None or n > best[1]:
                best = (name, n)
    return best[0] if best else None


def modules(repo, package):
    """Every importable module in the package that is not a test."""
    out = []
    for root, _, files in os.walk(os.path.join(repo, package)):
        if "test" in os.path.basename(root):
            continue
        for f in files:
            if f.endswith(".py") and not f.startswith("test"):
                rel = os.path.relpath(os.path.join(root, f), repo)
                out.append(rel[:-3].replace(os.sep, "."))
    return sorted(out)


class EnvironmentProblem(RuntimeError):
    """The test run did not produce a verdict -- pytest missing, a collection
    error, an import failure. NOT the same as 'everything passed'."""


def run_tests(repo, extra=()):
    """Run the suite and return (failures, output).

    Raises EnvironmentProblem when the run produced no verdict at all. It used
    to return 0 failures in that case, so a missing pytest read as 'everything
    passes' -- a debugging tool telling a user their broken repository is fine.
    pytest's exit codes: 0 all passed, 1 tests failed, 2 interrupted,
    3 internal error, 4 usage error, 5 nothing collected."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=native",
                        "-p", "no:randomly"] + list(extra), cwd=repo,
                       capture_output=True, text=True, timeout=1800)
    out = r.stdout + r.stderr
    m = re.search(r"(\d+) failed", out)
    passed = re.search(r"(\d+) passed", out)
    if r.returncode == 0:
        return 0, out
    if m:
        return int(m.group(1)), out
    if r.returncode >= 2 or not passed:
        head = (out.strip().splitlines() or ["(no output)"])[0][:200]
        raise EnvironmentProblem(
            "the test run produced no verdict (pytest exit %d): %s\n"
            "This is not the same as the suite passing. Install pytest, or "
            "check that the suite collects." % (r.returncode, head))
    return 0, out


def failing_nodes(out):
    return sorted(set(re.findall(r"^FAILED (\S+?)(?: |$)", out, re.M)))


def targets(repo, out, package, mods):
    """Which function is at fault? The traceback first; then the failing TEST's
    own calls, read from its source. Matching a function name out of a test's
    NAME does not work -- test_reduce_by_init tests reduceby."""
    # RANK BY EVIDENCE, never by position. A run reports MANY failing tests, so
    # their tracebacks are concatenated -- taking "the deepest frame" then picks
    # the last test's frame, not the faulty one. And import machinery
    # (__getattr__ in a lazy __init__) is never the fault.
    score = collections.Counter()
    for m in re.finditer(r'File "([^"]+)", line \d+, in (\w+)', out):
        p, fname = m.group(1), m.group(2)
        if package not in p or "test" in os.path.basename(p) or not os.path.exists(p):
            continue
        rel = os.path.relpath(p, repo)
        if not rel.endswith(".py") or fname.startswith("__"):
            continue
        if os.path.basename(rel) == "__init__.py":
            continue
        score[(rel[:-3].replace(os.sep, "."), fname)] += 1
    defined = {}
    for mod in mods:
        pth = os.path.join(repo, mod.replace(".", os.sep) + ".py")
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
                        nm = (fn.id if isinstance(fn, ast.Name)
                              else fn.attr if isinstance(fn, ast.Attribute) else None)
                        if nm in defined:
                            called[nm] += 1
    for nm, n in called.items():
        score[(defined[nm], nm)] += n
    return [t for t, _ in score.most_common()]


def relevant(repo, out, func):
    """Of the currently-failing tests, the ones that actually exercise `func`.

    A real repository has failures nothing can fix -- toolz's test_has_version
    fails on any clone that is not pip-installed, because the package metadata
    is missing. Screening candidates against EVERY red test therefore rejects
    every candidate, since none of them can conjure package metadata. Screen
    against the tests that call the function being repaired."""
    hits = []
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
                    f = getattr(c, "func", None)
                    nm = (f.id if isinstance(f, ast.Name)
                          else f.attr if isinstance(f, ast.Attribute) else None)
                    if nm == func:
                        hits.append(node)
                        break
    return hits or failing_nodes(out)
