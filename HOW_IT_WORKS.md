# How the law works, and why it is not a lookup table

```bash
python3 proof/realrepo/walkthrough.py
```

That traces one real decision end to end and **computes every number below when
you run it**. Nothing here is asserted.

## The whole policy

```
((((((((((((((((((((((x) & 32766)) & (0 - (((x) & 32766)))))...
```

63 characters of integer arithmetic. Compiled once at import, evaluated on one
integer. There is no table, no dictionary, no stored case list.

## One decision, traced

**1. The interpreter speaks.** Only exception names the run actually printed are
read. No interpretation.

```
toolz/tests/test_itertoolz.py:151: in test_nth
E   AssertionError: assert 'B' == 'C'

   observation -> {E_ASSERT}
```

**2. Pack it into an integer.** Each of the 15 observations is one bit.

```
bit  7  E_ASSERT       1        all others 0
situation = 128
```

**3. Evaluate.** `decide(128) = 7` → `ACTS[7]`.

**4. Act.** The act does not fix anything by itself. It names *which kind* of
repair to look for.

## Why that is generalisation, not retrieval

```
situations it answers                                    32,768
events it was authored from                                  11
proportion of its answers that were ever measured        0.0336%
stored entries                                                0
acts reachable                                          11 of 11, none dead
two-fault situations it rules on and was never
  authored on                                                91
```

A table over 15 bits needs 32,768 entries. This stores none, because the answer
is **computed from the integer**. It was authored from 11 measured events and
answers 32,757 situations nobody ever showed it — including 91 combinations of
two simultaneous faults that appear nowhere in its authoring set.

The repairs are not stored either. On ten real bugs, **148 candidate edits were
generated and executed**, and each survivor had to green all 185 tests.

## What the decision actually buys: the search collapses

The act names the kind of repair, and that is what makes the search small.
Measured on ten real bugs in `toolz`:

```
bug                    full space   evaluated   narrowing
merge_with_order           20,031           4      5008x
groupby_wrongvar            5,580           6       930x
itemfilter_swap             2,444           3       815x
unique_wrongvar             3,187          13       245x
reduceby_nocontinue        12,274          32       384x
partition_alwayspad           808           9        90x
sliding_off                   764          88         9x

across the completed runs:  148 evaluated out of 45,088
```

`merge_with_order` was found on the **4th candidate out of 20,031**. That is the
brain doing its job: it does not search the space, it decides which corner of it
to look in.

## The cost

```
per decision     2.2 us      ~465,000/sec
tokens           0           no key, no network, no model
```

On those same ten bugs a frontier model deciding for itself spent **74,964
tokens** and scored 10/10. The law scored 9/10 at zero.

Read the zero as the price of a **first pass**, not of the whole job. And zero
tokens is not zero cost — 148 candidates is 148 test-suite executions of real
CPU, which a token comparison hides completely.

## The honest part, and it is the important one

The worked example above answers `RELAX_ASSERT` — *weaken the failing
assertion*. On the toy scripts this law was authored from, that was right. On a
real repository it is backwards: the test is right and the library is wrong.

**As shipped, that scores 0 of 10 on real bugs and weakens 7 test suites.**

That is not a failure of the expression. The expression mapped the observation
onto act index 7 correctly and consistently every time. `ACTS[7]` is a *list
entry chosen by a human*, and the human chose wrong:

```
BITS[7] = E_ASSERT   ->   ACTS[7] = RELAX_ASSERT
```

Correct that one meaning — act 7 becomes *the library is wrong, repair it* —
leave `decide()` untouched byte for byte, and the same law scores **9 of 10 at
zero tokens** (`proof/realrepo/edgub_repair.py`).

So judge two things separately:

- **the mapping** — 63 characters, 32,768 answers from 11 events, no table
- **the act list** — supplied by a human, and wrong in the shipped version

Most of what looks like the law failing, in this project's whole history, has
been the second one.
