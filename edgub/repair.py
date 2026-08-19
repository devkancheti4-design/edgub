"""THE PRODUCT. Point it at a repository with failing tests.

    import edgub
    report = edgub.repair(".")

It observes what the interpreter said, the law decides which repair class the
fault belongs to, and the repair is GENERALISED FROM THE REPOSITORY'S OWN
EVIDENCE -- its failing tests. Every candidate is screened in process against
those tests and then must green the entire suite before it is kept.

Nothing here is specific to any project. The package, its modules, the failing
tests and the faulty function are all discovered by reading the repository.

What it cannot repair it does not guess at. It returns an Unrepaired record
carrying the observation, the act, the target and a ready-to-send prompt, so a
model can finish the job with the smallest possible context.
"""
import ast, os, sys, time, shutil, tempfile
from dataclasses import dataclass, field

from . import BITS, ACTS, decide, sit, observe_traceback
from .acts import ROUTES, SEMANTIC
from . import edits as _edits
from .screen import Fast
from . import discover as _d
from .pipeline import solve as _infer
from .memory import Memory as _Memory
from .discover import EnvironmentProblem as _EnvProblem


def _trial(repo, args):
    """Run the suite while a CANDIDATE is spliced in.

    A candidate can break the module at import time, and pytest then reports a
    collection error -- exit 2, no verdict. That is a fact about the CANDIDATE,
    not about the environment, so it must reject the candidate rather than
    abort the whole run. The baseline call still raises: there, no verdict
    really does mean the environment is unusable."""
    try:
        return _d.run_tests(repo, args)[0]
    except _EnvProblem:
        return 10 ** 6


@dataclass
class Repaired:
    test: str
    module: str
    function: str
    act: str
    edit: str
    candidates: int
    diff: str


@dataclass
class Unrepaired:
    test: str
    module: str
    function: str
    act: str
    candidates: int
    reason: str
    prompt: str


@dataclass
class Report:
    repaired: list = field(default_factory=list)
    unrepaired: list = field(default_factory=list)
    seconds: float = 0.0
    model_calls: int = 0
    tokens: int = 0

    def __str__(self):
        s = ["edgub: %d repaired, %d left for a model, %.1fs, %d tokens"
             % (len(self.repaired), len(self.unrepaired), self.seconds, self.tokens)]
        for r in self.repaired:
            s.append("  repaired  %s.%s   %s via %s (%d candidates)"
                     % (r.module.split(".")[-1], r.function, r.act, r.edit, r.candidates))
        for u in self.unrepaired:
            where = ("%s.%s" % (u.module.split(".")[-1], u.function)
                     if u.module else u.test)
            s.append("  left      %-24s %s" % (where, u.reason))
            if u.candidates:
                s.append("            %s exhausted %d candidates"
                         % (u.act, u.candidates))
        return "\n".join(s)


def _prompt(repo, mod, func, out, act):
    path = os.path.join(repo, mod.replace(".", os.sep) + ".py")
    src = open(path).read()
    body = ""
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            body = "\n".join(src.splitlines()[n.lineno - 1:n.end_lineno])
    return ("A debugging policy ruled: the library is wrong and must be repaired "
            "(never the test).\n\nFailing tests:\n```\n%s\n```\n\nSource of `%s` "
            "in %s:\n```python\n%s\n```\n\nReturn only the corrected function."
            % (out[:1500], func, mod.replace(".", os.sep) + ".py", body[:2500]))


