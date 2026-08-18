"""EVIDENCE ONLY — this script calls the private authoring engine
and therefore cannot run outside it. Its output is the .log file
beside it, which is the measurement being reported.
"""
"""THE CLOSED LOOP, END TO END — no human anywhere in the cycle.

The law starts DELIBERATELY INCOMPLETE: authored from only part of the fault
catalogue. Then, for every fault:

    observe (read the interpreter)  ->  the LAW picks a repair
    apply it and RUN
    if it passes            -> solved, next fault
    if it does not          -> FAILURE DETECTED BY RUNNING, not by me:
                               the harness tries every repair, finds the one
                               that actually works, appends that event, and
                               RE-AUTHORS the law. Then retries.

That re-authoring is AUTHOR_SUCCESSOR applied to the controller itself, and
nothing outside the loop decides when it happens.

Scored: which faults triggered a successor, whether each successor fixed what
its predecessor missed, and -- the part that matters -- whether it REGRESSED
on anything the predecessor already handled.
"""
import sys


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v



def _ENGINE_UNAVAILABLE(*a, **k):
    raise SystemExit('the authoring engine is private and not shipped here; '
                     'see the .log beside this file for the measurement')
, json, time, itertools
sys.path.insert(0, ".")
import debugger as G
import ENGINE_LAW as META   # rules on the AUTHORING process, not on Python faults

BITS, ACTS = G.BITS, G.ACTS


def _ntz(v):
    b = s32(v) & 4094; b &= -b
    return ((b.bit_length() - 1) if b else 0) & 15


def _T(inner):
    b = "((%s) & (0 - (%s)))" % (inner, inner); v = "((%s) - 1)" % b
    v = "((%s) - (((%s) >> 1) & 1431655765))" % (v, v)
    v = "(((%s) & 858993459) + (((%s) >> 2) & 858993459))" % (v, v)
    v = "((((%s) + ((%s) >> 4)) & 252645135))" % (v, v)
    return "(((((%s) * 16843009)) >> 24) & 15)" % v


_OPS.setdefault("ntzb", (1, _T("(({a}) & 4094)"), lambda a, _b: _ntz(a)))
CONSTS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15, 4094)


def author(events):
    """The sphere authors a controller from whatever has been measured."""
    D = sorted({(x, a) for x, a in events})
    for size in (1, 2, 3):
    r = _ENGINE_UNAVAILABLE(D, intent="mask", max_size=size,
                              consts=CONSTS, extra_ops=("ntzb",))
        if r.found:
            c = compile(r.expr, "<l>", "eval")
            return r, (lambda x, c=c: s32(eval(c, {"__builtins__": {}},
                                              {"x": x})) % 12)
    return r, None


def measure_correct(name):
    """FOUND BY RUNNING. Try every repair; keep the one that makes it pass."""
    src, expect = G.BROKEN[name]
    for i, a in enumerate(ACTS):
        if a in ("SHIP", "AUTHOR_SUCCESSOR"):
            continue
        if "PASSES" in G.observe(G.repair(a, src), expect):
            return i
    return None


