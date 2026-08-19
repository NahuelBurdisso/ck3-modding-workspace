# Battle Chronicles - run log

Every in-game run, oldest first. Source repo: `../../mods/battle_chronicles`.
Read this before designing a run: it is the record of what has actually been
measured, as opposed to what has been reasoned about.

## First live run (2026-08-12)

8 of 10 events fired. `probe 'BC:'` counts: van_breaks_through 16,
horse_killed 15, banner_falls 10, flank_collapses 7, ground_favours_us 5,
rally_the_line 5, shieldbrother_forged 3, lines_bogged_down 1, plus 40 cleanup
calls and one 0003 pop-up.

- **Resolved:** `bc_script_values.txt` works. Reading `side_strength` into a
  script value and multiplying is valid — `bc_flank_collapses` and
  `bc_van_breaks_through` both fired.
- **Two bugs found and fixed:** the opinion modifiers needed a *positive*
  `monthly_change` (a decay rate, not a signed drift), and `add_gold = -100` is
  rejected outright — now `remove_short_term_gold = 100`.
- **Never fired:** both knight events. Diagnosed and fixed — see below.

## Changes made after that run

- **Knight events were unreachable, for three compounding reasons.** The pool
  they compete in is `knight_none` at `base = 2000`, twice the commander pool's,
  so `base = 40` was ~2% of a roll before any gate applied. On top of that,
  `prowess <= 6` describes almost no knight — knights are *selected* for prowess.
  Now `base = 150`, `prowess >= 10` for the breach, and `craven OR prowess <= 8`
  for the disgrace, which is the better story regardless.
- **Every gameplay effect moved out of its toast.** The stated reason — that a
  toast body only runs for a character a player is playing — was a *guess* from
  the documentation wording, and the 2026-08-13 run disproved it (see below).
  The move was still correct; the justification was not.
- **Knight toasts now address the side commander.** Raised on the knight, they
  reached nobody.
- **Weights retuned** against the observed distribution: `horse_killed` 60 → 40
  (no situational gate, was behaving like a second `none`), `lines_bogged_down`
  60 → 100 (terrain gate is narrow enough on its own), `van_breaks_through`'s
  martial bonus 40 → 25.
- **Shieldbrothers now leave a memory**, `bc_shieldbrother_memory`, forty years,
  one for each man naming the other. Opinion decays; this does not.

## Review pass, 2026-08-12 (four bugs, all found by reading)

- **The knight's opinion ran backwards.** `bc_knight_holds_the_breach` used
  `add_opinion = { target = liege }`, which raises *the knight's* opinion of his
  lord. "Stood Fast in Battle" is the lord's view of the knight. Now
  `reverse_add_opinion`, matching the grudge in `bc_knight_shames_himself`.
- **Two events skipped the tier gate.** `bc_flank_collapses` had no
  `NOT = { bc_is_faltering_trigger }` and `bc_van_breaks_through` had no
  `NOT = { bc_has_momentum_trigger }`. Tiers are separate modifier keys, so a
  commander could carry minor and major at once and sit at ±9 — off the end of
  the ladder everything else is tuned against.
- **`mountains` was in both terrain lists**, so mountain ground both favoured
  you and bogged you down, and the two events competed for the same roll. It is
  now only in the bogging list; hills and forest already carry "good defensive
  ground", and wetlands and jungle alone are close to nonexistent in Westeros.
- **Shieldbrother burned its cooldown on a no-op.** `is_valid` can only ask
  whether the side has two knights, not whether a second one is off cooldown, so
  the event could win a roll and find nobody to pair with — after already
  spending the knight's 15-day lockout and logging a fire. Nothing happens now
  until the partner exists.

## Calibration run, 2026-08-13 (39 combat ends, both sides logged)

The grade's thresholds were seeded from vanilla's own numbers and then measured
with temporary ladder markers. Vanilla's numbers turned out to be the wrong
*shape*, not merely the wrong size — **three of the five rows never fired once**:

| row | ladder | verdict |
|---|---|---|
| size | <5k 26 / 5-10k 8 / 10-20k 5 / 20k+ **0** | 20k and 30k were dead. Now 10k / 20k. |
| blood | <25 3 / 25-50 29 / 50-75 7 / 75+ **0** | 75 was dead. Now 50 (top 18%). |
| odds | even 9 / 1.2x 9 / 1.5x 11 / 2x 10 | 1.5x fired on **54%** and was carrying the whole trigger. Now 2x (top 26%). |
| warscore | <10 30 / 10-25 3 / 25-50 2 / 50+ 4 | 25 already sat at the top 15%. Kept. |

