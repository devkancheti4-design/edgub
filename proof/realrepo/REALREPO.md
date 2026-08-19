# edgub on real repositories

Two real libraries, real test suites, bugs of the kind that survive code review —
a wrong variable, a missing `continue`, a collapsed branch, a reversed tuple,
a condition inverted on one path only. `toolz`: 3,346 lines, 185 tests, green
at HEAD. Ten bugs, each in its own throwaway copy, each verified red first.

## What happened the first time: 0 of 10, and seven damaged test suites

The law was given the best possible hands — Opus 5, told to perform exactly the
act the law named and nothing else.

```
unique_wrongvar      function edited   seen_add(str(item))  — not a repair
groupby_wrongvar     CANNOT
reduceby_nocontinue  TEST weakened     equality -> key set only
partition_alwayspad  TEST weakened     compare only the complete partitions
sliding_off          TEST weakened     equality -> membership
itemfilter_swap      TEST weakened     frozenset — orientation no longer asserted
merge_with_order     TEST weakened     set — value order no longer asserted
diff_nodefault       TEST weakened     prefix — the padding no longer asserted
join_sides           TEST weakened     frozenset — which side is left no longer asserted
get_default_inv      CANNOT

                     0 fixed   7 test suites weakened   2 refused
```

Zero repairs, and seven suites quietly weakened with the bugs still in the
library. That is worse than doing nothing.

## Why — and it was not the law

`ACT[i]` answers `BITS[i]`. `BITS[7]` is `E_ASSERT`; `ACTS[7]` is
`RELAX_ASSERT`. So the shipped act list says **"a test failed → weaken the
test."** Every one of the eleven acts suppresses an exception; not one repairs
a wrong value:

```
DEFINE_NAME      binds the missing name to 0
CAST_OPERAND     wraps operands in int()
GUARD_SUBSCRIPT  clamps the index
GUARD_DIVISOR    makes the divisor non-zero
ADD_ATTRIBUTE    adds the attribute
COERCE_INT       strips non-digits
RELAX_ASSERT     turns the assert into an assignment
RAISE_LIMIT      multiplies the budget
ADD_IMPORT       imports the module

acts that repair a WRONG VALUE: 0 of 11
```

That list was authored against toy scripts, where a failing assertion really was
the wrong thing. On a real repository the assertion is right and the library is
wrong, so the central pairing is exactly inverted. **The act list is supplied;
the law only maps observations onto it.**

## The same law, once the acts mean the right thing

`edgub.decide()` is used **byte for byte unchanged**. Only what each act *means*
was corrected — every act now repairs the library instead of suppressing the
symptom, and each routes to the edit classes its fault implies. Index 7,
answering `E_ASSERT`, becomes *the library is wrong; repair it*.

```
bug                  observation      act#   authored                tried
unique_wrongvar      E_ASSERT+E_TYPE   2     unwrap call                13
groupby_wrongvar     E_ASSERT+E_TYPE   2     unwrap call                 6
reduceby_nocontinue  E_ASSERT          7     name no_default->key       32
partition_alwayspad  E_ASSERT          7     name no_pad->n              9
sliding_off          E_ASSERT          7     drop arg 1                 88
itemfilter_swap      E_ASSERT          7     swap tuple 0<->1            3
merge_with_order     E_ASSERT          7     unwrap call                 4
join_sides           E_ASSERT          7     swap tuple 0<->1           68
get_default_inv      E_TYPE            2     cmp->Gt                    15
diff_nodefault       E_ASSERT          7     -- none --

                                       9 / 10      0 tokens
```

**0 of 10 → 9 of 10, with the law untouched.** For comparison, Opus 5 deciding
for itself scored 10/10 on the same bugs for 74,964 tokens.

## It routes; it does not brute-force

```
bug                    full space   evaluated   narrowing
merge_with_order           20,031           4      5008x
groupby_wrongvar            5,580           6       930x
itemfilter_swap             2,444           3       815x
unique_wrongvar             3,187          13       245x
reduceby_nocontinue        12,274          32       384x
partition_alwayspad           808           9        90x
sliding_off                   764          88         9x

  full space over the completed runs   45,088
  actually evaluated                      148
```

`merge_with_order` was found on the 4th candidate out of 20,031. The routing
collapses the space by two to three orders of magnitude; the search is what
remains after the law has done its work, not a substitute for it.

## How the attribution was settled

Not by argument. **Hold `decide()` fixed, change only the supplied material, and
see what moves.** Three bugs missed on the first corrected run; all three traced
to a line of mine:

```
unique_wrongvar   ACT_CLASSES[2] excluded "pass a different value"
get_default_inv   ACT_CLASSES[2] excluded comparison repairs
diff_nodefault    `if tried > 4000` — my ceiling reporting as the law's ⊥
```

Widening only my side resolved two of the three, with identical rulings from the
law before and after.

## Limits, stated

- **Two repairs green the suite without being the original code.**
  `reduceby_nocontinue` returned `name no_default->key` and
  `partition_alwayspad` returned `name no_pad->n`. Both pass all 185 tests. The
  suite cannot distinguish them from the true fix — the oracle is weaker than
  the question. Counted as repairs because the suite is the only judge
  available, but they are not recoveries of the original.
- **`diff_nodefault` needs a synthesised `if/else`.** Restoring a deleted branch
  is not in the edit material, and no amount of searching reaches it.
- **The act→edit-class sets are engineering, not emergent.** The law routes; a
  human decided what each route may reach. Every new fault shape is a commit.
- **`toolz` is a famous public library.** A frontier model has seen these
  functions in training, so its 10/10 is partly recall. On private code that
  advantage shrinks.

## Reproduce

```bash
python inject_hard.py bugged     # ten hard bugs into throwaway copies
python spec.py hard              # what the law rules, before any repair
python edgub_repair.py           # decide() verbatim, acts corrected
```

`edgub.decide()` is imported from the package and never modified by any file here.
