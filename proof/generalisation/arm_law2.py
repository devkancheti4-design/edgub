"""ARM LAW, SUPPLIED FAIRLY — and this time the LAW actually drives.

WHAT WAS WRONG WITH THE FIRST RUN. It was one fixed pass over a hard-coded
edit set. There was no decide(), no acts, no escalation: the law was never
called. Meanwhile the model arm had an interpreter, seven tool calls and ~45k
tokens of reasoning per batch. That is not a comparison, it is a handicap.

WHAT IS EQUAL NOW
    the data          the SAME six examples. No extra examples, ever.
    the effort        the model spent reasoning; the law spends escalation
                      rounds -- widening its own material and budget.
    the judge         the SAME twenty held-out inputs.

WHAT THE LAW DECIDES, every round, with ENGINE_LAW.decide and nothing else:
    BUILT  + one behaviour fits          -> SHIP
    BUILT  + several behaviours fit      -> the six do not determine it (AMB)
    no fit + material not widest         -> UNREAD  -> ADD_MATERIAL
    no fit + budget not deepest          -> CAPPED  -> RAISE_BUDGET

MATERIAL, IN TIERS -- the thing I withheld last time:
    0  the blind set        n+1, n-1, -n, 0, 1
    1  + every constant ALREADY IN THE FUNCTION      (P03 needed 4; it was there)
    2  + every value visible in the SIX EXAMPLES
    3  + a bounded numeric sweep, -64..64            (P02 needed 7)
"""
import ast, sys, json, copy, itertools, os

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ENGINE_LAW as EL

BINOPS = [ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod]
CMPOPS = [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq]
CAP_CANDIDATES = 400000

# The search must never touch the inputs it will be judged on. Candidates are
# separated from one another on PROBE -- inputs the law picks for itself,
# disjoint from both the six examples and the twenty held-out. Without this the
# search sees the judging inputs and the model never did, which is a leak even
# though the ANSWERS are never used.
PROBE = [14, 16, 18, 20, 22, 24, 26, 27, 29, 30,
         31, 32, 34, 35, 36, 60, 70, 80, 90, 100]


class _Stop(Exception):
    pass


def _limited(fn, x, limit=30000):
    n = 0
    def tr(f, e, a):
        nonlocal n
        n += 1
        if n > limit:
            raise _Stop()
        return tr
    sys.settrace(tr)
    try:
        return fn(x)
    finally:
        sys.settrace(None)


def run(src, xs):
    ns = {}
    try:
        exec(src, ns)
    except Exception:
        return None
    out = []
    for x in xs:
        try:
            out.append(_limited(ns["f"], x))
        except Exception:
            return None
    return out


def _stamp(t):
    for i, n in enumerate(ast.walk(t)):
        n._sid = i
    return t