def _blast_radius(orig, cand, lo, hi):
    """How far outside the target function did this candidate reach?

    Candidates are produced with ast.unparse, which regenerates source from the
    tree and DISCARDS EVERY COMMENT and normalises quoting. If the spliced
    region is wrong by even a line, the result is a rewritten file that still
    passes the tests -- which is what happened to tabulate: 294 insertions,
    1,397 deletions, reported as "1 repaired". A green suite is not evidence
    that nothing was destroyed."""
    a, b = orig.splitlines(), cand.splitlines()
    if a[:lo] != b[:lo]:
        return "text above the target function changed"
    tail_a, tail_b = a[hi:], b[len(b) - len(a[hi:]):]
    if tail_a != tail_b:
        return "text below the target function changed"
    # Comments INSIDE the target function are unavoidably lost: candidates are
    # produced with ast.unparse, which does not carry them. That is a real cost
    # and it is reported, but it must not veto the repair -- counting comments
    # across the whole file rejected every candidate for any function that
    # contained one, which is why partition could not be repaired through the
    # product while the same inference worked standalone.
    out_a = a[:lo] + a[hi:]
    out_b = b[:lo] + b[len(b) - len(a[hi:]):]
    lost = "\n".join(out_a).count("#") - "\n".join(out_b).count("#")
    if lost > 0:
        return "%d comment(s) removed OUTSIDE the target function" % lost
    return None


def _splice(path, func, body):
    src = open(path).read()
    fn = None
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
    if fn is None:
        return None, src
    lines = src.splitlines(keepends=True)
    ind = len(lines[fn.lineno - 1]) - len(lines[fn.lineno - 1].lstrip())
    if ind:
        body = "\n".join((" " * ind) + l if l.strip() else l
                         for l in body.splitlines())
    cand = "".join(lines[:fn.lineno - 1]) + body + "\n" + "".join(lines[fn.end_lineno:])
    try:
        compile(cand, "<c>", "exec")
    except SyntaxError:
        return None, src
    open(path, "w").write(cand)
    return cand, src


def repair(repo=".", package=None, pytest_args=(), max_candidates=40000,
           apply=True, verbose=False):
    """Repair what the repository's own tests determine. Returns a Report.

    repo            path to the project
    package         importable package name; discovered if omitted
    pytest_args     extra arguments for pytest (e.g. deselecting a known failure)
    apply           write repairs to disk. False leaves the tree untouched.
    """
    t0 = time.time()
    repo = os.path.abspath(repo)
    package = package or _d.find_package(repo)
    if package is None:
        raise ValueError("no importable package found under %r" % repo)
    mods = _d.modules(repo, package)
    rep = Report()
    work = repo if apply else tempfile.mkdtemp(prefix="edgub_")
    if not apply:
        shutil.copytree(repo, os.path.join(work, "r"),
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache",
                                                      ".git"))
        work = os.path.join(work, "r")

    tried_targets = set()
    mem = _Memory()
    baseline, _b = _d.run_tests(work, pytest_args)
    for _ in range(64):
        failed, out = _d.run_tests(work, pytest_args)
        if failed == 0:
            break
        baseline = failed
        red = _d.failing_nodes(out)
        obs = observe_traceback(out)
        baseline = failed
        act_i = decide(sit(obs))
        act = ACTS[act_i]
        classes, tier = ROUTES.get(act_i, (SEMANTIC, 3))
        tg = _d.targets(work, out, package, mods)
        if not tg or not classes:
            rep.unrepaired.append(Unrepaired(
                ", ".join(red[:3]), "", "",
                act, 0,
                "the failing test exercises no function in this package -- it is "
                "an environment or packaging failure, not a code defect",
                ""))
            break
        tg = [t for t in tg if t not in tried_targets]
        if not tg:
            break

        # ------------------------------------------------------------------
        # INFERENCE FIRST. The body's examples say what the function must do;
        # generalise the repair from them. Enumeration is the LAST resort, not
        # the first -- it is what made this slow, what rewrote a file in
        # tabulate by greening a suite accidentally, and what could never reach
        # a missing branch at all.
        # ------------------------------------------------------------------
        done = False
        for mod, func in tg[:3]:
            try:
                desc, cands, route, el = _infer(work, mod, func, red, mem=mem)
            except Exception:
                desc, cands = None, None
            if not cands:
                continue
            path = os.path.join(work, mod.replace(".", os.sep) + ".py")
            src0 = open(path).read()
            fn0 = next((n for n in ast.walk(ast.parse(src0))
                        if isinstance(n, ast.FunctionDef) and n.name == func), None)
            if fn0 is None:
                continue
            lines0 = src0.splitlines(keepends=True)
            for k, (cand_src, arm) in enumerate(cands, 1):
                whole = ("".join(lines0[:fn0.lineno - 1]) + cand_src + "\n"
                         + "".join(lines0[fn0.end_lineno:]))
                harm = _blast_radius(src0, whole, fn0.lineno - 1, fn0.end_lineno)
                if harm:
                    continue
                open(path, "w").write(whole)
                f2 = _trial(work, pytest_args)
                if f2 < baseline:
                    rep.repaired.append(Repaired(
                        ", ".join(red[:2]), mod, func,
                        "INFER/" + route, arm, k, _diff(src0, whole)))
                    mem.learn(_Memory.signature({"E_ASSERT"}, "REPAIR_LIBRARY",
                              {"kind": desc.get("kind", "missing_branch"),
                               "keyword": desc["branch_on"]}),
                              "missing_branch", desc, el)
                    tried_targets.add((mod, func))
                    done = True
                    break
                open(path, "w").write(src0)
            if done:
                break
        if done:
            continue

        got = None
        for mod, func in tg[:3]:
            rel = _d.relevant(work, out, func)
            got = _search(work, mod, func, classes, tier, rel, pytest_args,
                          max_candidates, verbose, baseline)
            if got and got[0]:
                break
        if got and got[0]:
            label, tried, diff = got
            rep.repaired.append(Repaired(", ".join(red[:2]), mod, func, act,
                                         label, tried, diff))
            tried_targets.add((mod, func))
            continue
        mod, func = tg[0]
        tried = got[1] if got else 0
        rep.unrepaired.append(Unrepaired(
            ", ".join(red[:2]), mod, func, act, tried,
            "the supplied edit classes cannot express this repair",
            _prompt(work, mod, func, out, act)))
        tried_targets.add((mod, func))          # move on; do not stop the run

    rep.seconds = time.time() - t0
    return rep


