# edgub

Repair a repository from its own failing tests. **No model, no API key, no
network.** Standard library only.

```bash
pip install -e .
edgub .
```

```
edgub: 1 repaired, 1 left for a model, 2.4s, 0 tokens
  repaired  itertoolz.unique   CAST_OPERAND via name item->val (117 candidates)
  left      tests/test_package.py::test_has_version   the failing test exercises
            no function in this package -- an environment failure, not a defect
```

It discovers your package, runs your suite, reads what the interpreter said,
decides which class of repair the fault belongs to, generalises a repair from
your own tests, and verifies it against the whole suite before keeping it.

```python
import edgub
report = edgub.fix(".")            # or edgub.fix(repo, package="mypkg")
for r in report.repaired:
    print(r.function, r.edit, r.diff)
for u in report.unrepaired:
    print(u.prompt)                # ready to send to a model, minimal context
```

## What it is honestly for

**A free deterministic first pass.** It repairs the mechanical fraction offline
and hands you a minimal, precise prompt for the rest. It is *not* a replacement
for a model. On ten real bugs in `toolz`:

```
                                        repaired    tokens
edgub                                      8/10          0
a frontier model, the two it cannot reach  2/10     26,630
TOGETHER                                  10/10     26,630
that model alone, same ten, batched       10/10     74,964
```

Same accuracy, **64.5% fewer tokens**. Note that 8-of-10 free is 80% of *cases*
but only 64.5% of *tokens* — the ones it cannot reach are the hard ones and cost
more per bug.

## Limits, stated plainly

- **It cannot write code that isn't there.** Both bugs it failed needed a
  synthesised `if/else`. No supplied edit class can invent a branch; a model
  does it in one pass. That is the division of labour, not a bug to fix later.
- **The act-to-edit mapping is engineering, not emergent.** New fault shapes
  need new edit classes. You are adopting a taxonomy someone maintains.
- **A 14-line dict reproduces the single-fault behaviour.** See below.
- It repairs; it does not review. It has no idea what your code is *for*.

## How much of it is a lookup table

```
the policy                      1,513 characters of arithmetic
entries stored                  0
single-fault situations         14 -- and ALL 14 map 1:1 to one act
lines of Python to reproduce
  the behaviour that occurs     14
of ten real bugs, single-fault   8
```

Storage-wise there is no table. Functionally, on the cases that occur, there
is — and a reviewer's 14-line dict reproduces them. The expression does compute
something a naive dict does not on *compound* faults ("lowest set bit"
reproduces only 43.8% of it), but compound rulings are also the part that
scored 0/10 before the act meanings were corrected, so that structure has never
been shown to earn anything. `proof/realrepo/not_a_lookup.py` measures both.

## Verify everything

```bash
./verify.sh            # PYTHON=/path/to/python if pytest is in a virtualenv
```

Runs every claim above from a clean clone, including cloning a real third-party
repository, injecting a bug, and repairing it. If a line fails, the claim it
supports does not belong here.

## What changed in 0.2.0

The 0.1 release shipped a policy that **scored 0/10 on real repositories and
weakened seven test suites**. `ACT[i]` answers `BITS[i]`, so `E_ASSERT` was
answered by `RELAX_ASSERT` — *a test failed, weaken the test*. True of the toy
scripts it was authored from, exactly inverted on real code.

The expression is unchanged. Only what the acts *mean* was corrected, and that
alone moved 0/10 to 8/10. That correction now ships in `edgub/acts.py` instead
of living in a proof script.

Also fixed, all of them found by packaging or by outside review:

```
the law was passed to eval() as a STRING and recompiled every call
   345 us -> 2.13 us
"63 characters" was a regex reading the docstring, not the artefact
   the law is 1,513 characters
sit() dropped unknown observation names silently -> 0 -> SHIP
   an unrecognised fault said "ship the broken code". Now raises.
ImportError and ModuleNotFoundError were not observed at all
a missing pytest reported as 0 failures -> "everything passes"
   a debugging tool telling you your broken repo is fine. Now raises.
targets() took the deepest traceback frame, which is wrong when several
   failing tests are concatenated; it picked import machinery
the candidate screen required passing tests that can never pass
   (package-metadata failures), so every candidate was rejected
five benchmarks that could not run from a clean clone, deleted with the
   numbers they supported
```

## License

MIT.

## Fuse it to the model you already run

```python
import edgub
from edgub.fuse import fuse, Anthropic

rz = fuse(Anthropic("claude-opus-5"))
r = rz.fix(".")

r.free        # repaired by edgub, 0 tokens
r.by_model    # repaired by the model
r.tokens      # what the model actually cost
```

```
1 repaired (1 free, 0 by the model), 1 unfixed, 0 tokens, 2.3s
  free   itertoolz.unique  name item->val
  model calls made : 0
```

**This is the honest way to buy it: a token reducer, not a replacement.**
edgub repairs what your tests determine for nothing; what it cannot reach
becomes a *minimal* prompt — the failing tests and the one function — instead
of an agent shipping a repository into context. The model still decides
everything edgub could not.

```
                                    repaired    tokens
edgub alone                            8/10          0
a frontier model alone                10/10     74,964
edgub + model on the remainder        10/10     26,630   -> 64.5% saved
```

Three properties that make it safe to bolt on:

- **the failure mode is a passthrough**, never a wrong answer — anything edgub
  misses reaches your model exactly as it would have without edgub;
- **the model's patch is verified** — spliced, compiled, suite run, reverted if
  it does not hold;
- **`Callable_`** lets you measure the saving with a stand-in before spending
  anything.

### Two caveats, stated where they cannot be missed

**64.5%, not 80%.** Eight of ten never reach the model, but the two that do are
the hard ones and cost more per bug. And batching matters and has nothing to do
with edgub: one bug sent alone cost 26,646 tokens; sent as a pair, both cost
26,630. An unbatched baseline would let this read "90% saved" for identical
work. 64.5% is the matched-conditions number and the only one to quote.

**The Anthropic path is written, not exercised.** There was no API key in the
environment where this was built, so `Anthropic` is untested against the live
API; `Callable_` and the whole surrounding pipeline are tested. Do not treat
the adapter as proven until you have run it once yourself.
