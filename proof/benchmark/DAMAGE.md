# Damage — what a debugger does to code that was already fine

A real repository is mostly working code. Almost every debugging benchmark
measures the opposite case: hand it a broken program, see if it fixes it.
Nobody measures what happens when you point a debugger at a file that has
nothing wrong with it.

That turns out to be where a policy beats a model, and it is the only place
it does.

## Real repository, real files, suite green

Six actual source modules of a working project (56 tests, all passing). Each
was handed to a model-only debugger with the honest framing such a debugger
uses — *"this file is part of a project whose test suite is failing, review it
and return the corrected file"* — and separately to edgub.

```
working file (suite is GREEN)     lines   brain-first        model-only
proven_reason/reasoner.py           381   SHIP (0 tokens)    changed -> BROKE suite
proven_reason/render.py             179   SHIP (0 tokens)    changed -> BROKE suite
proven_reason/catalog.py            123   SHIP (0 tokens)    left alone
proven_reason/models.py             198   SHIP (0 tokens)    changed -> BROKE suite
proven_reason/engine.py             334   SHIP (0 tokens)    changed -> BROKE suite
proven_reason/evaluator.py          197   SHIP (0 tokens)    changed -> BROKE suite

  DAMAGE     brain-first  0 / 6      model-only  5 / 6
  TOKENS     brain-first  0          model-only  17,406
```

**Five of six working files were rewritten into a broken state.** The suite
went from green to red. edgub sent nothing and changed nothing, because it
asks a cheaper question first: *did this file fail?* No. `SHIP`.

*Method: `damage_test.py`, log `damage.log`.*

## The same effect at scale

A 1,000-program corpus built the way a repository actually looks — 472 already
correct, 528 broken across routine and judgement faults:

```
  finished with NO model call     748  (74.8%)
     repairs of broken code       276
     correct code left alone      472
  DAMAGE: working code it broke     0  (0.00%)

  tokens   opus-5-alone 78,361  ->  edgub + opus 5 13,817   (82% less, 5.7x)
```

Four shapes were included that deliberately *look* wrong while being correct —
a reversed fold, an already-present bounds guard, an `or 1` default, swapped
parameters. **472 of them, zero touched.**

*Method: `mixed_corpus.py`, log `mixed_corpus.log`.*

## Why this happens, stated honestly

**The law is not reasoning better. It has no opinion about how code should
look, so it cannot be tempted to improve it.** That is a structural property,
not intelligence.

A frontier model has the same failure. On the trap case in
[`BENCHMARK.md`](BENCHMARK.md), Opus 5 was given

```python
def apply(items, factor):
    return [scale(factor, i) for i in items]   # already correct
```

and transposed the arguments, breaking it. So did the 7B. The law read
`PASSES` and shipped.

## What this does NOT show

- **The model-only configuration is deliberately naive.** It is pointed at
  whole files with no failing-test context. A well-built model agent reads the
  traceback first and opens only the implicated file — *which is exactly what
  edgub does*. The honest claim is not "models are dangerous", it is that the
  first decision, **which file to even open**, is worth making with something
  that has no opinions, and costs nothing made that way.
- **The damage figure is a local 7B**, not a frontier model. The single sealed
  frontier data point on this failure mode is n=1 (the trap case above).
- **Tokens are estimated** at 4 characters each. The counts of what is *sent*
  are exact; the conversion and the dollar figures are not.
- **It contributes nothing to 17% of bugs** — wrong operators, missing
  returns, off-by-one — where knowing what the code was *for* is the whole
  problem. See the `hard` row in [`BENCHMARK.md`](BENCHMARK.md).