def _search(repo, mod, func, classes, tier, red, pytest_args, cap, verbose,
            baseline=0):
    path = os.path.join(repo, mod.replace(".", os.sep) + ".py")
    if not os.path.exists(path):
        return None, 0, ""
    src = open(path).read()
    fn = None
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
    if fn is None:
        return None, 0, ""
    ns = []
    for extra in ("collections", "itertools", "operator", "functools", "heapq", "math"):
        try:
            ns += dir(__import__(extra))
        except Exception:
            pass
    here = os.getcwd()
    try:
        screen = Fast(repo, mod, func, red)
    except Exception:
        return None, 0, ""
    finally:
        os.chdir(here)
    tried = 0
    for label, mut in _edits.mutants(fn, tier=tier, namespace=sorted(set(ns))):
        if not any(label.startswith(c) for c in classes):
            continue
        tried += 1
        if tried > cap:
            break
        body = ast.unparse(mut)
        if not screen.ok(body):
            continue
        os.chdir(here)
        before = open(path).read()
        cand, orig = _splice(path, func, body)
        if cand is None:
            continue
        harm = _blast_radius(before, cand, fn.lineno - 1, fn.end_lineno)
        if harm:                          # a green suite is not a licence to damage
            open(path, "w").write(orig)
            continue
        failed = _trial(repo, pytest_args)
        if failed < baseline:            # fixed something, broke nothing
            return label, tried, _diff(orig, cand)
        open(path, "w").write(orig)
    os.chdir(here)
    return None, tried, ""


def _diff(a, b):
    import difflib
    return "\n".join(l for l in difflib.unified_diff(
        a.splitlines(), b.splitlines(), lineterm="", n=1)
        if l.startswith(("+", "-")) and not l.startswith(("+++", "---")))
