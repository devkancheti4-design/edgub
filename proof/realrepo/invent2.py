"""DOES THE DATA NARROW THE INVENTION? A guided composition.

The first attempt enumerated WRAP_IF x ADD_ELSE x every name x every comparison
x every callee -- over 400,000 candidates for `diff`, about thirty hours. That
was a design fault of mine: I supplied primitives with no narrowing, which is
exactly the brute force the routing exists to avoid.

Everything the composition needs is visible in the data:

  the failing test names the keyword          diff(..., default=None)
  the signature names the parameters          diff(*seqs, **kwargs) -> default, key
  the module names its own sentinels          no_default, no_pad
  the module names the callables it imports   zip, zip_longest

So the ingredients are READ, not enumerated:

  condition operands  <- parameters and module-level sentinels ONLY
  alternative callee  <- callables the module already uses, AND ONLY THOSE WHOSE
                         SIGNATURE ACCEPTS THE KEYWORD. `fillvalue` is accepted
                         by zip_longest and by nothing else in scope, so the
                         keyword the test passes names the callee: 41 -> 1.
  keyword to add      <- keywords that appear at real call sites ONLY

Nothing here knows what the repair is. It knows where to look for the parts.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import os, re, ast, sys, copy, json, time, shutil, subprocess
import harness as H
import primitives as P

PY = sys.executable
CMPOPS = [ast.Eq, ast.NotEq, ast.Is, ast.IsNot]


_ACC = {}


def accepts(callee, kw, repo, mod):
    """Does this callable take that keyword? Read its signature -- introspection,
    not judgement. A candidate that cannot take the keyword the failing test
    passes is not a candidate."""
    key = (callee, kw)
    if key in _ACC:
        return _ACC[key]
    code = ("import sys, inspect, importlib; sys.path.insert(0, %r);\n"
            "m = importlib.import_module(%r)\n"
            "f = getattr(m, %r, None) or __builtins__.get(%r) if isinstance("
            "__builtins__, dict) else getattr(m, %r, None)\n"
            "import builtins\n"
            "f = getattr(m, %r, None) or getattr(builtins, %r, None)\n"
            "try:\n"
            "    inspect.signature(f).bind_partial(**{%r: None}); print(1)\n"
            "except Exception: print(0)\n"
            % (os.path.abspath(repo), mod, callee, callee, callee, callee,
               callee, kw))
    try:
        r = subprocess.run([PY, "-c", code], cwd=repo, capture_output=True,
                           text=True, timeout=30)
        ok = r.stdout.strip().endswith("1")
    except Exception:
        ok = True                      # unknown signature: do not exclude it
    _ACC[key] = ok
    return ok


def read_ingredients(repo, mod, func, red):
    """Everything the composition may use, read off the code and the tests."""
    path = os.path.join(repo, mod.replace(".", "/") + ".py")
    src = open(path).read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func)

    params = [a.arg for a in fn.args.args]
    if fn.args.vararg:
        params.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        params.append(fn.args.kwarg.arg)
    # names the body binds -- kwargs.get('default', ...) makes `default` local
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            params.append(n.id)

    # module-level sentinels: bare assignments at module scope
    sentinels = [t.id for st in tree.body if isinstance(st, ast.Assign)
                 for t in st.targets if isinstance(t, ast.Name)]

    # callables the module actually uses
    used = {n.func.id for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    imported = set(re.findall(r"^from [\w.]+ import (\w+)", src, re.M))
    imported |= set(re.findall(r"^import (\w+)", src, re.M))
    callees = sorted((used | imported) - {func})

    # keywords that appear at real call sites, in the module AND the failing tests
    kws = {k.arg for n in ast.walk(tree) if isinstance(n, ast.Call)
           for k in n.keywords if k.arg}
    for node in red:
        f = os.path.join(repo, node.partition("::")[0])
        if os.path.exists(f):
            try:
                t2 = ast.parse(open(f).read())
            except SyntaxError:
                continue
            for n in ast.walk(t2):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                   and n.func.id == func:
                    kws |= {k.arg for k in n.keywords if k.arg}
    return fn, sorted(set(params)), sorted(set(sentinels)), callees, sorted(kws)


def guided(repo, cfg, mod, func, red):
    fn, params, sentinels, callees, kws = read_ingredients(repo, mod, func, red)
    path = os.path.join(repo, mod.replace(".", "/") + ".py")
    src = open(path).read()
    lines = src.splitlines(keepends=True)
    a, b = fn.lineno - 1, fn.end_lineno
    ind = len(lines[a]) - len(lines[a].lstrip())
    print("      read from the data: %d params, %d sentinels, %d callees, %d keywords"
          % (len(params), len(sentinels), len(callees), len(kws)), flush=True)

    holders = [h for h in ast.walk(fn) if isinstance(getattr(h, "body", None), list)]
    tried = 0
    for holder in holders:
        for si, stmt in enumerate(list(holder.body)):
            if isinstance(stmt, (ast.FunctionDef, ast.Raise)):
                continue
            alts = []
            for c in callees:
                a1 = P.SUBST_CALLEE(stmt, c)
                if a1 is None:
                    continue
                alts.append(a1)
                for k in kws:
                    if not accepts(c, k, repo, mod):    # the keyword names the callee
                        continue
                    for v in params:
                        a2 = P.ADD_KW(a1, k, v)
                        if a2 is not None:
                            alts.append(a2)
            for p in params:
                for sen in sentinels:
                    if p == sen:
                        continue
                    for op in CMPOPS:
                        for alt in alts:
                            tried += 1
                            newfn = copy.deepcopy(fn)
                            tgt = None
                            for h in ast.walk(newfn):
                                if isinstance(getattr(h, "body", None), list) and \
                                   len(h.body) == len(holder.body) and \
                                   ast.dump(h.body[si]) == ast.dump(holder.body[si]):
                                    tgt = h
                                    break
                            if tgt is None:
                                continue
                            node = P.ADD_ELSE(P.WRAP_IF(stmt, P.CMP(p, op, sen)), alt)
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
                                rr = subprocess.run(
                                    [PY, "-m", "pytest", "-q", "--tb=no", "-p",
                                     "no:randomly"] + red, cwd=repo,
                                    capture_output=True, text=True, timeout=60)
                                cheap = "failed" not in (rr.stdout + rr.stderr)
                            except subprocess.TimeoutExpired:
                                cheap = False
                            if cheap:
                                f2, _ = H.run_suite(repo, cfg["ignore"])
                                if f2 == 0:
                                    return ("if %s %s %s: <orig> else: <alt>"
                                            % (p, op.__name__, sen)), tried, cand
                            open(path, "w").write(src)
    open(path, "w").write(src)
    return None, tried, None


TARGETS = {"diff_nodefault": ("toolz.itertoolz", "diff"),
           "partition_alwayspad": ("toolz.itertoolz", "partition")}

if __name__ == "__main__":
    cfg = H.REPOS["hard"]
    work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_invent2")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    print("GUIDED INVENTION — the data picks the ingredients\n")
    ok = 0
    for bid, (mod, func) in TARGETS.items():
        repo = os.path.join(work, bid)
        shutil.copytree(os.path.join(cfg["root"], bid), repo,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        failed, out = H.run_suite(repo, cfg["ignore"])
        red = H.failing_nodes(out)
        print("   %s" % bid, flush=True)
        t0 = time.time()
        label, tried, cand = guided(repo, cfg, mod, func, red)
        ok += bool(label)
        print("      %-48s %d tried  %.0fs"
              % (label or "-- none --", tried, time.time() - t0), flush=True)
        if cand:
            import difflib
            orig = open(os.path.join(cfg["root"], bid,
                                     mod.replace(".", "/") + ".py")).read()
            d = [l for l in difflib.unified_diff(orig.splitlines(),
                                                 cand.splitlines(), n=0, lineterm="")
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            for l in d[:10]:
                print("        %s" % l)
    print("\n  invented from data: %d/2" % ok)
