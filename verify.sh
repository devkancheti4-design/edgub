#!/bin/sh
# Every claim in the README, run from a clean clone. If a line fails, the claim
# it supports is not backed and does not belong in the README.
set -e
cd "$(dirname "$0")"
echo "== 1. decide() speed =="
python3 -c "
import sys, time; sys.path.insert(0,'.')
import edgub
for _ in range(200): edgub.decide(7)
N=20000; t=time.perf_counter()
for i in range(N): edgub.decide(i&255)
print('   %.2f us per call' % ((time.perf_counter()-t)/N*1e6))"
echo "== 2. self-test on toy programs =="
python3 proof/selftest.py | tail -2
echo "== 3. how one decision is made, traced =="
python3 proof/realrepo/walkthrough.py | grep -E "observation read|situation =|characters of|decide\\(|situations it answers|authored from|stored entries|NEVER authored"
echo "== 3b. is it a lookup table? =="
python3 proof/realrepo/not_a_lookup.py | grep -E "length:|entries stored|answered but never|never in the authoring"
echo "== 4. real repo: what the shipped act list rules =="
cd proof/realrepo
[ -d bugged ] || python3 inject_hard.py bugged >/dev/null
python3 spec.py hard | tail -4
echo "== 5. token cost =="
python3 token_cost.py | grep -E "tokens spent|api keys|TOTAL|opus 5 deciding|AS SHIPPED|corrected"
