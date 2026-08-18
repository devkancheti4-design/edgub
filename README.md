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