The three ratio rows are scale-free and will hold as hosts grow. Size is the only
absolute, which is why both rungs are set above the sample rather than fitted to
it — 20k is reserved for late-campaign hosts and is meant to age into relevance.
Re-derive by restoring the ladders from git history, not by guessing.

- **Resolved:** `side_max_army_size` works on the LEFT of a comparison. It had
  zero script precedent anywhere in vanilla, AGOT or the playset. A control
  ladder against plain constants left its `else` branch, and the odds ladder
  spread across all four buckets instead of collapsing to one.
- **Resolved:** a `send_interface_toast` body **does** run for an AI character —
  `fired bc_knight_holds_the_breach` 14 == `toast body ran` 14.
- **Resolved:** all 11 phase events now fire, including
  `bc_knight_shames_himself` (11×), which never fired before the retune.
- **Resolved:** symmetry holds empirically. Every ladder matches rung-for-rung
  between `.0091` and `.0092` across all 39 battles, and `win notable` 5 ==
  `lose notable` 5. Only the per-side host ladder differs, which is correct.
- **Resolved:** zero mod-attributable lines in `error.log`.

## Confirmation run, 2026-08-13 (Generous, 5 combat ends)

A second, short run on `bc_aftermath_generous` to settle the two things the
calibration run could not.

- **Resolved: two knights on the same side both get a memory of the same
  battle.** Checked by eye in the memories window on two different knights after
  a player-fought battle; both name the same province. This was the one thing in
  the design no log could answer, and it is the load-bearing proof that
  `bc_battle_memory_effect` is iterator-safe — the `random_memory` +
  `NOT = { has_variable = battle_location }` idiom does not let the second
  knight's `set_variable` land on the first knight's memory.
- **Resolved: `bc_aftermath_generous` executes.** 3 of 5 battles graded notable
  against a Default rate that is now well under the 13% the calibration run
  measured on looser thresholds.
- **Symmetry held again:** win notable 3 == lose notable 3, win not-notable 2 ==
  lose not-notable 2. All 5 battles, both sides, same verdict.
- Zero mod-attributable lines in `error.log`.

## Forced-nickname run, 2026-08-14 (expansion plan 1, task 2)

The nickname reward path had never executed, so plan 1 forced it before plan 1
task 4 refactors it. The gate was temporarily reduced to `has_any_nickname = no`
— dropping `exists = var:bc_notable_battles`, `var:bc_notable_battles >= 3` and
`martial >= 14` — and restored afterwards with `git checkout --`. No source
change survives this run.

- **Resolved:** `bc_aftermath_nickname_effect` executes. `BC: nickname awarded`
  appeared 3 times over 4 notable wins, and the toast rendered in game. The name
  drawn was `nick_agot_greycloak`, so the `random_list` of 27 and AGOT's nickname
  keys both resolve.
- **The toast is addressed correctly.** It reached the player.
- **The toast text is generic and that is a real gap.** All 27 nicknames share one
  `bc_aftermath_nickname_toast_desc`, which never names the nickname it just gave
  — the player sees "men have started calling him something" and has to open the
  character to learn what. Noted for plan 6.
- **Error sweep clean.** `probe "bc_"` returned 15 groups, all whitelisted: the
  mod's own `BC:` markers, the launcher's `BC Spike|...|Disabled` line, and two
  engine load lines (`NAMESPACE > 'bc_chronicles' is set to #4180000`,
  `Loaded [6] events from 'events/bc_events.txt'`). Zero lines in `error.log`.
- **A wasted run came first, and the cause is worth writing down.** The mod had
  fallen out of `dlc_load.json` since 2026-08-12, so the first attempt produced
  zero `BC:` lines from a full battle. `deploy` writes the pointer `.mod` only; it
  does not enable the mod. Check `debug.log` for
  `Battle Chronicles|mod/battle_chronicles.mod|Enabled` before trusting any run.

## DIAG run, 2026-08-14 (expansion plan 1, task 15)

