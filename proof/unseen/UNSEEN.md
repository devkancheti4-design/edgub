# On a library it was never built against

`more-itertools` — 736 tests. A real keyword-gated branch removed: `chunked(...,
strict=True)` silently ignored. 2 tests break.

## Starved — no body

```
REFUSE: the examples do not distinguish any keyword's presence.
        Widened through length/type/raises/value over 2 example(s)
        and none separated them.
```

Correct, and informative. With only its own two doctest examples nothing
separated `strict=True` from `strict=False`, so it **refused and named the gap**
instead of guessing or enumerating.

This is why an earlier "zero repairs on unseen libraries" result was withdrawn:
`python -m edgub` built no model, so a refusal had nobody to ask and fell
through to a search that timed out. That measured a **data-starved
configuration**, not the architecture.

## Fused — the body supplies the material it named

```
body supplies 4 examples (~73 tokens), including the case that RAISES
   -> derived: branch on `strict`, lens=raises, 9 candidates
   -> evidence: 3 examples pass `strict` and behave differently; 3 do not

direct ask would cost ~658 tokens (the function + failing tests)
material route  ~73 tokens          9x cheaper
```

The body was asked for **data, not a fix**. The derivation stayed with the
algorithm, and the `raises` lens is a rung the widening reached on its own.

## What is proven here, and what is not

**Proven:** the refusal is accurate; naming the missing material is actionable;
supplying it lets the algorithm derive on a library it has never seen; and the
material route is an order of magnitude cheaper than a direct ask.

**Not proven:** it derived 9 *candidates* — it did not verify a repair. Fixing
`strict` needs a raised `ValueError` in the else-arm, and `synthesise` only
builds call-substitution arms, so it probably cannot construct that one. This is
one bug, in one library, with tokens counted by character estimate rather than a
live API.

## The stopping rule

The loop can never cost more than not using it:

```
budget = the cost of asking directly
stop the moment the loop has spent it, and ask directly instead
```
