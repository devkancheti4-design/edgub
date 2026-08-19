"""LAW AS BRAIN, OPUS 5 AS HANDS — build the instruction the body receives.

The law decides WHICH act. The model performs THAT act and nothing else: it may
not pick a different repair, may not decide the fault is elsewhere, may not
free-form. That is the whole point of the split.

This file only computes, per bug: the mechanical observation, the act the law
names, and the target the run itself points at. It writes those out as the
body's instructions.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..")))
import os, re, sys, ast, json, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import edgub
import harness as F

ACT_MEANING = {
 "SHIP": "the work is done; change nothing",
 "ADD_STATE": "the observation cannot tell two cases apart; encode the missing variable",
 "ADD_MATERIAL": "nothing available reads or expresses what is needed; supply it",
 "RESHAPE": "the thing exists but not in the form required; change its form",
 "CHANGE_GRANULARITY": "records agree at one scale and disagree at another; re-record",
 "RAISE_BUDGET": "the input is clean and the budget ran out; raise it",
 "HARVEST_COUNTEREXAMPLE": "an independent check refuted it; turn the refutation into a test",
 "AUTHOR_SUCCESSOR": "the act set cannot express this; author a successor policy",
 "DEFINE_NAME": "bind the undefined name",
 "CAST_OPERAND": "coerce the operand at the failing operator",
 "GUARD_SUBSCRIPT": "clamp the failing index",
 "GUARD_DIVISOR": "make the failing divisor safe",
 "ADD_ATTRIBUTE": "add the missing attribute",
 "COERCE_INT": "strip non-numeric characters inside the failing conversion",
 "RELAX_ASSERT": "weaken the failing assertion",
 "RAISE_LIMIT": "raise the numeric budget on the failing line",
 "ADD_IMPORT": "import the module the name refers to",
}


def build(root, cfg, ids=None):
    out = []
    for b in json.load(open(os.path.join(root, "bugs.json"))):
        if ids and b["id"] not in ids:
            continue
        repo = os.path.join(root, b["id"])
        failed, run = F.run_suite(repo, cfg["ignore"])
        tg = F.targets(repo, run, cfg)
        errbits = F.observe(run) if hasattr(F, "observe") else set()
        # edgub's law reads the fault class from the interpreter
        eobs = set()
        for name, bit in (("NameError", "E_NAME"), ("TypeError", "E_TYPE"),
                          ("IndexError", "E_INDEX"), ("ZeroDivisionError", "E_ZERO"),
                          ("AttributeError", "E_ATTR"), ("ValueError", "E_VALUE"),
                          ("AssertionError", "E_ASSERT")):
            if name in run:
                eobs.add(bit)
        eobs = eobs or {"OUT_WRONG"}
        eact = edgub.ACTS[edgub.decide(edgub.sit(eobs))]
        mod, func = tg[0] if tg else (None, None)
        src = ""
        if mod:
            p = os.path.join(repo, mod.replace(".", "/") + ".py")
            t = ast.parse(open(p).read()); lines = open(p).read().splitlines()
            for n in ast.walk(t):
                if isinstance(n, ast.FunctionDef) and n.name == func:
                    src = "\n".join(lines[n.lineno - 1:n.end_lineno])
        out.append({"id": b["id"], "mod": mod, "func": func,
                    "edgub_obs": sorted(eobs), "edgub_act": eact,
                    "failing": F.failing_nodes(run),
                    "run": run[:2500], "src": src})
    return out


if __name__ == "__main__":
    tag = sys.argv[1]
    cfg = F.REPOS[tag]
    spec = build(cfg["root"], cfg)
    json.dump(spec, open(os.path.join(HERE, "spec_%s.json" % tag), "w"), indent=1)
    print("%-20s %-16s %-24s %s" % ("bug", "observation", "edgub's act", "target"))
    for s in spec:
        print("%-20s %-16s %-24s %s.%s"
              % (s["id"], "+".join(s["edgub_obs"])[:16], s["edgub_act"],
                 (s["mod"] or "-").split(".")[-1], s["func"]))
    import collections
    c = collections.Counter(s["edgub_act"] for s in spec)
    print("\n  the act list as shipped rules:")
    for a, n in c.most_common():
        print("    %-18s %d of %d" % (a, n, len(spec)))
    print("  acts among these that repair a wrong value: 0")