Five open questions were instrumented with pure `debug_log` markers and answered
in one session. 137 combat ends per grader. The DIAG markers are temporary and
come out in task 16; the answers are permanent and live here.

- **Q1 — commander trait density.** n=267 side commanders: 0 traits 153, 1 trait
  110, 2 traits 3, 3+ traits 1. `number_of_commander_traits < 3` passes 99.6% of
  the time, so it is not a gate in practice. Keep it; it costs nothing and it
  covers the one case in 267.
- **Q2 — `scope = combat` events work; the combat links do not.**
  `bc_chronicles.0900` — the probe event, since retired — fired **151** times, so a
  `scope = combat` event dispatched from `on_combat_start` is valid even though
  nothing in vanilla or AGOT declares one. But `combat_attacker.side_commander` and
  `combat_defender.side_commander` each resolved **zero** times from inside it, and
  `?=` swallowed both failures in silence.
  **This conclusion was later superseded — see the 2026-08-14 run.** The two links
  were probably never the problem: no commander is assigned to a combat side at
  `on_combat_start` at all, so *every* route out of that hook finds nobody. The
  hook is now unclaimed and the opening runs from inside the battle.
- **Q3 — battle size.** Per side: 5k+ 46, 3k 42, 2k 31, 1k 14, under-1k 4. The
  invented 2,000 boundary in `bc_battle_open_effect` splits the low band 73/18
  instead of leaving one undivided lump. Keep it.
- **Q4 — a toast body DOES run for an AI subject.** Split by subject: human 0,
  AI 117, and the marker *inside* the toast ran 117 times. **B == H + A**, so
  nesting is not what suppresses anything. This retires the mod's original stated
  reason for keeping effects out of toasts — the practice stays, the explanation
  was wrong. The earlier probe could not settle this because it did not split by
  who was playing the subject.
- **Q5 — terrain census.** rough 58, forest 32, winter 20, open 19, jungle 8,
  **desert 0**, and `NONE MATCHED` **0** — the `agot_is_<x>_terrain` ladder is
  exhaustive over everything that actually occurred. Desert's zero is recorded
  rather than acted on; the arm stays.
- **Other counts:** `win notable` 79 / `lose notable` 79 and `win not notable` 58
  / `lose not notable` 58, perfectly symmetric as they must be.
  `BC: nickname awarded` 5, this time under the real gate.

### The run also exposed a defect that made the whole ledger dead

`bc_record_moment_effect` declared `SWING` in its signature and read it nowhere.
CK3 does not ignore an unused parameter — it **refuses to compile the effect**:

```
[E] Compiling source for bc_record_moment_effect failed for unknown arguments: SWING
    bc_ledger_effects.txt line: 119
```

thirteen times at load, and **zero** `BC: moment` lines all session. All 18 call
sites were silently dead. Nothing else broke: no toast, no event, no call site
complained. The fix reads the parameter with a two-arm log rather than deleting
it, so plan 6's wound gate keeps the `SWING = down` hook it is written against.

Three follow-on lines were `Variable 'X' is used but is never set` for
`bc_battle_style`, `bc_battle_tier` and `bc_battle_wounded` (twice each). The
first two resolve once the seam compiles. The third is genuine and stays until
plan 6 — and it corrects a claim the plan made in passing: `remove_variable` on a
never-set variable **does** log.

## Checkpoint run, 2026-08-14 (plans 2, 3 and 4 in one session)

Three deferred runtime checkpoints — plan 2 task 12, plan 3 task 10, plan 4 task
11 — run together on one debug session rather than three. 37 notable losses, 707
moments recorded.

**Error sweep clean.** `error.log` holds exactly one distinct `bc_` group:
`Variable 'bc_battle_wounded' is used but is never set`, twice, which is the
known plan-6 debt, since retired — `bc_wound_effect` writes the variable, and the
error sweep under "Confirmation run, 2026-08-15" below found no `bc_` group at
all. Every `debug.log` group is either a mod marker or one of the two engine
load lines plan 1 carved out. **Zero missing-variable reads** for anything plans
2, 3 or 4 introduced — which is the real result, because all three read
variables that may not exist and rely on nested guards rather than
short-circuiting.

### Plan 2 — the ledger

- `BC: size` covered 3 of 4 bands (size 2 ×120, size 3 ×96, size 1 ×40).
- `BC: verb` hit **all four** verbs: shieldwall 57, pursuit 42, bloodied 52,
  spent horse 40. The verb table is exercised end to end.
