# Proof

Every figure here is reproducible from the logs and scripts in this directory.
Where a claim could not be re-measured it is marked as such rather than quoted.

---

## 1. The fair test — routing, against a frontier model

`fair_test.py`, log: `fair.log`

Both sides saw the same broken program and the same traceback, and chose from
the same eleven repairs. **Ground truth was measured by execution**: every
repair was applied and run, and the one that made the program produce the
expected output is the answer. Opus 5's choices were written into the source
**before** the ground truth was computed.

```
case            measured          the law           opus 5            who
plain-name      DEFINE_NAME       DEFINE_NAME       DEFINE_NAME       both
module-name     ADD_IMPORT        ADD_IMPORT        ADD_IMPORT        both
str-plus-int    CAST_OPERAND      CAST_OPERAND      CAST_OPERAND      both
list-index      GUARD_SUBSCRIPT   GUARD_SUBSCRIPT   GUARD_SUBSCRIPT   both
div-zero        GUARD_DIVISOR     GUARD_DIVISOR     GUARD_DIVISOR     both
missing-attr    ADD_ATTRIBUTE     ADD_ATTRIBUTE     ADD_ATTRIBUTE     both
int-of-junk     COERCE_INT        COERCE_INT        COERCE_INT        both
assert-fails    RELAX_ASSERT      RELAX_ASSERT      RELAX_ASSERT      both
nested-call     COERCE_INT        COERCE_INT        COERCE_INT        both
comprehension   GUARD_SUBSCRIPT   GUARD_SUBSCRIPT   GUARD_SUBSCRIPT   both
deep-name       DEFINE_NAME       DEFINE_NAME       DEFINE_NAME       both

  the law : 11/11        opus 5 : 11/11
```

Three cases (`chained-sub`, `computed-zero`, `float-junk`) were **excluded
because no repair in the act set works** — neither side could route them.

**Cost.** The decision is 2.5 µs, measured separately by compiling the
expression once and timing it in isolation. The `44217 us` printed in
`fair.log` is wrong: it includes a subprocess launch inside the timing loop.
The error is recorded here rather than removed from the log.

**Scope.** Fourteen cases, drawn from the eight fault families the law was
authored on, with new names, shapes and call sites. It is not a benchmark.

## 2. Generalisation

| test | script | result |
|---|---|---|
| unseen programs — new names, shapes, call sites | `reach_test.py` | **8 / 8** |
| unseen domains — classes, generators, `os.path`, parsing, config | `reach_test.py` | **6 / 8** |
| faults with **no matching act**, repaired by authoring a body from tests | `reauthor_test.py` | **4 / 6** |

The 4/6 matters most: a wrong operator has no repair in the menu, but the
correct body is derivable from five test cases. The two remaining failures are
a function returning strings and one depending on hidden state — neither is a
function of its arguments, so no arithmetic engine can express it.

## 3. The closed loop — self-improvement with no human in the cycle

`closed_loop.py`, log: `closed_loop.log`

The law starts knowing four of ten faults. When a repair fails, **the harness
detects it by running**, measures the working repair by trying every one, and
re-authors.

```
faults solved:      10 / 10
successors:         3
regressions:        0 -- none
faults outside the starting catalogue: 6, solved: 6
```

At one point re-authoring **abstained** — two events shared an input and
disagreed (`math.floor` without an import reports `NameError`, identical to a
genuinely undefined name). The loop asked a second authored law what to do
about its own contradiction; the answer was `ADD_STATE`, an observation bit
was added to separate the two cases, and the fault was fixed. No human chose
any of that.

## 4. A real repository — where it is weak

`real_repo.log`. Target: a repository with 56 tests, faults injected into real
source files, pytest as the oracle.

```
import removed      reasoner.py   ADD_IMPORT       REPAIRED
constant deleted    evaluator.py  GUARD_SUBSCRIPT  not repaired
constant deleted    engine.py     DEFINE_NAME      not repaired
bounds guard        reasoner.py   —                fault never reached
zero divisor        __init__.py   —                fault never reached

  1/5
```

**The routing held; the repairs did not.** The law chose the right act in 3 of
3 cases where the traceback was read correctly. But `DEFINE_NAME` binds a
missing name to `0`, and the deleted line was `DEFAULT_GRAMMAR = Grammar()` —
the `NameError` is silenced and the program stays broken. Two faults were
injected into code paths covered only by tests that had been deselected for
speed, so they were never reached at all.

Three defects were found here that eight synthetic domains never surfaced:

1. the traceback path matcher required an absolute path; pytest prints relative
2. the module list was hardcoded and omitted `ast`
3. `ADD_IMPORT` inserted at line 0, which breaks any file with a licence
   header, a module docstring, or `from __future__ import ...`

The third also exposed a bad check: `ast.parse` **accepts** a misplaced
`__future__` import and only `compile()` rejects it. The insertion point is
now validated with `compile()`.

## 5. What is not claimed

- Not a benchmark: 14 routing cases, 8 domain cases, one repository.
- The routing tie is on *choosing* a repair. On real code the repairs are the
  weaker half.
- `SHIP` is returned when a program runs cleanly and prints the wrong answer.
  That is a defect, not a verdict.
- The eight fault families bound what it can do. Nothing outside them is
  handled, and re-authoring cannot invent an act.