def sites(fn):
    """Every place a single generic edit can be made."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.BinOp):
            out.append(("binop", n._sid))
        elif isinstance(n, ast.Compare) and len(n.ops) == 1:
            out.append(("cmp", n._sid))
        elif isinstance(n, ast.Constant) and isinstance(n.value, int) \
                and not isinstance(n.value, bool):
            out.append(("const", n._sid))
        elif isinstance(n, ast.If):
            out.append(("if", n._sid))
        elif isinstance(n, ast.Call) and len(n.args) >= 2:
            out.append(("swap", n._sid))
        elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice):
            out.append(("slice", n._sid))
    for holder in ast.walk(fn):
        b = getattr(holder, "body", None)
        if isinstance(b, list) and len(b) > 1:
            for j in range(len(b)):
                out.append(("del%d" % j, holder._sid))
    return out


def edits_at(kind, node, consts):
    """The alternatives available at one site, given the CURRENT material."""
    if kind == "binop":
        return [("op", o) for o in BINOPS if type(node.op) is not o]
    if kind == "cmp":
        return [("cmp", o) for o in CMPOPS if type(node.ops[0]) is not o]
    if kind == "const":
        return [("val", v) for v in consts if v != node.value]
    if kind == "if":
        return [("not", None)]
    if kind == "swap":
        return [("swap", None)]
    if kind == "slice":
        return [("neg", None)]
    if kind.startswith("del"):
        return [("del", int(kind[3:]))]
    return []


def apply_edits(fn, plan):
    """plan: [(sid, kind, edit)] -- returns a new source string, or None."""
    t = copy.deepcopy(fn)
    idx = {n._sid: n for n in ast.walk(t)}
    for sid, kind, (etype, val) in plan:
        n = idx.get(sid)
        if n is None:
            return None
        if etype == "op":
            n.op = val()
        elif etype == "cmp":
            n.ops[0] = val()
        elif etype == "val":
            n.value = val
        elif etype == "not":
            n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
        elif etype == "swap":
            n.args[0], n.args[1] = n.args[1], n.args[0]
        elif etype == "neg":
            for f in ("lower", "upper"):
                v = getattr(n.slice, f, None)
                if v is not None:
                    setattr(n.slice, f, ast.UnaryOp(op=ast.USub(), operand=v))
        elif etype == "del":
            if val >= len(n.body) or len(n.body) < 2:
                return None
            del n.body[val]
    ast.fix_missing_locations(t)
    try:
        return "def " + ast.unparse(t).split("def ", 1)[1]
    except Exception:
        return None


def material(tier, fn_consts, ex_vals):
    c = {0, 1, -1}
    c |= {v + d for v in fn_consts for d in (1, -1)} | {-v for v in fn_consts}
    if tier >= 1:
        c |= set(fn_consts)                        # the function's OWN constants
    if tier >= 2:
        c |= set(ex_vals) | {abs(v) for v in ex_vals}
    if tier >= 3:
        c |= set(range(-64, 65))                   # bounded numeric sweep
    return sorted(c)


def search(item, tier, depth, log):
    fn = _stamp(ast.parse(item["broken"]).body[0])
    idx = {n._sid: n for n in ast.walk(fn)}
    fn_consts = [n.value for n in ast.walk(fn)
                 if isinstance(n, ast.Constant) and isinstance(n.value, int)
                 and not isinstance(n.value, bool)]
    ex_vals = [y for _, y in item["examples"]]
    consts = material(tier, fn_consts, ex_vals)
    S = sites(fn)
    per = []
    for kind, sid in S:
        for e in edits_at(kind, idx[sid], consts):
            per.append((sid, kind, e))
    plans = [[p] for p in per]
    if depth >= 2:
        n0 = len(per)
        pairs = [[a, b] for i, a in enumerate(per) for b in per[i + 1:]
                 if a[0] != b[0]]
        if len(plans) + len(pairs) > CAP_CANDIDATES:
            log.append("2-edit space capped at %d of %d pairs"
                       % (CAP_CANDIDATES - len(plans), len(pairs)))
            pairs = pairs[:CAP_CANDIDATES - len(plans)]
        plans += pairs
    ex_in = [x for x, _ in item["examples"]]
    ex_out = [y for _, y in item["examples"]]
    beh, tried = {}, 0
    for plan in plans:
        tried += 1
        src = apply_edits(fn, plan)
        if src is None:
            continue
        if run(src, ex_in) != ex_out:
            continue
        h = run(src, PROBE)                      # PROBE, never hold_in
        if h is None:
            continue
        beh.setdefault(tuple(h), src)
    return beh, tried


def solve(item):
    """THE LAW DRIVES. Every act below is ENGINE_LAW.decide's, not mine."""
    tier, depth, trail, log, total = 0, 1, [], [], 0
    for _ in range(8):
        beh, tried = search(item, tier, depth, log)
        total += tried
        obs = {}
        if beh:
            obs["BUILT"] = 1
            if len(beh) > 1:
                obs["AMB"] = 1
        else:
            if tier < 3:
                obs["UNREAD"] = 1
            if depth < 2:
                obs["CAPPED"] = 1
        act = EL.ACTS[EL.decide(EL.situation("WRITE_CODE", **obs))]
        trail.append(act)
        if act == "SHIP" and beh:
            src = next(iter(beh.values()))
            got = run(src, item["hold_in"])       # scoring only, after SHIP
            return {"verdict": "DETERMINED", "correct": got == item["hold_out"],
                    "n_beh": 1, "tier": tier, "depth": depth, "tried": total,
                    "trail": trail, "log": log, "shipped": src}
        if act == "ADD_MATERIAL":
            if tier >= 3 and depth >= 2:
                break
            tier = min(tier + 1, 3)
        elif act == "RAISE_BUDGET":
            depth = min(depth + 1, 2)
        elif act == "ADD_STATE":
            # the six examples do not determine the answer: several behaviours
            # fit. There is no seventh example to be had, so this is where the
            # data runs out -- report it rather than guess.
            src = next(iter(beh.values()))
            got = run(src, item["hold_in"])
            anyr = any(run(s2, item["hold_in"]) == item["hold_out"]
                       for s2 in beh.values())
            return {"verdict": "AMBIGUOUS", "n_beh": len(beh), "tier": tier,
                    "depth": depth, "tried": total, "trail": trail, "log": log,
                    "correct": got == item["hold_out"], "any_right": anyr,
                    "shipped": src}
        else:
            if tier < 3:
                tier += 1
            elif depth < 2:
                depth += 1
            else:
                break
    return {"verdict": "BOTTOM", "correct": False, "n_beh": 0, "tier": tier,
            "depth": depth, "tried": total, "trail": trail, "log": log}


if __name__ == "__main__":
    items = json.load(open(sys.argv[1]))
    print("ARM LAW, SUPPLIED FAIRLY — ENGINE_LAW.decide chooses every act\n")
    print("%-5s %-11s %-5s %-5s %-9s %-30s %s"
          % ("id", "verdict", "tier", "edits", "cands", "acts the law took", "held-out"))
    res = []
    for it in items:
        r = solve(it); r["id"] = it["id"]
        res.append(r)
        print("%-5s %-11s %-5d %-5d %-9d %-30s %s"
              % (it["id"], r["verdict"], r["tier"], r["depth"], r["tried"],
                 "->".join(a[:5] for a in r["trail"][:5]),
                 "EXACT" if r["correct"] else "no"))
        for l in r["log"]:
            print("        (%s)" % l)
    n = len(res)
    print("\n  held-out EXACT            %d/%d" % (sum(1 for r in res if r["correct"]), n))
    for v in ("DETERMINED", "AMBIGUOUS", "BOTTOM"):
        sub = [r for r in res if r["verdict"] == v]
        if sub:
            print("  %-24s %2d   of which exact %d"
                  % (v, len(sub), sum(1 for r in sub if r["correct"])))
    print("  wrong answers             %d"
          % sum(1 for r in res if r["verdict"] == "DETERMINED" and not r["correct"]))
    print("  tokens                    0")
    json.dump(res, open(sys.argv[2], "w"), indent=1)