- `BC: chronicle mark commander` ×139.
- **`BC: floor admitted` never fired.** Per plan 2 task 12 step 6 this is
  *inconclusive, not a failure* — that row only applies when the mark marker is
  absent, and it fired 139 times. Retry recipe: two battles back to back with the
  same commander. **The floor is untested, not broken.** Every other empty probe
  in plan 2 means a defect; this one does not, and it is the result a later
  reader is most likely to misremember.

Two structural notes from plan 2 that belong with these counts:

- **The battle-size boundary is measured, not invented.** Q3's census (per side:
  5k+ 46, 3k 42, 2k 31, 1k 14, under-1k 4) is what the 2,000 rung in
  `bc_battle_open_effect` is set against — it splits the low band 73/18 rather
  than leaving one lump. Plan 6's wound gate inherits it.
- **All four verbs are reachable from the shipped call sites**, so a missing verb
  after several varied battles is a defect to investigate, not a shrug. What is
  unreachable is three `(KIND, SWING)` *pairs* out of twelve — `wild`/`up`,
  `entrenched`/`down`, `ordered`/`down` — which is why only the `ordered` row of
  the verb ladder tests `SWING` at all.
- **`bc_mark_chronicle_effect` and `bc_chronicle_ready_trigger` are knight-only
  now.** The commander pool got its own pair, so the two pacing budgets stopped
  competing: a commander moment no longer spends a knight's slot.
- **Known pre-existing hazard, not fixed and not worsened.** A pop-up option
  answered *after* combat ends applies its momentum modifier with a fresh 20-day
  duration, and `bc_cleanup_effect` has already run, so nothing strips it until
  it expires. This predates plans 1 and 2 and affects `bc_chronicles.0001`–`.0003`;
  the 60-day pop-up cooldown keeps the window narrow. The family-2 modifiers are
  immune only as a side effect of the `exists = var:bc_battle_size` guard, which
  is there for correctness of the read — **do not remove that guard on the
  grounds that the variable is always written, because at that call site it is
  not.**

### Plan 3 — style and terrain reputation

| | reset | streak | award |
|---|---|---|---|
| style | 67 | 7 | **1** |
| terrain | 69 | 8 | **8** |

Terrain awarded across 3 distinct argument hashes.
**No `BC: terrain NONE MATCHED`** — the terrain ladder is still exhaustive under
the reputation caller, matching Q5. **No `BC: award blocked` of any kind**, which
confirms Q1's estimate that the trait-count budget gate passes ~99.6% of the time
and shows style and terrain never collided over the same battle.

### Plan 4 — the nemesis

`BC: nemesis new` ×32, `escalate` ×6, `held` ×1, `rung grudge` ×26, `rung rival`
×12.

- **The accounting is exact.** At the first snapshot new 30 + escalate 6 + held 1
  = 37 = exactly the 37 `BC: lose notable`. Nothing was swallowed by the entry
  point's nested guards on `bc_battle_foe` existence and liveness.
- **`rung rival` (12) exceeding `escalate` (6) proves the wipe branch.** A first
  loss can only land on the rival rung if `bc_rivalry_step_value` returned 2, so
  `scope:wipe` resolves inside the script value — which had no precedent.
- **The descent path is unverified.** `decrement`, `cleared`, `wipe` and
  `rule off` were all absent, for the ordinary reason that nobody beat their
  nemesis in one session. All four are permanent markers and will report
  themselves.

### Bonus: plan 1's last open done-when closed

`BC: moment decisive` fired once. It had been 0 across 707 moments in the DIAG
run, and it was the single unmet criterion left on plan 1.

## Sweep run, 2026-08-14 (plan 5 task 11 and plan 6 task 6 in one session)

Counts below are the whole `debug.log` — 5,623 `BC:` hits over 96 distinct
markers, 169 combat ends per side, 137 notable wins and 137 notable losses. Three
results, two of them failures, and both failures were diagnosable from the marker
counts alone.

### The eve never reached a single commander, and the ratio said why

- `BC: eve fired` **68**, `BC: eve side` **136**, `BC: eve commander` **0**.

