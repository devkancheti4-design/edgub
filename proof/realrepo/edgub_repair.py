"""DOES THE EDGUB LAW GENERALISE ONCE THE ACTS MEAN THE RIGHT THING?

THE CLAIM UNDER TEST. edgub scored 0/10 on real repositories and weakened seven
test suites. I called that a failure of the law. That was wrong, and this file
tests the correction.

The law is a MAPPING from observation to act INDEX. The act LIST is mine, and so
is the alignment -- ACT[i] answers BITS[i], which is why RELAX_ASSERT sits at
index 7 answering E_ASSERT at bit 7. The law never chose that pairing. It
learned a map over acts I supplied, measured on toy scripts where weakening the
assertion genuinely was the fix.

So: edgub.decide() is used VERBATIM, byte for byte. Only what the acts MEAN is
corrected. Every act now repairs the library instead of suppressing the symptom,
and each one routes to the edit classes appropriate to its fault:

    index 1  E_NAME      -> repair an identifier
    index 2  E_TYPE      -> arity and wrapping
    index 3  E_INDEX     -> constants and slices
    index 5  E_ATTR      -> repair an attribute
    index 7  E_ASSERT    -> THE LIBRARY IS WRONG. Repair it.      <-- the inversion
    index 10 SELF        -> the whole space

If the law generalises, the same decide() that produced seven test-weakenings
now routes seven semantic bugs into a semantic repair search.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..")))
import os, re, sys, ast, json, shutil, subprocess, time, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import edgub                      # decide() and BITS used verbatim
import edits
import harness as F

PY = sys.executable

# WHAT EACH ACT NOW MEANS: a set of edit-class prefixes, and how wide to look.
SEMANTIC = ("binop", "cmp", "const", "invert", "swap", "unwrap", "negate",
            "delete", "name", "attr", "drop", "insert")
ACT_CLASSES = {
 0:  (None, 0),                                          # SHIP
 1:  (("name", "attr"), 1),                              # E_NAME
 2:  (("drop", "unwrap", "swap", "const", "name", "cmp", "attr"), 2),  # E_TYPE
 3:  (("const", "negate", "swap"), 1),                   # E_INDEX
 4:  (("const", "binop", "invert"), 1),                  # E_ZERO
 5:  (("attr", "name"), 1),                              # E_ATTR
 6:  (("const", "unwrap", "cmp"), 1),                    # E_VALUE
 7:  (SEMANTIC, 3),                                      # E_ASSERT -> REPAIR LIBRARY
 8:  (("const",), 1),                                    # E_RECUR
 9:  (("name", "attr"), 1),                              # ADD_IMPORT slot
 10: (SEMANTIC, 3),                                      # AUTHOR_SUCCESSOR
}


def observe(out):
    o = set()
    for name, bit in (("NameError", "E_NAME"), ("TypeError", "E_TYPE"),
                      ("IndexError", "E_INDEX"), ("KeyError", "E_INDEX"),
                      ("ZeroDivisionError", "E_ZERO"), ("AttributeError", "E_ATTR"),
                      ("ValueError", "E_VALUE"), ("AssertionError", "E_ASSERT"),
                      ("RecursionError", "E_RECUR")):
        if name in out:
            o.add(bit)
    return o or {"OUT_WRONG"}


def search(repo, mod, func, classes, tier, cfg, red, keep=12):
    path = os.path.join(repo, mod.replace(".", "/") + ".py")
    src = open(path).read()
    fn = None
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
    if fn is None:
        return None, 0
    ns = []
    for extra in ("collections", "itertools", "operator", "heapq"):
        try:
            ns += dir(__import__(extra))
        except Exception:
            pass
    lines = src.splitlines(keepends=True)
    a, b = fn.lineno - 1, fn.end_lineno
    ind = len(lines[a]) - len(lines[a].lstrip())
    tried = 0
    for label, mut in edits.mutants(fn, tier=tier, namespace=sorted(set(ns))):
        if not any(label.startswith(c) for c in classes):
            continue
        tried += 1
        body = ast.unparse(mut)
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
                                capture_output=True, text=True, timeout=90)
            cheap = "failed" not in (rr.stdout + rr.stderr)
        except subprocess.TimeoutExpired:
            cheap = False
        if cheap:
            f2, _ = F.run_suite(repo, cfg["ignore"])
            if f2 == 0:
                return label, tried
        open(path, "w").write(src)
        if tried > 40000:
            return None, tried
    open(path, "w").write(src)
    return None, tried


if __name__ == "__main__":
    cfg = F.REPOS["hard"]
    bugs = json.load(open(os.path.join(cfg["root"], "bugs.json")))
    work = os.path.join(HERE, "work_edgub_repair")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    print("EDGUB'S decide() VERBATIM — only what the acts MEAN is corrected\n")
    print("%-20s %-14s %-6s %-26s %s" % ("bug", "observation", "act#", "authored", "tried"))
    ok = 0
    for b in bugs:
        repo = os.path.join(work, b["id"])
        shutil.copytree(os.path.join(cfg["root"], b["id"]), repo,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        failed, out = F.run_suite(repo, cfg["ignore"])
        obs = observe(out)
        idx = edgub.decide(edgub.sit(obs))          # UNCHANGED
        classes, tier = ACT_CLASSES.get(idx, (SEMANTIC, 3))
        tg = F.targets(repo, out, cfg)
        red = F.failing_nodes(out)
        label, tried = (None, 0)
        if classes and tg:
            for mod, func in tg[:2]:
                label, tried = search(repo, mod, func, classes, tier, cfg, red)
                if label:
                    break
        ok += bool(label)
        print("%-20s %-14s %-6d %-26s %d"
              % (b["id"], "+".join(sorted(obs))[:14], idx,
                 label or "-- none --", tried), flush=True)
    print("\n  edgub's law, acts corrected: %d/%d   0 tokens" % (ok, len(bugs)))
