# Combined verification session — 2026-08-20

Three plans are each blocked on a game run, and all three ask for the same run: long
battles commanded in person. This sheet is the union of them, ordered so nothing has to
be done twice. Results go back into the three plans, not here.

| plan | what it needs | steps here |
|---|---|---|
| `2026-08-20-battle-chronicles-toast-priority.md` task 8 | the preemption lane fires, and reads as weight rather than noise | B, C, E1, F |
| `2026-08-13-battle-chronicles-expansion-plan-6-flesh.md` steps 1-9 | `BC: wound gates passed` non-zero, and the wound toast rendered | B, C, E2 |
| `2026-08-13-battle-chronicles-expansion-plan-4-rivalry.md` step 5 | a `grudge` visible on a character screen | D |

**The loc halves of plan 6 step 2 and plan 4 step 2 are already answered statically** and
do not need eyes on the rules screen. All five rules — `bc_frequency`, `bc_swing`,
`bc_aftermath`, `bc_rivalry`, `bc_wounds` — have a `rule_bc_*` name key, a `_desc`, and a
`setting_bc_*` pair for every option declared in `common/game_rules/bc_game_rules.txt`.
A raw token on that screen is now only possible via a defect `validate` would have caught.
Glance at it if the screen is open anyway; do not spend a step on it.

---

## A. Done before this sheet was written

- [x] `validate battle_chronicles --strict` — 0 errors, 2 known namespace warnings
- [x] `tools/_bcorder.py` — 238/206 pairs, 0 out-of-order, 0 depth mismatches
- [x] `ck3.py deploy battle_chronicles`, confirmed at slot 36 of the playset
- [x] logs archived to `D:/ck3/logs/archive-20260820-run6/`

## B. Launch

```bash
cd /d/ck3 && python tools/ck3.py launch --clear-logs
```

At the main menu, in another shell:

```bash
cd /d/ck3 && grep -F "Battle Chronicles" "/d/Documents/Paradox Interactive/Crusader Kings III/logs/debug.log" | head -3
cd /d/ck3 && python tools/ck3.py probe 'Compiling source'
```

Expected: a `Battle Chronicles|mod/battle_chronicles.mod|Enabled` line, and **no `bc_`
symbol** in the compile sweep. A `bc_` name there means that effect is dead at every call
site and the run would measure nothing.

## C. Play — at least three long battles, commanding in person

`is_ai = no` gates the toast counters, so watching an ally's battle measures nothing.

While playing, note by hand — **the log cannot answer either of these**:

1. **Toasts on screen per battle.** The ceiling is 6 per 30-day battle. 7+ means the
   volume model is wrong, not mistuned.
2. **Did the extra message read as the battle turning, or as one more line?** This is the
   real verdict. If it reads as noise, the answer is not a shorter cooldown — it is that
   the in-battle toast is the wrong surface, and the work belongs in a combat-end
   chronicle instead.

Also watch for a red toast titled **Carried From the Field** (plan 6). It should carry the
commander's portrait and a real name in the body. It is rare; seeing none is a valid
outcome, not a failure.

## D. Before quitting — the one thing no marker proves

Find a commander who lost a notable battle. Open his character screen and **look at his
relations**. Plan 4 has been waiting on this since the 2026-08-14 checkpoint.

| what you see | what it means |
|---|---|
| a `grudge`, tooltip reading `beat him on the field` | the saved-scope target form is right. This is the only evidence there will ever be |
| a `grudge` with a raw `bc_reason_battle_grudge` key | the effect works; one side of the loc key is misspelled |
| no `grudge`, but `BC: nemesis new` fired in the log | the saved-scope target is being declined. Stop and re-derive the target form from a shipped call site — do not guess |

## E. Quit, then wait

Exit from inside the game. **Do not force-kill it.** Then:

```bash
tasklist | grep -i ck3.exe
```

**No output before reading anything.** The process lingers ~20s at ~9 GB after the window
closes, and `debug.log` is written live — a mid-session read has put a wrong number into
this project's docs three separate times.

### E1. Toast counters

```bash
cd "/d/Documents/Paradox Interactive/Crusader Kings III/logs" && for m in "BC: toast preempt" "BC: toast rank2" "BC: moment minor" "BC: moment major" "BC: moment decisive" "BC: fired" "BC: combat end cleanup"; do printf "%-28s %s\n" "$m" "$(grep -cF "$m" debug.log)"; done
```

The first two are **player-only** — every other `BC:` marker counts the whole world.
Single digits are expected there, not a fault.

**Regression guard, read before anything else:** `BC: fired` and the three moment shares
must match Run 1b — 465 fired, 74.8 / 12.9 / 12.3. This design touched only the toast
gate; movement in those is an accident to diagnose, not a result.

### E2. Wound counters

```bash
cd "/d/Documents/Paradox Interactive/Crusader Kings III/logs" && for m in "BC: wound gates passed" "BC: wound"; do printf "%-28s %s\n" "$m" "$(grep -cF "$m" debug.log)"; done
```

**Divide both by `BC: fired`.** Raw counts are not comparable across runs of different
length; the series so far, normalised, is 1.34% then 1.72%.

| shape | reading |
|---|---|
| `gates passed` non-zero, `wound` non-zero | the pass shape. Plan 6 closes |
| `gates passed` counts, `wound` 0 | the `var:bc_battle_size >= 3` read is the rejector |
| both 0 while `BC: moment major` counts | the outer limit rejects — most likely `bc_wounds_off` or a `wounded` trait already present |
| `wound` twice in one battle | `bc_battle_wounded` is not holding. Look at `bc_clear_scratch_effect`, not `bc_wound_effect` |

Also, cheap and worth doing on a run that already happened:

```bash
cd /d/ck3 && python tools/ck3.py probe "more than one 'effect' defined"
```

Expected exit 1. Silent in game if it ever fires — the engine keeps one `effect` block by
alphabetical filename order and logs only this line.

## F. Write it down

Each plan takes its own results section — do not consolidate them here:

- toast-priority: `## Run 2 results`, with the on-screen count and the plain-words judgement
- plan 6: a run-log entry in the mod `README.md`, in the existing dated shape
- plan 4: the grudge observation, in the README's "Not yet verified in game" entry, which
  then gets removed

Then `project_battle_chronicles.md` in workspace memory still carries "unmeasured since
2026-08-15" as a standing risk. Replace it with what this run measured.