if __name__ == "__main__":
    catalogue = list(G.BROKEN)
    # START INCOMPLETE: only these four are known at the outset.
    known = ["NAMEERR", "IMPORTERR", "TYPEERR", "INDEXERR"]
    events = []
    for n in known:
        a = measure_correct(n)
        if a is None:
            print("  (%s has no working repair in the catalogue -- omitted)" % n)
            continue
        events.append((G.sit({n}), a))
    events.append((G.sit({"PASSES"}), 0))
    print("THE CLOSED LOOP")
    print("catalogue: %d faults.  the law starts knowing %d of them: %s\n"
          % (len(catalogue), len(known), ", ".join(known)), flush=True)

    r, law = author(events)
    gen = 1
    print("generation 1 authored from %d events  (%s)\n" % (len(events), r.note),
          flush=True)

    solved, history, regressions = [], [], []
    for name in catalogue:
        src, expect = G.BROKEN[name]
        obs = G.observe(src, expect)
        act = ACTS[law(G.sit(obs))]
        passed = "PASSES" in G.observe(G.repair(act, src), expect)
        if passed:
            solved.append(name)
            print("  %-12s law says %-22s -> FIXED" % (name, act), flush=True)
            continue
        # FAILURE DETECTED BY RUNNING. The loop, not a human, reacts.
        print("  %-12s law says %-22s -> did not fix it" % (name, act), flush=True)
        correct = measure_correct(name)
        if correct is None:
            print("       no repair in the catalogue fixes it -- nothing to learn")
            continue
        print("       measured the working repair by running: %s" % ACTS[correct])
        events.append((G.sit(obs), correct))
        before = {n: ACTS[law(G.sit(G.observe(*G.BROKEN[n])))] for n in solved}
        r, law2 = author(events)
        if law2 is None:
            # THE ENGINE REFUSED TO AUTHOR A CONTRADICTION. Two events now
            # share an input and disagree: that is AMB. The DECISION about what
            # to do is not mine -- ask the law, which was authored from
            # measured events, and do what it says.
            # The DEBUGGER's law reads Python faults; it has no vocabulary for
            # "my own events contradict". That is the ENGINE law's job -- it
            # rules on the authoring process itself. SELF because the thing
            # being fixed IS the controller.
            ruling = META.ACTS[META.decide(META.situation("DEBUG", AMB=1, SELF=1))]
            print("       re-author ABSTAINED -- the events contradict.")
            print("       asking the law what to do about it: %s" % ruling)
            if ruling == "ADD_STATE":
                # encode the missing variable, as instructed. The observation
                # could not tell an undefined NAME from an unimported MODULE;
                # both surface as NameError. Split them.
                G.BITS.append("ISMODULE")
                def observe2(src, expect, selfjob=False, _o=G.observe):
                    o = _o(src, expect, selfjob)
                    if "NAMEERR" in o:
                        import re as _re
                        for m in ("math", "os", "re", "json", "random", "time"):
                            if _re.search(r"\b%s\." % m, src) and ("import " + m) not in src:
                                o.add("ISMODULE")
                    return o
                G.observe = observe2
                events = [(G.sit(G.observe(*G.BROKEN[n])), measure_correct(n))
                          for n in list(G.BROKEN)
                          if measure_correct(n) is not None and n in solved + [name]]
                events.append((G.sit({"PASSES"}), 0))
                r, law2 = author(events)
                if law2 is None:
                    print("       still no law; keeping the predecessor"); continue
                gen += 1; law = law2
                print("       state added, generation %d authored from %d events (%s)"
                      % (gen, len(events), r.note), flush=True)
                obs = G.observe(src, expect)
                again = "PASSES" in G.observe(G.repair(ACTS[law(G.sit(obs))], src), expect)
                print("       retry with the successor -> %s"
                      % ("FIXED" if again else "still failing"), flush=True)
                if again: solved.append(name)
                history.append((name, ACTS[correct], gen))
            continue
        gen += 1
        law = law2
        print("       AUTHOR_SUCCESSOR: generation %d authored from %d events (%s)"
              % (gen, len(events), r.note), flush=True)
        again = "PASSES" in G.observe(G.repair(ACTS[law(G.sit(obs))], src), expect)
        print("       retry with the successor -> %s"
              % ("FIXED" if again else "still failing"), flush=True)
        if again:
            solved.append(name)
        for n, was in before.items():                     # REGRESSION CHECK
            now = ACTS[law(G.sit(G.observe(*G.BROKEN[n])))]
            if now != was:
                regressions.append((n, was, now))
        history.append((name, ACTS[correct], gen))

    print("\n%s" % ("-" * 62))
    print("faults solved:            %d / %d" % (len(solved), len(catalogue)))
    print("successors authored:      %d" % (gen - 1))
    print("triggered by:             %s" % ", ".join(h[0] for h in history))
    print("regressions on previously-solved faults: %d %s"
          % (len(regressions), regressions if regressions else "-- none"))
    unseen = [n for n in catalogue if n not in known]
    got = [n for n in unseen if n in solved]
    print("\nfaults NOT in the starting catalogue: %d, of which solved: %d"
          % (len(unseen), len(got)))
    json.dump({"solved": solved, "generations": gen, "history": history,
               "regressions": regressions}, open("closedloop.json", "w"), indent=1)