136 is exactly twice 68, so the `scope = combat` event dispatched and
`every_combat_side` visited both sides of every one of those 68 combats. Both
links worked. `side_commander` then produced nobody, 136 times out of 136.

That is not a broken scope link. The same `side_commander` reached a commander
**385** times in the same log through `BC: chronicle mark commander`. The
difference is *when*: **no commander is assigned to a combat side at
`on_combat_start`.** This also retires the DIAG Q2 conclusion above —
`combat_attacker` / `combat_defender` were very likely never the problem, there
was simply nobody there to find.

There is no other pre-battle hook in the on_action dump, so no routing fixes it.
The opening moved **into** the battle: `bc_eve_offer_effect` is now called from
the end of `bc_battle_open_effect`, which already runs on the side commander and
already holds the foe and the size, and gates itself to the first moment with
`NOT = { exists = var:bc_battle_moments }`. `on_combat_start` is left unclaimed
with the measurement written into the on_action file.

**The general lesson, which cost two runs: a `?=` block that never runs is
indistinguishable from one that had nothing to do.** Only the marker inside it
told the difference.

### The dead-knight toast was watching the wrong side

- `BC: dead knights` **0**, across 274 notable grader runs.

Vanilla kills knights on **one** side and not from the hook we were on.
`combat_event.1001` walks the winner at AGOT `combat_events.txt:846` only to write
battle history; it does its killing at `:849`, inside
`enemy_side = { every_side_knight = { ... } }`. So the dead knights of a battle
are always the **loser's**, and they are made dead on the **winner's** hook — a
place `bc_chronicles.0092` can never be ordered after.

The toast now lives once, in `.0091`, reaching across to `enemy_side` and
addressing the loser's commander. That requires our grader to dispatch after
`combat_event.1001`, which is why the on_action file is now
`zz_bc_on_actions.txt`: the merged `events` list is ordered by the same
alphabetical filename read order that decides an `effect` fight, and `bc_` sorted
before `combat_`.

### Family 3 is shipped but unmeasured

- `BC: moment decisive` at its shipped line **0**. `BC: wound` **0**.

The single `BC: moment decisive` in the log is at line 258 of a **previous
build** of `bc_ledger_effects.txt` — written without the `file:line` form on
purpose, because `validate` checks every citation in that shape against the
current file and this one deliberately points at a superseded one. The current
build logs it from inside
`bc_record_effective_tier_effect`, at a line that has moved since. So no decisive
moment occurred at all during this run and the wound was never reached. This is
not evidence against the wound; it is evidence that `decisive` needs
`var:bc_battle_moments >= 5`, i.e. a long battle, and none happened. Plan 6's
firing rate remains unknown.

### Closed by this run

- **`BC: floor admitted` fired 5 times.** It was 0 in the checkpoint run and
  recorded there as *inconclusive, not a failure*. The cooldown floor is now
  exercised.

## Confirmation run, 2026-08-15 (logs cleared first)

Both 2026-08-14 fixes retested on a clean log. 40 combat ends per side, 28
notable wins, 28 notable losses, 167 moments. **Error sweep clean — no `bc_`
group in `error.log` at all**, which also retires the `bc_battle_wounded` debt
for good.

### The opening works, end to end

```
1  bc_eve_effects.txt:72 (bc_eve_offer_effect):          BC: eve offered
1  bc_eve_events.txt:70  (bc_chronicles.0011:immediate): BC: eve popup 0011
```

Gate passed, event raised, event opened — and **the pop-up named the enemy
commander**, confirmed by eye. That closes the two things no static check could
reach: `scope:bc_eve_foe` survives the `trigger_event`, and
`bc_eve_facing_nemesis_trigger` picks the nemesis branch correctly. The move off
`on_combat_start` is done.

### The dead-knight toast failed again, and the single marker failed again

`BC: dead knights` **0** over 28 notable wins, after the `enemy_side` rework and
the `zz_` rename.

**The block had one marker, inside the innermost `?=` — the same trap that hid
the eve's failure for two runs.** A zero from it cannot say which of three
different failures happened, and they need three different fixes. The block now
carries a marker per step (`BC: dk reached enemy side`, `BC: dk found dead`,
`BC: dead knights`); the next run names the failing step instead of returning
another uninformative zero. The scope path itself is not in doubt — vanilla does
`enemy_side = { every_side_knight = { ... } }` at `combat_events.txt:850`.

