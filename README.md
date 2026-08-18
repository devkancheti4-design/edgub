# edgub

A debugger whose repair policy is **one arithmetic expression**, authored by a
program-synthesis engine from events measured by running — not written by a
human, not a model call.

```
read the traceback  ->  extract the syntax at the failing line
                    ->  the authored law returns one of eleven repairs
                    ->  apply it to the AST  ->  run the tests again
```

**2.5 microseconds per decision. Zero tokens. No network. No model.**

---

## The result nobody measures: damage

Almost every debugging benchmark hands you a broken program and asks if you
fix it. **A real repository is mostly working code.** Six real source modules
of a project whose 56 tests all pass, each handed to a model-only debugger with
the framing such a debugger actually uses — *"the suite is failing, review this
file and return the corrected version"*:

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

**Five of six working files were rewritten into a broken state.** edgub sent
nothing and touched nothing, because it asks a cheaper question first: *did
this file fail?*

At scale, on a 1,000-program corpus shaped like a real repo (472 already
correct, 528 broken):

```
  finished with NO model call   748  (74.8%)
  working code it broke           0  (0.00%)
  tokens        78,361  ->  13,817     (82% less)
```

**This is not the law reasoning better.** It has no opinion about how code
should look, so it cannot be tempted to improve it — a structural property,
not intelligence, and worth more than intelligence on the three quarters of a
repository that is not broken. A frontier model has the same failure: given
code that only *looked* wrong, Opus 5 broke it too.

Full method, logs, and everything this does **not** show:
[`proof/benchmark/DAMAGE.md`](proof/benchmark/DAMAGE.md).

## Where it stands against a frontier model

**It ties, it loses, and it wins — depending on the task.** All three are
measured, with ground truth found by execution:

| test | the law | law + a free local 7B | a frontier model | verdict |
|---|---|---|---|---|
| routing a failure to the right repair (14) | **11/11** | — | 11/11 | **tie** |
| repairing ordinary bugs (8) | **3/8** | 8/8 | 8/8 | **loses alone, ties paired** |
| hard traps — misleading frames, shadowed builtins, late binding (8) | — | **8/8** | 7/8 | **wins** |
| a real repository, 5 injected faults | **1/5** | — | — | **loses** |

**The law alone is not a debugger** — 3/8 once a repair needs content it
cannot invent, and 1/5 on real code where its repairs are too shallow.

**Paired with a free local model it matches a frontier model**, at 2.2x the
speed and no cost, because the law decides *what* to do and the model only
supplies *content*.

**On the hard set it beats a frontier model**, and for one structural reason:

```python
def apply(items, factor):
    return [scale(factor, i) for i in items]   # already correct
```

That looks like transposed arguments. Opus 5 transposed them and broke it. The
7B did the same. The law observed `PASSES` and returned `SHIP` — it has no
opinion about how code should look, and reacts only to what happened.

Full numbers, methods, logs and everything that would make them wrong:
[`proof/benchmark/BENCHMARK.md`](proof/benchmark/BENCHMARK.md).

## The result that matters

Fourteen broken programs. Both sides saw the same traceback and chose from the
same eleven repairs. Ground truth was measured by execution — the repair that
actually made the program produce the expected output. Opus 5's answers were
sealed in source before the ground truth was computed.

| | routing accuracy | cost per decision |
|---|---|---|
| **the authored law** | **11 / 11** | **2.5 µs, 0 tokens** |
| Opus 5 (frontier model) | **11 / 11** | ~1–3 s, ~600 tokens |

Identical choices on every case, including a nested `int(str(x) + 'z')`, a
subscript on a list built inside a comprehension, and a free name in a nested
function scope.

Three further cases were excluded because **no repair in the act set works** —
neither side could route them. Same wall for both.

## What else was measured

| test | result |
|---|---|
| unseen programs — new names, shapes, call sites | **8 / 8** repaired |
| unseen *domains* — classes, generators, `os.path`, parsing, config | **6 / 8** |
| faults outside the act set, using `REAUTHOR_BODY` on the repo's tests | **4 / 6** |
| closed loop: fail → measure → re-author → retry | **10 / 10**, 3 successors, **0 regressions** |
| a real repository (`proven-reason`, 56 tests) | **1 / 5** — see limits |

Full numbers, methods and the failures: [`proof/PROOF.md`](proof/PROOF.md).

## Honest limits

- **The repairs are the weak half, not the routing.** On a real repository the
  law chose the right act in 3 of 3 cases where the traceback was read
  correctly, but only 1 of 3 repairs actually restored behaviour.
  `DEFINE_NAME` binds a missing name to `0` — which silences a `NameError`
  and leaves `DEFAULT_GRAMMAR = Grammar()` still broken.
- **It cannot invent a repair.** A wrong operator, an off-by-one or a missing
  return has no act, and re-authoring cannot learn one. `REAUTHOR_BODY` closes
  part of this gap by authoring a new function body from the repo's tests —
  4 of 6 — but only for functions of their arguments returning integers.
- **It will report `SHIP` on a program it has not fixed** when the failure is
  a wrong result rather than an exception. Do not run it unsupervised.
- The act set covers eight fault families. Anything outside them is not
  handled and will not be learned.

## Attribution

The **law** is the engine's, verbatim. The traceback reader, the AST
transformations and this packaging are ordinary engineering around it.
The engine itself is private and is not part of this repository.

Licence: Apache-2.0.
