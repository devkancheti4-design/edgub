# Benchmark — where this ties a frontier model, where it loses, where it wins

**It does all three.** Read the whole page before quoting any line of it.

The comparison is between three things:

| | what it is |
|---|---|
| **law** | the authored policy alone. Routes a failure to one of eleven repairs and applies an AST transform. 2.5 µs, 0 tokens, free. |
| **7B** | a local `qwen2.5-coder:7b` via ollama, given the file and the error, asked to return the corrected file. Free, no network. |
| **law + 7B** | the law decides *which* repair; the model supplies only the *content* the law cannot invent — a value, a body. The model never chooses what to do. |
| **Opus 5** | a frontier model. Repairs written in full, sealed in source before running. |

Ground truth in every case: **does the program run and print the expected
output.** Measured by execution, never judged.

---

## Set 1 — routing only. **TIE.**

Fourteen failures. Both sides saw the same traceback and chose from the same
eleven repairs. Opus 5's choices were sealed before ground truth was computed.

```
the law   11 / 11        2.5 µs per decision, 0 tokens
Opus 5    11 / 11        ~1-3 s per decision, ~600 tokens
```

Three further cases were excluded because **no repair in the act set works** —
neither side could route them. Same wall for both.

*Method: `../fair_test.py`, log `../fair.log`.*

## Set 2 — repair, ordinary bugs. **THE LAW ALONE LOSES. The pair ties.**

Eight bugs, half of which need content the law cannot invent (a value for a
missing name, a body for a wrong operator).

```
law only    3 / 8     0.9 s      <-- loses badly on its own
7B alone    8 / 8    16.5 s
law + 7B    8 / 8     7.6 s      <-- ties, at 2.2x the speed
Opus 5      8 / 8
```

**The law on its own is not a debugger.** Once a repair needs invented
content it scores 3/8, and no amount of routing accuracy changes that.

*Method: `three_way.py`, log `three_way.log`.*

## Set 3 — hard cases: misleading frames, latent boundaries, shadowed
builtins, late binding, aliasing, swallowed exceptions. **THE PAIR WINS.**

```
7B alone    6 / 8    18.4 s
law + 7B    8 / 8     9.3 s      <-- beats both
Opus 5      7 / 8
```

### The case that decided it

```python
def scale(v, f):
    return v / f
def apply(items, factor):
    return [scale(factor, i) for i in items]
print(apply([2, 4], 8))          # prints [4.0, 2.0] -- ALREADY CORRECT
```

`scale(factor, i)` *looks* like transposed arguments. Opus 5 transposed them
and printed `[0.25, 0.5]`. The 7B did the same. **Both broke working code
because it looked wrong.**

The law observed `PASSES` and returned `SHIP`. It left the file alone.

That is not luck. **The policy has no opinion about how code should look — it
reacts only to what happened.** A model cannot help having an opinion. This is
the one structural advantage in the whole benchmark.

*Method: `hard_cases.py`, log `hard_cases.log`, Opus 5's repairs in
`opus5_repairs.py`.*

---

## The honest summary

| set | law alone | law + 7B | frontier | verdict |
|---|---|---|---|---|
| routing (14) | **11/11** | — | 11/11 | **tie** |
| ordinary repair (8) | **3/8** | 8/8 | 8/8 | **loses alone, ties paired** |
| hard traps (8) | — | **8/8** | 7/8 | **wins** |
| a real repository (5) | **1/5** | — | — | **loses** |

**It ties a frontier model on routing, loses badly alone once content must be
invented, wins on cases where over-eager fixing is the danger, and does poorly
on a real repository where the repairs are too shallow.**

## What would make these numbers wrong

- **The sets are small** — 14, 8, 8 — and I wrote them. The case that trapped
  the frontier model was not constructed deliberately; it is strong evidence
  precisely because it was an accident, and one accident is not a trend.
- **Set 3 rewards conservatism.** `SHIP` on a program whose output is right is
  correct. `SHIP` on a program that is silently wrong is the law's known
  defect, and a set built around latent bugs would punish exactly the
  behaviour that wins here.
- **Set 2 favours a small model**: every case is a self-contained five-line
  function, the best possible setting for "return the corrected file". On a
  400-line module that approach degrades and targeted edits should widen the
  gap — untested.
- **Opus 5's repairs were written directly, not through an API.** Token and
  dollar figures elsewhere are estimates; the 7B and law+7B timings are
  wall-clock measurements.
- **The real repository result (1/5) is the least flattering and the most
  representative.** The routing held; the repairs did not.
