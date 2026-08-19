"""CHECK 4 — NEGATIVE CONTROL: FEED IT LIES.

If the 19 answers were recalled rather than derived, corrupting the examples
would not change what comes back. So: same broken source, but the six examples
replaced with a DIFFERENT program's. A generaliser must stop returning the
original.

BOUNDED ON PURPOSE at the material and budget the real run used for 18 of 20
(tier 0, one edit). The control asks whether the answer TRACKS THE DATA, not
how deep the space goes -- and escalating a contradiction to tier 3 two-edit
is hours of search to prove a point tier 0 already proves. The bound is stated
rather than hidden.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arm_law2 as L

G = os.path.dirname(os.path.abspath(__file__))
items = {i["id"]: i for i in json.load(open(os.path.join(G, "corpus.json")))}
EX = [x for x, _ in items["P00"]["examples"]]
ALL = EX + L.PROBE + items["P00"]["hold_in"]

ids = sorted(items)
agree = fits = empty = 0
print("%-5s %-28s %s" % ("id", "with a DIFFERENT program's data", "returns the original?"))
for i, pid in enumerate(ids):
    it = dict(items[pid])
    it["examples"] = items[ids[(i + 7) % len(ids)]]["examples"]   # wrong outputs
    log = []
    beh, tried = L.search(it, 0, 1, log)          # tier 0, one edit -- bounded
    if not beh:
        empty += 1
        print("%-5s %-28s %s" % (pid, "empty space (no fit)", "no"))
        continue
    fits += 1
    src = next(iter(beh.values()))
    same = L.run(src, ALL) == L.run(items[pid]["_good"], ALL)
    agree += same
    print("%-5s %-28s %s" % (pid, "fit the corrupted data", "YES" if same else "no"))

print("\n  returned the original anyway (would prove lookup) : %d of 20" % agree)
print("  returned a fit to the corrupted data              : %d of 20" % fits)
print("  returned the empty space                          : %d of 20" % empty)
print("\n  bound declared: tier 0, one edit -- the setting that answered 18 of 20"
      "\n  in the real run. Nothing was searched and discarded silently.")
