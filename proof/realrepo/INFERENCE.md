# Inference, not enumeration

The law decides which class of repair a fault is. The repair itself is
**generalised from the examples the body supplies** — the function's own
doctests and the failing test's assertions. Enumeration runs only if that
yields nothing.

```
edgub: 1 repaired, 1 left for a model, 3.5s, 0 tokens
  repaired  itertoolz.diff  INFER/inference via zip_longest(..., fillvalue=default)
            4 candidates
```

`diff` is the bug enumeration exhausted **25,057 candidates** on and never
solved. Inference reaches it in **4**, because the examples state the answer:

```
list(diff([1,2,3],[1,2,10,100]))                -> [(3,10)]
list(diff([1,2,3],[1,2,10,100], default=None))  -> [(3,10),(None,100)]

2 examples pass `default` and produce longer output; 6 do not
   -> the function BRANCHES on `default`.          Read, not searched.
one callable in scope accepts a padding keyword
   -> that is the other arm.                       Read, not searched.
```

The derived rule is stored, keyed by the *shape* of the fault with no project,
file or function name in it, so the next occurrence is a lookup:

```
E_ASSERT|REPAIR_LIBRARY|keyword=default|kind=missing_branch
```

## Honestly unresolved

`partition_alwayspad` is **not** repaired. Every inference candidate either
fails to improve the suite or breaks the module at import.

An earlier draft of this file claimed it was repaired. That was wrong: the
standalone harness checked `"failed" not in output`, and a pytest *collection
error* prints no `"failed"`, so a module that would not import was read as a
pass. The product caught what my test of the product did not.

## Defects this path exposed, all in the plumbing

```
inference was built and never wired in -- the product ran enumeration
the damage gate counted comments file-wide, so any target function
  containing one had every candidate vetoed
a candidate breaking the import aborted the whole run instead of being
  rejected as a bad candidate
```

## Both repaired, and checked against a reference — not a test suite

```
partition_alwayspad   1 repaired, 3.5s, 0 tokens, 4 candidates
diff_nodefault        1 repaired, 4.8s, 0 tokens, 7 candidates
```

Enumeration exhausted **808** and **25,057** candidates on these and solved
neither.

Verified the way that actually settles it — against the pre-injection original
over every input in the space, not against the suite:

```
partition_alwayspad   AGREES WITH THE ORIGINAL on all 360 inputs
diff_nodefault        AGREES WITH THE ORIGINAL on all 147 inputs
```

That distinction is not pedantry. Three separate false results today greened a
test suite: `diff(..., fillvalue=pad)` was the wrong callee, tabulate's rewritten
file was 1,397 deleted lines, and an earlier "partition repaired" was a module
that would not import. **A passing suite is a sample. A reference is a verdict.**

## The two synthesis bugs that were blocking partition

```
it appended `fillvalue=pad` to a call that ALREADY had it
   -> SyntaxError: keyword argument repeated; the module would not import

it generated only one orientation
   -> diff's body pads nothing and needs the padding arm ADDED
      partition's body already pads and needs the plain arm RESTORED
```

Both orientations are now generated and every candidate is compiled before it
is offered.

## What is still missing, named rather than hidden

edgub has no **REFUSE** verdict. When it cannot reach a repair it prints a
sentence I wrote — "the supplied edit classes cannot express this repair" —
rather than deriving what was missing. A reasoner that says *more declared
material, not more depth* would name the gap. That is the next piece, and it is
not built.
