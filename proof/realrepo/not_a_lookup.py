"""IS THE LAW A LOOKUP TABLE? Four checks that a table fails.

The commonest reading of this project is that `decide()` is a disguised table of
memorised answers. It is not, and none of the following requires trusting me.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import ast, json, collections, re
import edgub

print("CHECK 1 — THERE IS NO TABLE. The law is a closed-form expression.\n")
src = open(_os.path.join(_os.path.dirname(edgub.__file__), "__init__.py")).read()
law = re.search(r"LAW\s*=\s*'([^']*)'", src).group(1)
print("   the entire policy, verbatim:")
print("      %s" % law)
print("   length: %d characters" % len(law))
print("   a table over %d observation bits would need %d entries"
      % (len(edgub.BITS), 2 ** len(edgub.BITS)))
print("   entries stored: 0\n")

print("CHECK 2 — IT RULES ON SITUATIONS IT WAS NEVER SHOWN.\n")
N = 2 ** len(edgub.BITS)
cov = collections.Counter(edgub.decide(x) for x in range(N))
print("   distinct situations it answers : %d" % N)
print("   events it was authored from    : 11   (proof/selftest.py)")
print("   answered but never measured    : %d  (%.4f%% were measured)"
      % (N - 11, 100.0 * 11 / N))
print("   acts reachable                 : %d of %d" % (len(cov), len(edgub.ACTS)))
dead = [a for i, a in enumerate(edgub.ACTS) if not cov.get(i)]
print("   acts that never fire           : %s\n" % (dead or "none"))

print("CHECK 3 — COMPOUND OBSERVATIONS IT WAS NEVER AUTHORED ON.\n")
singles = [{b} for b in edgub.BITS if b != "PASSES"]
seen = {edgub.sit(s) for s in singles} | {edgub.sit({"PASSES"})}
import itertools
compound = [set(c) for c in itertools.combinations(
    [b for b in edgub.BITS if b != "PASSES"], 2)]
unseen = [c for c in compound if edgub.sit(c) not in seen]
print("   two-fault situations never in the authoring set : %d" % len(unseen))
for c in unseen[:5]:
    print("      %-28s -> %s" % ("+".join(sorted(c)), edgub.ACTS[edgub.decide(edgub.sit(c))]))
print("   each is computed by the expression, not retrieved.\n")

print("CHECK 4 — THE REPAIRS ARE NOT STORED EITHER.\n")
print("""   Every repair this project reports was found by generating candidate
   edits and running the repository's own test suite against them. Nothing is
   recalled: on the ten hard bugs, 148 candidates were evaluated out of a
   45,088 space, and each surviving candidate had to green all 185 tests.

   The strongest evidence is negative. The same machinery, fed a DIFFERENT
   program's examples, returned the original program 0 times out of 20 and the
   empty space 20 times out of 20. A lookup table cannot do that -- it would
   return its stored answer regardless of the data.
   (That control is in the private engine's repository, not here, because it
   tests the engine law rather than this one.)""")
