"""WHAT EACH ACT MEANS. This is the part that was wrong in the first release.

`decide()` maps an observation onto an act INDEX. What that index MEANS is a
separate table, and the shipped one was authored against toy scripts where a
failing assertion really was the wrong thing. On a real repository the
assertion is right and the library is wrong, so index 7 -- answering E_ASSERT
-- meant "weaken the test". That scored 0 of 10 on real bugs and weakened seven
test suites.

Here every act repairs the LIBRARY, and each routes to the edit classes its
fault implies. The expression is untouched; only these meanings changed, and
that alone moved 0/10 to 8/10.

    index  answers      routes to
    0      PASSES       nothing -- the work is done
    1      E_NAME       identifiers
    2      E_TYPE       what is passed, and how
    3      E_INDEX      offsets and slices
    4      E_ZERO       divisors and guards
    5      E_ATTR       attributes
    6      E_VALUE      conversions and comparisons
    7      E_ASSERT     THE LIBRARY IS WRONG -- the full semantic space
    8      E_RECUR      budgets
    9      (import)     identifiers
    10     (self)       the full semantic space
"""
SEMANTIC = ("binop", "cmp", "const", "invert", "swap", "unwrap", "negate",
            "delete", "name", "attr", "drop", "insert")

# act index -> (edit classes it may reach, how wide to look)
ROUTES = {
    0:  (None, 0),
    1:  (("name", "attr"), 1),
    2:  (("drop", "unwrap", "swap", "const", "name", "cmp", "attr"), 2),
    3:  (("const", "negate", "swap", "name"), 1),
    4:  (("const", "binop", "invert", "name"), 1),
    5:  (("attr", "name"), 1),
    6:  (("const", "unwrap", "cmp", "name"), 1),
    7:  (SEMANTIC, 3),
    8:  (("const",), 1),
    9:  (("name", "attr"), 1),
    10: (SEMANTIC, 3),
}
