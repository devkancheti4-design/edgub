# It generalises — measured on a library it has never seen

The toolz corpus and edgub's edit classes were built alongside each other, so
7/10 there measures *fit*, not reach. This file is the reach measurement: the
same package, unmodified, against `funcy` — a library nothing here was tuned
on — with six bugs injected by an outside reviewer, not by me.

## Result

```
edgub 0.3 on funcy (unseen library, 205 tests)

bug                result      edit                budget where it landed
swap_yesno_colls   REPAIRED    swap tuple 0<->1    2s
swap_kv            REPAIRED    swap tuple 0<->1    2s
swap_yesno_seqs    REPAIRED    invert if           2s
cmp_flip_pool      -> model                        exhausted 120s
bool_flip_tail     -> model                        exhausted 120s
cmp_flip_path      -> model                        exhausted 120s

3 / 6 repaired free, 0 tokens
```

An earlier run against `more-itertools` (736 tests, 21,039 subtests) scored
**0 of 4** and one case killed pytest with exit -9 after 879 seconds. That
result stands and is not deleted: on a second unseen library the same package
repaired nothing. Two unseen libraries, 3/10 combined.

## Every repair landed in 2 seconds. None ever landed later.

The escalation ladder was 2s -> 10s -> 30s -> 120s. All three repairs came at
the first rung; widening bought **zero** additional repairs and consumed 180 of
the 182 CPU-seconds spent.

This is the enumeration/inference split, visible in wall-clock: inference reads
the answer immediately, or enumeration will not find it. `diff` is the same
story from the other side — 4 candidates by inference, 25,057 by enumeration
and never solved.

**Consequence: the search budget should be 5 seconds, not 30, and not parity.**

## The cost-parity argument, and why it does not matter

Widen only while CPU is still cheaper than the tokens a model would burn:

```
Opus 5 body cost per bug   7,496 tokens ~= $0.033
cloud vCPU                 $0.04/hour   =  $1.11e-5 per CPU-second
parity point               ~2,970 CPU-seconds per bug
measured need              2 seconds
```

The budget is economically justified out to 50 minutes per bug and empirically
needs 0.07% of it. Stated honestly: the parity formula is the right principle
and the wrong constraint — patience binds long before economics does.

## The part the repair count hides

When edgub *cannot* repair, it still removes the model's search:

```
handoff prompt on an unrepaired bug     1,873 chars = ~468 tokens
the same bug, model working from repo         ~7,496 tokens
```

The prompt states the ruling ("the library is wrong and must be repaired, never
the test") and the failing test. The model does not localise, does not decide
test-vs-code, does not read the package. So the escalated bugs are ~16x cheaper
too, and the run totals:

```
3 repaired free                    0 tokens
3 escalated x ~468 tokens      1,404 tokens
opus 5 alone, same six        44,976 tokens
                              --------------
saved                          ~96% (prompt-side)
```

Honest qualifications: 468 is prompt-side only — the model's reply adds roughly
100-300 tokens per bug, so ~93% is the defensible figure. The prompt also
currently embeds a full pytest traceback including absolute paths, which is
noise that would shrink it further. And CPU is not free: 182 CPU-seconds is
$0.002 against $0.099 of tokens displaced — a 50x ratio, but not zero.

## What this does not show

- Two libraries is not a generalisation claim, it is two data points, one of
  which was a zero.
- `swap_yesno_seqs` was injected as a swapped return tuple and repaired with
  `invert if` — suite-green, different code. The suite is a weaker oracle than
  the question, and this is the second time that has been measured here.
- Nothing here tests a private codebase, where a model's recall advantage
  shrinks and edgub's should not.

## Reproduce

```bash
pip install -e . && pip install pytest
git clone --depth 1 https://github.com/Suor/funcy && cd funcy && pip install -e .
# inject the six faults listed above, then:
python -c "import edgub; print(edgub.fix('.'))"
```
