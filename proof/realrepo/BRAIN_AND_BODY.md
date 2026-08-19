# Brain and body on ten real bugs

`edgub.decide()` decides. What it cannot repair goes to a frontier model. Ten
bugs of the kind that survive review, in `toolz` — 3,346 lines, 185 tests.

```
                                        repaired    tokens
brain  edgub.decide, acts corrected        8/10          0
body   opus 5, the two it cannot reach     2/10     26,630
---------------------------------------------------------
TOGETHER                                  10/10     26,630
opus 5 alone, same ten, batched           10/10     74,964

tokens saved: 48,334 of 74,964 = 64.5%
```

Same accuracy either way. Both of the body's repairs verified green on the full
185-test suite.

## 80% of cases is not 80% of tokens

Eight of ten never reach the model — but the saving is **64.5%, not 80%**. The
two that do reach it are the hard ones: both needed a synthesised `if/else`,
and hard cases cost more per bug than the average. Quoting the case count as
the saving would inflate it by fifteen points.

The batching also matters and has nothing to do with the law. Sent alone, one
bug cost 26,646 tokens; sent as a pair, both cost 26,630. If the baseline had
been run one-bug-at-a-time it would have been ~266,000 and this table would
read "90% saved". Same system, same work. The 64.5% is measured under matched
conditions and is the number to quote.

## What each side did

```
brain, free                                        act#   candidates
  unique_wrongvar      name item->val                 2          117
  groupby_wrongvar     unwrap call                    2            6
  reduceby_nocontinue  insert continue @1             7          393
  sliding_off          const 1->0                     7           10
  itemfilter_swap      swap tuple 0<->1               7            3
  merge_with_order     unwrap call                    7            4
  join_sides           swap tuple 0<->1               7           68
  get_default_inv      cmp->Gt                        2           15

brain, exhausted -- a genuine ⊥, not a timeout
  partition_alwayspad  808 candidates, space closed empty
  diff_nodefault       25,057 candidates, space closed empty

body, opus 5
  diff_nodefault       wrote `if default is no_default: ... else: ...`
  partition_alwayspad  wrote `if pad is no_pad: ... else: ...`
```

Both failures are the same class: **restore a deleted branch.** No supplied edit
class can write a condition and two arms that were never in the file. That is
precisely what the model does in one pass, and it is the honest division of
labour this table measures.

## The instrument was wrong before this run

An earlier version of this measurement reported **9/10**, and it was wrong in
both directions. Candidates were screened by spawning a fresh `pytest` per
candidate; through stale bytecode that screen **rejected repairs that actually
work**.

Replacing it with in-process screening (`fastcheck.py`) was 2,028x faster and
changed the answers:

```
per candidate       0.229s -> 0.00011s
unique_wrongvar     failed -> repaired
reduceby            `name no_default->key` -> `insert continue @1`
                    (a suite-satisfying wrong fix -> the genuine one)
partition           `name no_pad->n` -> correctly REJECTED
```

So this 8/10 is worth more than that 9/10: the old number was inflated by two
repairs that greened the suite without being correct. Fixing the instrument
cost a point and bought two right answers.

`fastcheck.py` is validated before use — it must reject the bugged function and
accept the repaired one — because the whole reason the old screen was wrong is
that nobody checked it.

## Reproduce

```bash
python3 inject_hard.py bugged     # fetches toolz, injects the ten bugs
python3 edgub_repair.py           # decide() verbatim, acts corrected
```

The body's side is a recorded measurement: re-running a frontier model needs a
key, so its token counts are stated with provenance rather than claimed as
reproducible.
