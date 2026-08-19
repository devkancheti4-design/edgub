"""EDIT MATERIAL — lazy, incremental, deduplicated.

WHAT WAS SLOW, and it was not the checking.
  * mutants() built the ENTIRE candidate list before anything was filtered,
    deep-copying the whole function once per candidate. groupby at tier 3 meant
    5,572 deepcopies before the first check ran. That, not the doctests, was
    the cost.
  * every escalation regenerated the tiers below it, re-testing everything
    already refuted. The law asked for MORE material, never for the old
    material again.

BOTH FIXED HERE.
  * mutants() is a GENERATOR. Nothing is built until it is asked for, so a
    search that finds a repair in the first dozen candidates pays for a dozen.
  * min_tier generates only the classes a given escalation ADDS.
  * identical results are emitted once.

Nothing was removed. Every candidate the old version could produce, this one
still produces -- just later, and only if asked.

TIERS
  0  rearrange   binop, comparison, constant, invert if, negate slice,
                 swap args, swap a tuple, unwrap a call, delete a statement
  1  rename      replace an in-scope name; repair an identifier that does not
                 resolve, against the namespace that should hold it
  2  arity       drop an argument at a call
  3  author      insert continue/break anywhere inside a loop; insert a.m(b)
"""
import ast, copy, difflib, builtins

BINOPS = [ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod]
CMPOPS = [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq]
METHODS = ["update", "extend", "append", "add", "sort", "reverse"]


def _stamp(t):
    for i, n in enumerate(ast.walk(t)):
        n._sid = i
    return t


def _find(tree, sid):
    for n in ast.walk(tree):
        if getattr(n, "_sid", None) == sid:
            return n
    return None


def _names_in(fn):
    out, seen = [], set()
    for a in fn.args.args:
        if a.arg not in seen:
            seen.add(a.arg); out.append(a.arg)
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id not in seen:
            seen.add(n.id); out.append(n.id)
    return out