**The lesson is now three runs old and should be treated as a rule: a marker
inside a `?=` or a nested `if` only proves the innermost step. Mark every step
whose failure would need a different fix.**

### The decisive rung was measured too high, and has been lowered

`BC: moment decisive` **0** again, so `BC: wound` was **0** for the
uninformative reason a second time. But this run had a clean log and gave the
number that explains it:

| | |
|---|---|
| moments recorded | 167 |
| combat ends | ~40 |
| **moments per battle** | **~4.2** |
| old decisive floor | `var:bc_battle_moments >= 5` |

**The floor sat above the mean battle length.** Across both runs — 874 moments —
`decisive` fired exactly once, ever. The rung was not rare, it was very nearly
unreachable, and since family 3's wound hangs off that arm alone it could never
be measured at all.

Lowered to `>= 4`, so the ladder is now minor 1-2, major 3, decisive 4+. **The
major band is one moment wide and that is the part most likely to need a second
look.** Re-measure before moving either number again.

## Tiered-marker run, 2026-08-15 (logs cleared, both fixes measured)

Third clean-log run. 44 combat ends, 36 notable wins, 36 notable losses. Battle
sizes 1/2/3 = 17/85/131. Moments: minor 187, major 45, decisive 1 = **233, or
5.3 per battle** — up from 4.2, so the mean moves between runs and any floor set
against it is soft.

### The opening is closed

`BC: eve offered` 2 → `BC: eve popup 0011` 2. Second clean run in a row with a
1:1 ratio. Nothing outstanding.

### The `zz_` filename premise is disproven

```
33  BC: dk reached enemy side
 0  BC: dk found dead
 0  BC: dead knights
```

Row one of the three-way table the block was carrying: **`enemy_side` steps
correctly and `combat_event.1001` has not killed anyone yet when we look.** The
per-step markers paid for themselves on their first run.

**Alphabetical filename order does not order the merged `events = { }` list.** It
decides which `effect` block wins when two files claim the same on_action, and
that is all. `zz_bc_on_actions.txt` sorts last among filenames and still ran
before AGOT's 1001. *No prefix can fix this — do not try another one.*

The read is now deferred a day into `bc_chronicles.0093`, raised from `.0091`
inside the same notability gate, which steps outside the dispatch entirely. The
one thing that cannot be settled statically is whether the combat side object
survives the day; `BC: dk deferred` (call site) paired with
`BC: dk deferred fired` (event) answers it. First counting while the second is
absent means re-hang the read on the commander character instead of the side.

### The decisive floor was the wrong lever

`BC: moment decisive` **1**, and the logged line was checked against that run's
build and matched the `debug_log` inside `bc_record_effective_tier_effect`, so it
is a genuine clear of the new `>= 4` floor rather than a stale hit. The number
that line had then is not recorded here on purpose: it would be a claim about a
build this file can no longer point at. But the interesting number is upstream:

`BC: fired bc_flank_collapses` **10**, and both `TIER = decisive` call sites pass
identical arguments, so they share one arg-hash — which totals 10. So
`bc_chronicles.0001.c` was chosen **zero** times and every decisive *request* in
the run came from the flank-collapse phase event.

| where those 10 landed | count | means |
|---|---|---|
| `:311` minor | 7 | ledger held 1-2 moments at call time |
| `:307` major | 2 | ledger held exactly 3 |
| `:285` decisive | 1 | ledger held 4+ |

`5 → 4` was directionally right (this run scores 0 at `>= 5`), but the dominant
constraint is not the floor: **only 10 of 233 moments ever ask for `decisive`,
and 7 of those ask too early.** `bc_flank_collapses` fires near the start of a
battle. Leave the floor at 4 and re-measure before touching it again.

### The wound's zero was starvation, not a bug

`bc_wound_effect` had exactly one call site — the last line of the decisive arm.
Decisive resolved once, so **the wound had one opportunity in the entire run and
missed it.** Adding markers to it would still have produced a one-sample log.

It is now called from the **major arm as well**, which resolved 45 times on the
same run. Its own `var:bc_battle_wounded` guard still caps it at one wound per
battle, so this widens the sample without widening the outcome. A
`BC: wound gates passed` marker now splits the five-row outer limit from the
nested `var:bc_battle_size >= 3` read, which are the two candidates with
different fixes.
