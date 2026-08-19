"""CAN IT INVENT AN EDIT CLASS IT WAS NEVER GIVEN?

Target: the two bugs every supplied edit class fails on. Both were made by
deleting an if/else. The engine gets six structural primitives, none of which
repairs anything alone, and must compose one that does.

Scored strictly: the whole 185-test suite must go green, and the bugs already
solved by the existing classes must stay solved.
"""
import os, re, sys, ast, json, shutil, subprocess, itertools, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import primitives as P
import harness as F

PY = sys.executable
CAP = 60000


def attempt(repo, cfg, mod, func, red):
    path = os.path.join(repo, mod.replace(".", "/") + ".py")
    src = open(path).read()
    tree = ast.parse(src)
    fn = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
    if fn is None:
        return None, 0
    modnames = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    modnames += re.findall(r"^from [\w.]+ import (\w+)", src, re.M)
    modnames += re.findall(r"^import (\w+)", src, re.M)
    lines = src.splitlines(keepends=True)
    a, b = fn.lineno - 1, fn.end_lineno
    ind = len(lines[a]) - len(lines[a].lstrip())
    tried = 0
    for label, holder, si, node in P.compositions(fn, modnames):
        tried += 1
        if tried > CAP:
            return None, tried
        newfn = __import__("copy").deepcopy(fn)
        tgt = None
        for h in ast.walk(newfn):
            if isinstance(getattr(h, "body", None), list) and \
               len(h.body) == len(holder.body) and \
               ast.dump(h.body[si]) == ast.dump(holder.body[si]):
                tgt = h
                break
        if tgt is None:
            continue
        tgt.body[si] = node
        ast.fix_missing_locations(newfn)
        body = ast.unparse(newfn)
        if ind:
            body = "\n".join((" " * ind) + l if l.strip() else l
                             for l in body.splitlines())
        cand = "".join(lines[:a]) + body + "\n" + "".join(lines[b:])
        try:
            compile(cand, "<c>", "exec")
        except SyntaxError:
            continue
        open(path, "w").write(cand)
        try:
            rr = subprocess.run([PY, "-m", "pytest", "-q", "--tb=no", "-p",
                                 "no:randomly"] + red, cwd=repo,
                                capture_output=True, text=True, timeout=60)
            cheap = "failed" not in (rr.stdout + rr.stderr)
        except subprocess.TimeoutExpired:
            cheap = False
        if cheap:
            f2, _ = F.run_suite(repo, cfg["ignore"])
            if f2 == 0:
                return label, tried
        open(path, "w").write(src)
    open(path, "w").write(src)
    return None, tried


TARGETS = {"diff_nodefault": ("toolz.itertoolz", "diff"),
           "partition_alwayspad": ("toolz.itertoolz", "partition")}
# Both were made by DELETING an if/else. No supplied edit class restores a
# branch; that is precisely why they are the targets.

if __name__ == "__main__":
    cfg = F.REPOS["hard"]
    work = os.path.join(HERE, "work")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    print("CAN IT COMPOSE AN EDIT CLASS NOBODY WROTE?\n")
    print("primitives supplied: WRAP_IF, ADD_ELSE, CLONE, SUBST_CALLEE, ADD_KW, CMP")
    print("none of them repairs anything alone\n")
    print("%-22s %-58s %s" % ("bug", "composition found", "tried"))
    ok = 0
    for bid, (mod, func) in TARGETS.items():
        repo = os.path.join(work, bid)
        shutil.copytree(os.path.join(cfg["root"], bid), repo,
                        ignore=shutil.ignore_patterns("__pycache__"))
        failed, out = F.run_suite(repo, cfg["ignore"])
        red = F.failing_nodes(out)
        t0 = time.time()
        label, tried = attempt(repo, cfg, mod, func, red)
        ok += bool(label)
        print("%-22s %-58s %d  (%.0fs)" % (bid, label or "-- none --", tried,
                                           time.time() - t0), flush=True)
    print("\n  invented an edit class: %d/2" % ok)
