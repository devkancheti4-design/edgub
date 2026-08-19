# How the law works — and how much of it is a lookup table

```bash
python3 proof/realrepo/walkthrough.py
```

That traces one real decision end to end and **computes every number below when
you run it**. Nothing here is asserted.

## The whole policy

```
((((((((((((((((((((((x) & 32766)) & (0 - (((x) & 32766)))))...
```

**1,513 characters** of integer arithmetic (`len(edgub.LAW)`). Compiled once at import, evaluated on one
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

## How much of it is a lookup table — measured, not argued

An outside reviewer traced the mechanism and called it an error-type → act table
encoded as arithmetic. **They are substantially right, and here is the number:**

```
single-fault situations                        14
of those, how many map 1:1 to one act          14   -- all of them
lines of Python needed to reproduce that       14
of the ten real toolz bugs, how many were
  single-fault                                  8   -- the dict handles them
```

So in practice a 14-line dictionary reproduces the behaviour that actually
occurs. The honest split:

- **Storage** — 0 entries. True, and uninteresting on its own.
- **Function on single faults** — a 1:1 map. The reviewer's dict wins.
- **Function on compound faults** — *not* the naive "lowest set bit" rule; that
  reproduces only 43.8% of `decide()`. So the expression computes something a
  simple dict does not.

But that last point only counts for something if the compound rulings are
*good*, and **on real repositories the shipped act list scored 0 of 10**. So the
part that is not a table is also the part that has never been shown to earn its
keep. Both halves of that sentence are ours to own.

What remains true and is worth the reader's time: it was authored from 11
measured events, it answers every situation without storing any, and correcting
one act's *meaning* took it from 0/10 to 9/10 with the expression untouched.
That is a claim about the act list being separable from the mapping — not a
claim that the mapping is deep.

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
