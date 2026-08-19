"""SCORE THE MODEL ARM on exactly the same held-out inputs as the law arm.

Two numbers matter, not one:
  EXACT     right on all 20 held-out inputs -- it recovered the function
  OVERFIT   matched all 6 given examples and still failed held-out -- it fit
            the data it was shown and did not generalise
"""
import json, sys

class _Stop(Exception): pass

def _limited(fn, x, limit=30000):
    n = 0
    def tr(f, e, a):
        nonlocal n
        n += 1
        if n > limit: raise _Stop()
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

if __name__ == "__main__":
    items = {i["id"]: i for i in json.load(open(sys.argv[1]))}
    answers = {}
    for p in sys.argv[3:]:
        answers.update(json.load(open(p)))
    print("ARM OPUS 5 — independent agents, same 6 examples, same held-out\n")
    print("%-5s %-9s %-9s %s" % ("id", "examples", "held-out", "note"))
    rows = []
    for pid, it in sorted(items.items()):
        src = answers.get(pid)
        if src is None:
            rows.append((pid, False, False, "no answer")); continue
        ex_ok = run(src, [x for x, _ in it["examples"]]) == [y for _, y in it["examples"]]
        ho = run(src, it["hold_in"])
        ho_ok = ho == it["hold_out"]
        note = "" if ho_ok else ("OVERFIT — fit the 6, missed held-out" if ex_ok
                                 else "did not even fit the 6")
        rows.append((pid, ex_ok, ho_ok, note))
        print("%-5s %-9s %-9s %s" % (pid, "ok" if ex_ok else "no",
                                     "EXACT" if ho_ok else "no", note))
    n = len(rows)
    ex = sum(1 for r in rows if r[1]); ho = sum(1 for r in rows if r[2])
    of = sum(1 for r in rows if r[1] and not r[2])
    print("\n  fit the 6 examples        %d/%d" % (ex, n))
    print("  held-out EXACT            %d/%d" % (ho, n))
    print("  OVERFIT (fit 6, failed)   %d" % of)
    print("  wrong answers             %d" % (n - ho))
    json.dump([{"id": r[0], "ex": r[1], "ho": r[2]} for r in rows],
              open(sys.argv[2], "w"), indent=1)
