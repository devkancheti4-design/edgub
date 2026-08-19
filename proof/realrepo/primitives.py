"""STRUCTURAL PRIMITIVES. None of these is a repair.

The two bugs no supplied edit class can reach -- diff_nodefault and
partition_alwayspad -- were made by DELETING a branch. Restoring one means
writing an `if/else` that was never in the file: a condition, the original
statement, and a second statement that differs from it.

No existing edit class does that, and I am not going to write one. Instead
these six primitives are supplied. Each is a single structural operation on an
AST. NOT ONE OF THEM REPAIRS ANYTHING BY ITSELF:

    WRAP_IF        put a statement under `if <test>:`
    ADD_ELSE       give an existing `if` an `else:` branch
    CLONE          duplicate a statement
    SUBST_CALLEE   change which function a call calls
    ADD_KW         add a keyword argument to a call
    CMP            build `a <op> b` from two in-scope names

A repair, if one exists, is a COMPOSITION of these. Composing them is the
engine's job -- exactly as `ntzb` was composed from `&`, `-` and `>>` rather
than supplied whole.
"""
import ast, copy

CMPOPS = [ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.Lt, ast.Gt]


def CMP(a, op, b):
    return ast.Compare(left=ast.Name(id=a, ctx=ast.Load()), ops=[op()],
                       comparators=[ast.Name(id=b, ctx=ast.Load())])


def WRAP_IF(stmt, test):
    return ast.If(test=test, body=[copy.deepcopy(stmt)], orelse=[])


def ADD_ELSE(ifnode, stmt):
    n = copy.deepcopy(ifnode)
    n.orelse = [copy.deepcopy(stmt)]
    return n


def CLONE(stmt):
    return copy.deepcopy(stmt)


def SUBST_CALLEE(stmt, newname):
    n = copy.deepcopy(stmt)
    for c in ast.walk(n):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
            c.func = ast.Name(id=newname, ctx=ast.Load())
            return n
    return None


def ADD_KW(stmt, key, valname):
    n = copy.deepcopy(stmt)
    for c in ast.walk(n):
        if isinstance(c, ast.Call):
            c.keywords = list(c.keywords) + [ast.keyword(
                arg=key, value=ast.Name(id=valname, ctx=ast.Load()))]
            return n
    return None


def scope_names(fn, module_names):
    """Names the composition may use: the function's own, plus the module's."""
    local = [a.arg for a in fn.args.args]
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id not in local:
            local.append(n.id)
    return local, sorted(set(module_names))


def compositions(fn, module_names, kw_keys=("fillvalue", "default", "key", "pad")):
    """Every composition of the primitives, lazily. The engine's search space.

    shape:  stmt S  ->  WRAP_IF(S, CMP(a, op, b)) then ADD_ELSE(that, S')
            where S' is CLONE(S) with SUBST_CALLEE and/or ADD_KW applied.
    """
    local, mod = scope_names(fn, module_names)
    callables = [m for m in mod if not m.startswith("_")][:60]
    holders = [h for h in ast.walk(fn) if isinstance(getattr(h, "body", None), list)]
    for holder in holders:
        for si, stmt in enumerate(list(holder.body)):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.FunctionDef)):
                continue
            alts = []
            for c in callables:
                a1 = SUBST_CALLEE(stmt, c)
                if a1 is not None:
                    alts.append(("callee->%s" % c, a1))
                    for k in kw_keys:
                        for v in local:
                            a2 = ADD_KW(a1, k, v)
                            if a2 is not None:
                                alts.append(("callee->%s +%s=%s" % (c, k, v), a2))
            for k in kw_keys:
                for v in local:
                    a3 = ADD_KW(stmt, k, v)
                    if a3 is not None:
                        alts.append(("+%s=%s" % (k, v), a3))
            for a in local:
                for b in local:
                    if a == b:
                        continue
                    for op in CMPOPS:
                        base = WRAP_IF(stmt, CMP(a, op, b))
                        for label, alt in alts:
                            node = ADD_ELSE(base, alt)
                            yield ("WRAP_IF(%s %s %s) + ADD_ELSE(%s)"
                                   % (a, op.__name__, b, label), holder, si, node)
