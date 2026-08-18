# Using edgub on your repository

## Install

```bash
git clone https://github.com/<you>/edgub && cd edgub
pip install -e .
```

No dependencies beyond the standard library. No API key. No network.

## Run it on a failing test

```python
import subprocess, edgub

def observe(out):
    """Read pytest's output. Mechanical: no judgement."""
    return edgub.observe_traceback(out)

r = subprocess.run(["pytest", "tests", "-q", "-x"],
                   capture_output=True, text=True)
if r.returncode:
    out = r.stdout + r.stderr
    situation = edgub.sit(observe(out))
    act = edgub.ACTS[edgub.decide(situation)]        # <- 2.5 microseconds
    path, line = edgub.target_file(out)
    src = open(path).read()
    fixed = edgub.repair(act, src, out)
    if fixed != src:
        open(path, "w").write(fixed)                 # then re-run the tests
```

## Do this first, every time

**Work on a throwaway copy or a git worktree.**

```bash
git worktree add /tmp/edgub-run HEAD
```

edgub modifies source files in place and keeps trying repairs until the tests
pass. That is exactly the behaviour you do not want pointed at a branch you
care about.

**Read every diff before committing.** A repair can make a test pass without
making the code right — `RELAX_ASSERT` weakens an assertion, and
`DEFINE_NAME` binds a missing name to `0`. Both silence a failure. Neither is
necessarily correct.

## Speed

The decision costs microseconds; everything else is your test suite. If your
suite is slow, run only the failing test while iterating:

```bash
pytest "tests/test_x.py::test_y" -q     # seconds
```

On the repository used for the measurements this took a cycle from
383 seconds to 0.01 — the suite, not the debugger, was the whole cost.

## What it will not do

It will not fix a wrong operator, an off-by-one, a missing return, or anything
else with no matching repair. When the program runs cleanly and prints the
wrong answer it currently returns `SHIP`, which is wrong — treat a `SHIP` on a
still-failing suite as "no opinion", not "fixed".
