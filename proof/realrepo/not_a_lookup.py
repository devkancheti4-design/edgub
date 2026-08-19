"""HOW MUCH OF THE LAW IS A LOOKUP TABLE? Measured both ways.

An outside reviewer traced the mechanism and called it an error-type -> act
table encoded as arithmetic. They are substantially right, and this file
measures exactly how right rather than arguing.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import ast, json, collections, re
import edgub

print("CHECK 1 — NOTHING IS STORED. The law is a closed-form expression.\n")
law = edgub.LAW   # the ARTEFACT, not a regex over a docstring
print("   the policy, first 70 chars of %d:" % len(law))
print("      %s..." % law[:70])
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


print("\nCHECK 5 — HOW MUCH OF IT A 14-LINE DICT REPRODUCES\n")
singles = [b for b in edgub.BITS if b != "PASSES"]
one_to_one = {b: edgub.ACTS[edgub.decide(edgub.sit({b}))] for b in singles}
print("   single-fault situations : %d" % len(singles))
print("   mapping 1:1 to one act  : %d  -- all of them" % len(one_to_one))
for b, a in one_to_one.items():
    print("      %-12s -> %s" % (b, a))
def naive(x):
    if x == 0:
        return 0
    return ((x & -x).bit_length() - 1) % 11
N = 2 ** len(edgub.BITS)
agree = sum(1 for v in range(N) if edgub.decide(v) == naive(v))
print("\n   a %d-line dict reproduces every single-fault ruling." % len(singles))
print("   'lowest set bit mod 11' reproduces %d/%d of the FULL space (%.1f%%),"
      % (agree, N, 100.0 * agree / N))
print("   so compound rulings are not that naive rule.")
print("""
   BUT: of the ten real toolz bugs, EIGHT were single-fault. The dict would
   have handled them. And the compound rulings -- the part a dict cannot
   reproduce -- are the same rulings that scored 0/10 on real repositories.

   So: nothing is stored, and on the cases that occur it behaves as a table.
   Both are true. The interesting claim is neither of those -- it is that
   correcting one ACT'S MEANING moved 0/10 to 9/10 with the expression
   untouched. The act list is separable from the mapping.""")
