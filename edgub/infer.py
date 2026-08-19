"""DERIVE THE REPAIR FROM THE DATA. No search space.

Enumeration asks "which of N mutations happens to pass?" -- 808 candidates for
partition, 25,057 for diff, and for diff it never found one. This asks what the
EXAMPLES SAY the function must do, and the answer is nearly complete before any
candidate exists.

    six calls to partition; two pass `pad`; those two produce LONGER output
    -> the function branches on `pad`.        Read, not searched.

    exactly one callable in scope accepts a padding keyword
    -> that is the other arm.                 Read, not searched.

    candidates remaining: 4, from 808.

The body's job is to supply the examples. The engine's job is to generalise from
them. Nothing here tries a mutation to see what sticks.
"""
import ast, inspect, importlib, sys


def _call_to(src, func):
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        return None
    best = None
    for c in ast.walk(tree):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
            if c.func.id == func:            # the TARGET, not the wrapper --
                return c                     # the examples are list(diff(...))
            best = best or c
    return best


def _shape(want):
    try:
        v = ast.literal_eval(want)
    except Exception:
        return None
    return len(v) if hasattr(v, "__len__") else 0


def branching_keyword(examples, func):
    """Which keyword's PRESENCE changes the behaviour? A fact in the data."""
    rows = []
    for call, want in examples:
        c = _call_to(call, func)
        if c is None:
            continue
        kws = {k.arg: ast.unparse(k.value) for k in c.keywords if k.arg}
        rows.append((kws, _shape(want), len(c.args)))
    keys = {k for kws, _, _ in rows for k in kws}
    for key in sorted(keys):
        with_k = [r for r in rows if key in r[0]]
        without = [r for r in rows if key not in r[0]]
        if not with_k or not without:
            continue
        # compare only calls of the SAME ARITY, else a longer positional call
        # masks the effect -- which is why diff came back silent before
        for arity in {r[2] for r in with_k} & {r[2] for r in without}:
            a = [r[1] for r in with_k if r[2] == arity and r[1] is not None]
            b = [r[1] for r in without if r[2] == arity and r[1] is not None]
            if a and b and max(a) > max(b):
                return key, with_k[0][0][key], len(with_k), len(without)
    return None


def callables_accepting(module_name, keyword, replacing=None):
    """Which callable in scope produces that effect? Its signature decides
    WHICH ARE POSSIBLE; evidence decides which is likely.

    Signature alone left `diff` ahead of `zip_longest` for partition, purely
    because it sorts first -- and it greened the suite, so nothing caught it.
    A green suite is not evidence the repair is the right one. Two signals,
    both read from the code rather than chosen by me:

      a function DEFINED IN THE SAME MODULE is a poor candidate for the other
      arm of a branch inside that module -- libraries do not usually implement
      one primitive by calling a sibling primitive;

      the arm is usually a VARIANT OF THE CALL BEING REPLACED -- zip becomes
      zip_longest. Shared prefix is the signal, and it is exactly what
      distinguishes the real answer here."""
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return []
    import os
    home = getattr(mod, "__file__", "") or ""
    out = []
    for name in dir(mod):
        f = getattr(mod, name, None)
        if not callable(f):
            continue
        try:
            inspect.signature(f).bind_partial(**{keyword: None})
        except (TypeError, ValueError):
            continue
        native = os.path.abspath(getattr(
            sys.modules.get(getattr(f, "__module__", ""), None), "__file__", "") or "")
        same_module = bool(native) and bool(home) and \
            os.path.abspath(home) == native
        prefix = 0
        if replacing:
            while prefix < min(len(name), len(replacing)) and \
                    name[prefix] == replacing[prefix]:
                prefix += 1
        out.append((same_module, -prefix, name))
    out.sort()
    return [n for _, _, n in out]


def replaced_callee(src, func):
    """The call the branch will wrap -- so the arm can be ranked against it."""
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            names = [c.func.id for c in ast.walk(n)
                     if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
            for nm in names:
                if nm not in ("len", "list", "tuple", "iter", "range", "int", "str"):
                    return nm
    return None


def infer(examples, func, module_name, pad_keywords=("fillvalue",), src=None):
    """Return a derived repair description, or None. Never a search."""
    b = branching_keyword(examples, func)
    if not b:
        return None
    key, shown, n_with, n_without = b
    replacing = replaced_callee(src, func) if src else None
    arms = []
    for kw in pad_keywords:
        arms += [(c, kw) for c in callables_accepting(module_name, kw, replacing)]
    return {
        "kind": "missing_branch",
        "keyword": key,
        "evidence": "%d examples pass `%s` and produce longer output; %d do not"
                    % (n_with, key, n_without),
        "arms": arms,
        "candidates": max(len(arms), 1),
    }


def sentinel_for(src, func, keyword):
    """What marks the keyword ABSENT? Read from the function itself:
    a default in the signature, or kwargs.get('key', SENTINEL)."""
    for n in ast.walk(ast.parse(src)):
        if not (isinstance(n, ast.FunctionDef) and n.name == func):
            continue
        args = n.args
        for a, d in zip(args.args[-len(args.defaults):] if args.defaults else [],
                        args.defaults):
            if a.arg == keyword:
                return ast.unparse(d)
        for a, d in zip(args.kwonlyargs, args.kw_defaults):
            if a.arg == keyword and d is not None:
                return ast.unparse(d)
        for c in ast.walk(n):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) \
               and c.func.attr == "get" and len(c.args) == 2 \
               and isinstance(c.args[0], ast.Constant) and c.args[0].value == keyword:
                return ast.unparse(c.args[1])
    return None


def synthesise(src, func, keyword, sentinel, arm_callee, arm_keyword):
    """Write the missing branch. The shape is determined; nothing is tried."""
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == func), None)
    if fn is None:
        return None
    for holder in ast.walk(fn):
        body = getattr(holder, "body", None)
        if not isinstance(body, list):
            continue
        for i, st in enumerate(list(body)):
            calls = [c for c in ast.walk(st)
                     if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
            if not calls:
                continue
            alt = copy.deepcopy(st)
            for c in ast.walk(alt):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                    c.func = ast.Name(id=arm_callee, ctx=ast.Load())
                    c.keywords = list(c.keywords) + [ast.keyword(
                        arg=arm_keyword, value=ast.Name(id=keyword, ctx=ast.Load()))]
                    break
            test = ast.Compare(left=ast.Name(id=keyword, ctx=ast.Load()),
                               ops=[ast.Is()],
                               comparators=[ast.parse(sentinel, mode="eval").body])
            node = ast.If(test=test, body=[copy.deepcopy(st)], orelse=[alt])
            t2 = copy.deepcopy(fn)
            for h2 in ast.walk(t2):
                b2 = getattr(h2, "body", None)
                if isinstance(b2, list) and len(b2) == len(body) and i < len(b2) \
                   and ast.dump(b2[i]) == ast.dump(st):
                    b2[i] = node
                    ast.fix_missing_locations(t2)
                    yield ast.unparse(t2)
                    break


import copy  # noqa: E402  (used by synthesise)
