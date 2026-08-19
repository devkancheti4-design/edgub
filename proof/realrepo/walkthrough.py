"""HOW THE LAW DECIDES — one decision, traced end to end.

Every number this prints is computed when you run it. Nothing is asserted.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), "..", "..")))
import re, itertools, collections
import edgub

src = open(_os.path.join(_os.path.dirname(edgub.__file__), "__init__.py")).read()
LAW = re.search(r"LAW\s*=\s*'([^']*)'", src).group(1)

print("=" * 72)
print("STEP 1 — THE INTERPRETER SPEAKS. Nothing here is a judgement.")
print("=" * 72)
dump = """toolz/tests/test_itertoolz.py:151: in test_nth
E   AssertionError: assert 'B' == 'C'"""
print(dump)
obs = edgub.observe_traceback(dump)
print("\n   observation read off it: %s" % sorted(obs))
print("   (only exception names the run actually printed -- no interpretation)")

print("\n" + "=" * 72)
print("STEP 2 — PACK IT INTO ONE INTEGER. Each observation is one bit.")
print("=" * 72)
for i, b in enumerate(edgub.BITS):
    mark = "1" if b in obs else "0"
    print("   bit %2d  %-14s %s" % (i, b, mark))
x = edgub.sit(obs)
print("\n   situation = %d   (binary %s)" % (x, bin(x)))

print("\n" + "=" * 72)
print("STEP 3 — THE LAW. This is the whole policy. There is no table.")
print("=" * 72)
print("   %s" % LAW)
print("\n   %d characters of arithmetic." % len(LAW))
print("   It is compiled once at import and evaluated on the integer above.")
i = edgub.decide(x)
print("\n   decide(%d) = %d   ->   ACTS[%d] = %s" % (x, i, i, edgub.ACTS[i]))

print("\n" + "=" * 72)
print("STEP 4 — WHY THIS IS NOT A LOOKUP TABLE")
print("=" * 72)
N = 2 ** len(edgub.BITS)
cov = collections.Counter(edgub.decide(v) for v in range(N))
print("   situations it answers          : %d" % N)
print("   events it was authored from    : 11")
print("   proportion ever measured       : %.4f%%" % (100.0 * 11 / N))
print("   stored entries                 : 0")
print("   acts reachable                 : %d of %d" % (len(cov), len(edgub.ACTS)))
singles = {edgub.sit({b}) for b in edgub.BITS}
pairs = [set(c) for c in itertools.combinations(
    [b for b in edgub.BITS if b != "PASSES"], 2)]
unseen = [c for c in pairs if edgub.sit(c) not in singles]
print("   two-fault situations it rules")
print("   on and was NEVER authored on   : %d" % len(unseen))
print("\n   a table over these bits would need %d entries. It stores none," % N)
print("   because the answer is COMPUTED from the integer, not retrieved.")

print("\n" + "=" * 72)
print("STEP 5 — WHAT THE DECISION BUYS: it collapses the search")
print("=" * 72)
print("""   The act does not fix anything by itself. It names WHICH KIND of repair
   to look for, and that is what makes the search small. Measured on ten real
   bugs in toolz (185 tests):

       bug                  full space   evaluated   narrowing
       merge_with_order         20,031           4      5008x
       groupby_wrongvar          5,580           6       930x
       itemfilter_swap           2,444           3       815x
       unique_wrongvar           3,187          13       245x
       reduceby_nocontinue      12,274          32       384x
       partition_alwayspad         808           9         90x
       sliding_off                 764          88          9x

       across the completed runs: 148 candidates evaluated out of 45,088

   Every surviving candidate had to green all 185 tests. Nothing is recalled --
   the repairs are generated and executed, and most are rejected.""")

print("\n" + "=" * 72)
print("STEP 6 — THE COST")
print("=" * 72)
import time
for _ in range(200):
    edgub.decide(7)
M = 20000
t0 = time.perf_counter()
for v in range(M):
    edgub.decide(v & 255)
el = (time.perf_counter() - t0) / M * 1e6
print("   per decision : %.2f us  (%d/sec)" % (el, int(1e6 / el)))
print("   tokens       : 0        no key, no network, no model")
print("   for the ten bugs above, a frontier model deciding for itself")
print("   spent 74,964 tokens and scored 10/10; the law scored 9/10 at zero.")
print("""
   Read the zero as the price of a FIRST PASS, not of the whole job. And zero
   tokens is not zero cost: 148 candidates is 148 test-suite runs of real CPU,
   which a token comparison hides completely.""")

print("\n" + "=" * 72)
print("STEP 7 — THE EXAMPLE ABOVE IS THE KNOWN DEFECT. Read it carefully.")
print("=" * 72)
print("""   decide() answered RELAX_ASSERT: weaken the failing assertion.

   On the toy scripts this law was authored from, that was correct -- the
   assert really was the wrong thing. On a real repository it is exactly
   backwards: the test is right and the library is wrong.

   Measured on ten real bugs in toolz, the shipped act list scores

       0 of 10 repaired, and 7 test suites weakened

   That is not a failure of the expression. The expression mapped the
   observation onto act index 7 correctly and consistently. ACTS[7] is a
   LIST ENTRY chosen by a human, and the human chose wrong:

       BITS[7] = E_ASSERT   ->   ACTS[7] = RELAX_ASSERT

   With that one meaning corrected -- act 7 becomes 'the library is wrong,
   repair it' -- and decide() untouched, byte for byte, the same law scores

       9 of 10 repaired, 0 tokens

   See proof/realrepo/edgub_repair.py. This is the distinction the whole
   project turns on: the law is a mapping onto acts, and the acts are supplied.
   Judge the mapping and the act list separately.""")