def mutants(fn, tier=0, namespace=(), min_tier=0):
    """Yield (label, tree). Lazy: nothing is copied until it is asked for."""
    base = _stamp(copy.deepcopy(fn))
    seen = set()

    def emit(label, sid, mutate):
        t = copy.deepcopy(base)
        if mutate is None:                      # unwrap: replace node with arg
            class _U(ast.NodeTransformer):
                def generic_visit(self, nd):
                    nd = super().generic_visit(nd)
                    if getattr(nd, "_sid", None) == sid and isinstance(nd, ast.Call) \
                       and len(nd.args) == 1:
                        return nd.args[0]
                    return nd
            _U().visit(t)
        else:
            n = _find(t, sid)
            if n is None:
                return None
            try:
                mutate(t, n)
            except Exception:
                return None
        ast.fix_missing_locations(t)
        key = ast.dump(t)
        if key in seen or key == ast.dump(base):
            return None
        seen.add(key)
        return (label, t)

    def want(t):
        return min_tier <= t <= tier

    nodes = list(ast.walk(base))

    if want(0):
        for n in nodes:
            sid = n._sid
            if isinstance(n, ast.BinOp):
                for o in BINOPS:
                    if type(n.op) is not o:
                        r = emit("binop->%s" % o.__name__, sid,
                                 lambda t, m, o=o: setattr(m, "op", o()))
                        if r: yield r
            elif isinstance(n, ast.Compare) and len(n.ops) == 1:
                for o in CMPOPS:
                    if type(n.ops[0]) is not o:
                        r = emit("cmp->%s" % o.__name__, sid,
                                 lambda t, m, o=o: m.ops.__setitem__(0, o()))
                        if r: yield r
            elif isinstance(n, ast.Constant) and isinstance(n.value, int) \
                    and not isinstance(n.value, bool):
                for v in (n.value + 1, n.value - 1, -n.value, 0, 1):
                    if v != n.value:
                        r = emit("const %s->%s" % (n.value, v), sid,
                                 lambda t, m, v=v: setattr(m, "value", v))
                        if r: yield r
            elif isinstance(n, ast.If):
                r = emit("invert if", sid, lambda t, m: setattr(
                    m, "test", ast.UnaryOp(op=ast.Not(), operand=m.test)))
                if r: yield r
            elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice):
                def neg(t, m):
                    for f in ("lower", "upper"):
                        v = getattr(m.slice, f, None)
                        if v is not None:
                            setattr(m.slice, f, ast.UnaryOp(op=ast.USub(), operand=v))
                r = emit("negate slice", sid, neg)
                if r: yield r
            elif isinstance(n, ast.Tuple) and len(n.elts) >= 2:
                r = emit("swap tuple 0<->1", sid, lambda t, m: m.elts.__setitem__(
                    slice(0, 2), [m.elts[1], m.elts[0]]))
                if r: yield r
            elif isinstance(n, ast.Call):
                if len(n.args) == 1:
                    r = emit("unwrap call", sid, None)
                    if r: yield r
                if len(n.args) >= 2:
                    r = emit("swap args", sid, lambda t, m: m.args.__setitem__(
                        slice(0, 2), [m.args[1], m.args[0]]))
                    if r: yield r
        for holder in nodes:
            b = getattr(holder, "body", None)
            if isinstance(b, list) and len(b) > 1:
                for j in range(len(b)):
                    if isinstance(b[j], (ast.Return, ast.Raise)):
                        continue
                    r = emit("delete stmt %d" % (j + 1), holder._sid,
                             lambda t, m, j=j: m.body.pop(j))
                    if r: yield r

    if want(1):
        local = _names_in(base)
        for n in nodes:
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in local:
                for other in local:
                    if other != n.id:
                        r = emit("name %s->%s" % (n.id, other), n._sid,
                                 lambda t, m, o=other: setattr(m, "id", o))
                        if r: yield r
        if namespace:
            known = set(namespace) | set(dir(builtins))
            for n in nodes:
                if isinstance(n, ast.Attribute):
                    for c in difflib.get_close_matches(n.attr, list(namespace), 3, 0.6):
                        if c != n.attr:
                            r = emit("attr %s->%s" % (n.attr, c), n._sid,
                                     lambda t, m, c=c: setattr(m, "attr", c))
                            if r: yield r
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) \
                        and n.id not in known and n.id not in local:
                    for c in difflib.get_close_matches(n.id, list(known), 3, 0.6):
                        if c != n.id:
                            r = emit("name %s->%s" % (n.id, c), n._sid,
                                     lambda t, m, c=c: setattr(m, "id", c))
                            if r: yield r

    if want(2):
        for n in nodes:
            if isinstance(n, ast.Call) and len(n.args) >= 1:
                for j in range(len(n.args)):
                    r = emit("drop arg %d" % j, n._sid,
                             lambda t, m, j=j: m.args.pop(j))
                    if r: yield r

    if want(3):
        loops = [l for l in nodes if isinstance(l, (ast.For, ast.While))]
        inside = set()
        for l in loops:
            for nd in ast.walk(l):
                if isinstance(getattr(nd, "body", None), list):
                    inside.add(nd._sid)
        for sid in sorted(inside):
            holder = _find(base, sid)
            if holder is None:
                continue
            for pos in range(len(holder.body) + 1):
                for kind, node in (("continue", ast.Continue), ("break", ast.Break)):
                    r = emit("insert %s @%d" % (kind, pos), sid,
                             lambda t, m, p=pos, nd=node: m.body.insert(p, nd()))
                    if r: yield r
        names = _names_in(base)
        for holder in nodes:
            b = getattr(holder, "body", None)
            if not isinstance(b, list):
                continue
            for pos in range(len(b)):
                for a in names:
                    for other in names:
                        if a == other:
                            continue
                        for meth in METHODS:
                            stmt = ast.Expr(value=ast.Call(
                                func=ast.Attribute(value=ast.Name(id=a, ctx=ast.Load()),
                                                   attr=meth, ctx=ast.Load()),
                                args=[ast.Name(id=other, ctx=ast.Load())], keywords=[]))
                            r = emit("insert %s.%s(%s) @%d" % (a, meth, other, pos),
                                     holder._sid,
                                     lambda t, m, s=stmt, p=pos: m.body.insert(p, copy.deepcopy(s)))
                            if r: yield r
