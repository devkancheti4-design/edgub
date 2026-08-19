# edgub

A free, offline debugging policy. One arithmetic expression maps what the
interpreter said to what to do about it. No API key, no network, no model.

```python
import edgub
act = edgub.ACTS[edgub.decide(edgub.sit({"E_NAME"}))]   # -> DEFINE_NAME
```

## Everything claimed here can be run

```bash
./verify.sh
```

That script runs every claim below from a clean clone. If a line fails, the
claim is not backed and does not belong here.

```
decide()                       2.2 us per call, ~465,000 calls/sec, 0 tokens
self-test                      11 / 11 repaired
ten hard bugs in real toolz    see proof/realrepo/REALREPO.md
```

## What this repo previously claimed and could not back

An outside reviewer tried to reproduce the headline numbers from a clean clone.
Almost none of them ran. Rather than leave them up, they have been removed:

```
"2.5 us per decision"        the shipped decide() measured 345 us -- 138x off.
                             LAW was passed to eval() as a STRING, so Python
                             recompiled it on every call. The published figure
                             was never true of the shipped code path.
                             FIXED: the law is compiled once at import.
                             Now measured at 2.2 us, and verify.sh proves it.

three_way.py    11/11 vs Opus 5      needed law_v3.json   -- never committed
damage_test.py  0/6 vs 5/6           needed repo_pristine/ -- never committed
token_cost.py   82% fewer tokens     needed a module that does not exist
hard_cases.py, mixed_corpus.py       could not import edgub at all
fair_test.py, reach_test.py,
reauthor_test.py                     did not even parse -- broken by an earlier
                                     pass that stripped private-engine calls
                                     and left `for` loops with no body

All of the above are DELETED, along with the numbers they supported. Their logs
are deleted too: a log you cannot regenerate is not evidence.
```

Five of eight headline benchmarks could not run. That is disqualifying for a
tool whose entire pitch is measurement, and the reviewer was right to say so.

## What is actually true, and measured

**On toy programs** — 11/11, reproducible via `proof/selftest.py`.

**On real repositories, as shipped: it fails.** Ten bugs of the kind that
survive review in `toolz` (3,346 lines, 185 tests): the act list scores
**0 of 10 and weakens seven test suites**. `ACT[i]` answers `BITS[i]`, so
`E_ASSERT` is answered by `RELAX_ASSERT` — *a test failed, weaken the test*.
That pairing was measured on toy scripts and is exactly inverted on real code.
None of the eleven acts repairs a wrong value; all eleven suppress an exception.

**With the act meanings corrected** and `edgub.decide()` byte-for-byte
unchanged, the same law scores **9 of 10** at zero tokens, evaluating 148
candidates out of a 45,088 space.

Method, tables, and limits: [proof/realrepo/REALREPO.md](proof/realrepo/REALREPO.md)

## What it is for

A cheap deterministic first pass that repairs the mechanical fraction offline
and hands the rest to a model. It is not a replacement for one: on the same ten
bugs a frontier model deciding for itself scored 10/10.

## Limits

- The act to edit-class mapping is engineering, not emergent. Every new fault
  shape is a commit.
- Two of the nine repairs pass all 185 tests without being the original code.
  The suite is a weaker oracle than the question.
- One bug needs a synthesised `if/else`; no supplied edit reaches it.
- `toolz` is a famous public library, so a frontier model's 10/10 is partly
  recall. On private code that advantage shrinks.

## Install

```bash
git clone https://github.com/devkancheti4-design/edgub && cd edgub
./verify.sh
```

Standard library only. No dependencies.

## Is it a lookup table?

The commonest reading of this project is that `decide()` is a disguised table of
memorised answers. `proof/realrepo/not_a_lookup.py` settles it:

```
the entire policy               63 characters of arithmetic
situations it answers           32,768
events it was authored from     11        (0.034% of them)
acts reachable                  11 of 11, none dead
two-fault situations it rules
on and was never authored on    91
entries stored                  0
```

The repairs are not stored either: on the ten hard bugs, 148 candidate edits
were generated and each had to green all 185 tests. Nothing is retrieved.

## Token cost

`proof/realrepo/token_cost.py`. The law's side is measured when you run it; the
model's side is a recorded measurement from 2026-08-19, listed with provenance
in the file header rather than estimated.

```
opus 5 deciding for itself             10/10    74,964 tokens   ($0.38-$1.87)
edgub as shipped                        0/10         0 tokens   + 7 test suites weakened
edgub with act meanings corrected       9/10         0 tokens
```

Two honest qualifications, both in the script's own output:

- **The 9/10 is not the shipped package.** It lives in
  `proof/realrepo/edgub_repair.py`. What ships scores 0/10.
- **Zero tokens is not zero cost.** That run evaluated 148 candidate programs,
  each a test-suite execution. On a wide function with weak doctests it is
  minutes of CPU. A token comparison hides this entirely.
