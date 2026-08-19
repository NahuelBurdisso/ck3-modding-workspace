# Battle Chronicles - development history

Verbatim from the CK3 workspace memory file, where this ran to 345 lines - two
thirds of that file - and had gone stale at the top (it still described the mod
as having 10 combat phase events; it has 444). Kept whole because it carries
CK3-general lessons mixed into the narrative. Current state lives in the memory
file `project_battle_chronicles.md`; measured runs live in `runs.md`.

- `mods/battle_chronicles` — the real mod: 10 combat phase events (7 commander, 3 knight),
  advantage-modifier momentum ladder, 2 game rules, 3 pop-ups, combat-end cleanup.
  Spec: `docs/specs/2026-08-12-battle-chronicles-design.md`.
  **Played 2026-08-12: 8/10 events fired.** Script values reading `side_strength` proven.
  Four bugs found and fixed: opinion `monthly_change` must be positive; `add_gold` rejects
  negatives; knight events unreachable (`knight_none` base 2000 vs their 40, plus
  `prowess <= 6` matches almost no knight — knights are selected for prowess); and every
  gameplay effect was nested inside `send_interface_toast` (moved out — correct move, but the
  reason given at the time, "player-conditional", was later disproven; see the traps above).
  Shieldbrother memory (`common/character_memory_types/`) added.
  **Enabled in the live playset 2026-08-12** (last entry, index 44 → 45 mods). Loads clean:
  `Mounted Data: D:/ck3/mods/battle_chronicles`, namespace `bc_chronicles` #4190000,
  4 events from `events/bc_events.txt`, zero `bc_` lines in `error.log`. `validate` 0/0.
  Combat phase events do NOT appear in the "Loaded [N] events" line — they live in
  `common/combat_phase_events/`, so 4 is the pop-up count, not a missing-event symptom.
  **Aftermath system shipped 2026-08-13** (plan `docs/plans/2026-08-13-battle-chronicles-aftermath.md`):
  `bc_chronicles.0091`/`.0092` grade each combat end, notable battles give surviving knights a
  40-year province memory, a 3-time winning commander with `martial >= 14` is named from 27 AGOT
  nicknames. Third game rule `bc_aftermath` (off/default/generous); all three rules default to
  their middle option.
  **Calibrated over 39 combat ends**: vanilla's thresholds were the wrong *shape* — `size>=20000`,
  `size>=30000` and `blood>=75` fired ZERO times while `odds>=1.5x` fired on 54% and carried the
  whole trigger. Now 10k/20k/50/2.0x, warscore kept at 25. Method that made this possible: ship
  temporary `bc_cal_*` ladder markers that fire on EVERY combat end regardless of the bar, plus a
  **control ladder** against plain constants so a dead row is distinguishable from a matched
  sample. Re-derive from git history, never guess.
  Also proven: `side_max_army_size` works on the LEFT of a comparison (no precedent anywhere);
  a `send_interface_toast` body DOES run for AI characters; `bc_aftermath_generous` works.
  **Two knights on one side DO each get their own memory of the same battle** (checked by eye,
  memories window = round button at `gui/window_character.gui:155-168`) — so the AGOT idiom
  `create_character_memory` + `random_memory { limit = { has_memory_type = X
  NOT = { has_variable = ... } } }` is genuinely iterator-safe, which the 24 `scope:new_memory`
  call sites in vanilla are not (all single-character, outside iterators).
  **MOD IS COMPLETE 2026-08-13**, all plan steps ticked. Nickname award observed under its real
  gate 2026-08-14 (5×).
  **Expansion plan 1 "The Spine" in progress** (`docs/plans/2026-08-13-battle-chronicles-expansion-plan-1-spine.md`,
  17 tasks). Tasks 1-15 done. Added: `common/scripted_effects/bc_ledger_effects.txt` (the ONE
  seam — `bc_battle_open_effect`, `bc_record_moment_effect`, tier ceiling, style write, scratch
  clear; all writes land on the side commander, never on a knight),
  `events/bc_aftermath_events.txt` (the `.0091`/`.0092` graders, moved out of `bc_events.txt`
  which is now pop-ups only), `events/bc_diag_events.txt` (TEMPORARY, removed in task 16).
  **DIAG answers, 137 combat ends:** commander traits 0/1/2/3+ = 153/110/3/1 (n=267);
  battle size per side 5k+ 46 / 3k 42 / 2k 31 / 1k 14 / <1k 4; terrain rough 58, forest 32,
  winter 20, open 19, jungle 8, desert 0, unmatched 0 (the `agot_is_*` ladder is exhaustive).
  **Seam proven working on the second run** (143 combat ends, 707 moments): minor 614,
  major 93, **decisive 0**, swings up 422 / down 285 — both totals equal 707. `decisive` is
  empty for PACING, not logic: moments are per-side-commander, mean ~2.5, and the only
  AI-reachable decisive site (`bc_flank_collapses`, 37 fires) needs 4 prior moments.
  Deliberately NOT retuned — that campaign lost every battle, so 2.5 may be a losing-side
  artefact. Scratch-leak check done statically, 31/31 call sites commander-scoped.
  Known residual leak: a commander killed/replaced mid-battle keeps his scratch forever,
  because the grader's `side_commander` then resolves to someone else.
  **PLAN 1 COMPLETE 2026-08-14**, 17/17 tasks, 107/108 checkboxes. Task 16 stripped the DIAG
  pass (`bc_diag_events.txt` → `bc_combat_start_events.txt`, hook kept); task 17 moved both
  ground triggers onto AGOT helpers and widened them to 9 terrains (`the_bog` = the Neck,
  139 provinces, which the old wetlands key never matched; `mountains` de-duplicated out of
  the favouring list). The one open checkbox is `BC: moment decisive`, left open on purpose.
  **PLAN 2 "Verbs and pacing" tasks 1-11 DONE 2026-08-14**
  (`docs/plans/2026-08-13-battle-chronicles-expansion-plan-2-verbs-and-pacing.md`); only task
  12, the runtime checkpoint, is left. Added: `common/modifiers/bc_battle_modifiers.txt`
  (family 2 — `bc_bloodied`, `bc_shieldwall`, `bc_spent_horse`, `bc_pursuit`; army_*/knight_*
  tags, so they show in the army stat breakdown, NOT the advantage breakdown),
  `bc_apply_verb_effect` (the ONE place the `(KIND, SWING)` → modifier mapping lives; no event
  ever names a modifier), a size gate so family 2 needs `bc_battle_size >= 2`,
  `bc_chronicle_ready_commander_trigger` + `bc_mark_chronicle_commander_effect` +
  `bc_chronicle_flag_days_value` (cooldown scaled 10/20/40 days by battle size, with a
  one-shot floor arm on `NOT = { exists = var:bc_battle_moments }`). The knight events keep
  the flat-15 shared variants **deliberately** — no `bc_` variable is ever written onto a
  knight, so the floor arm would be permanently true there and un-gate the mod's biggest
  event-spam surface. Loc 57 → 71 keys. Size boundary kept at 2000 (measured: 2k+3k = 73/137
  sides = 53%).
  **PLAN 3 "Reputation" tasks 1-9 DONE 2026-08-14**
  (`...expansion-plan-3-reputation.md`); only task 10, the runtime checkpoint, is left.
  Added `common/scripted_effects/bc_reputation_effects.txt`: two streak bookkeepers
  (style threshold 3, terrain threshold 2), two award ladders granting 12 EXISTING AGOT
  traits (no new art), and `bc_reputation_effect = { OUTCOME = win|lose }` — three FLAT
  `if` blocks sequenced by a `bc_award_taken` scratch marker rather than `else_if`, because
  every arm needs its own NESTED exists guard and an else_if arm cannot nest one. Both
  graders call it; the loser gained a `side_commander` block it never had, and `OUTCOME`
  closes only the nickname arm. Loc 71 → 85 keys. Q1 verdict: gate `number_of_commander_traits < 3`
  passes 99.6% (0/1/2/3+ = 153/110/3/1) → shipped as designed.
  Facts settled while doing it: **`reckless` and `cautious_leader` are the ONLY `opposites`
  pair among the twelve** — `has_trait` does not catch it, the engine silently refuses the
  `add_trait`, so those two arms `remove_trait` the opposite first; the six terrain traits
  have no `opposites` at all. The terrain bucket ladder is exhaustive over **all 23**
  `agot_is_*_terrain` helpers (5 desert / 5 open / 7 rough / 2 forest / 2 jungle / 2 winter),
  and `bc_terrain_last` stores the BUCKET not the terrain key, or hills→mountains would
  break a streak. Inside `scope:<province> = { }`, `root` is the COMBAT SIDE (neither a
  scripted effect nor `side_commander ?=` rebinds ROOT) — save the commander scope first.
  **PLAN 4 "The Man Across the Field" tasks 1-10 DONE 2026-08-14**
  (`...expansion-plan-4-rivalry.md`); only task 11, the runtime checkpoint, is left.
  Added `common/scripted_effects/bc_rivalry_effects.txt` (rung ladder → escalation →
  decrement → clear → entry point → toast), `bc_rivalry_step_value` in the script values,
  a 4th game rule `bc_rivalry` (off/rival/nemesis, default rival), `bc_facing_nemesis_trigger`,
  a ×1.5 `chance` modifier on all 7 commander phase events, and a dead-foe wipe at the end of
  `bc_battle_open_effect`. Loc 109 → 124 keys. Both graders call
  `bc_rivalry_effect = { OUTCOME = win|lose }` after B and before `bc_clear_scratch_effect`.
  Facts settled: **`set_relation_X = var:Y` / `remove_relation_X = var:Y` have ZERO shipped
  uses** anywhere in vanilla+AGOT (only `has_relation_X = var:Y` ships), so every relation
  effect saves `var:bc_nemesis` into `scope:bc_rivalry_foe` first — the design doc said no
  save was needed and is wrong. **`nemesis` carries `relation_aliases = { rival }`**
  (`00_scripted_relations.txt:81`), so `has_relation_rival` is TRUE for a nemesis and the
  removal ladder must test nemesis FIRST. `rival`/`nemesis` carry `corresponding`, `grudge`
  does not, so only the top two rungs are mutual. Escalation needs no teardown — the higher
  rung's `opposites` removes the lower one. The floor guard must read
  `<= bc_rivalry_step_value`, never a constant (`<= 2` erases a rival after one win, `<= 1`
  jams the counter at −1 after a wipe win). `bc_nemesis`/`bc_nemesis_losses` are LEDGER
  variables — `bc_clear_scratch_effect` must never learn about them.
  **All 5 script `.txt` in this mod carry a UTF-8 BOM** (plan 4 claimed otherwise);
  `bc_battle_open_effect` lives in `bc_ledger_effects.txt:52`, not `bc_scripted_effects.txt`.
  Next: plans 5-6.
  **CHECKPOINT RUN 2026-08-14 — all three deferred checkpoints (plan 2 task 12, plan 3
  task 10, plan 4 task 11) run in ONE debug session; committed `67cd8b8` (mod README)
  and `7db8adb` (plans + spec).** Error sweep CLEAN: the only `bc_` group in `error.log`
  is the known `bc_battle_wounded` ×2 debt, and **zero missing-variable reads** for any
  plan 2/3/4 variable — the nested-guard discipline holds at runtime. Counts: all four
  `BC: verb` values fired; style award 1 / terrain award 8; `BC: nemesis new` 32 +
  escalate 6 + held 1 = exactly the 37 `BC: lose notable`, so nothing was swallowed by
  the entry guards; **`rung rival` 12 > `escalate` 6 proves `scope:wipe` resolves inside
  `bc_rivalry_step_value`**. `BC: moment decisive` finally fired (n=1) — plan 1's last
  done-when, met; do NOT retune the ladder on n=1. Not fired, for ordinary reasons, not
  defects: `BC: floor admitted` (plan 2 says *inconclusive, not a failure*, when
  `chronicle mark commander` is present — it fired 139×; retry = two battles back to
  back with the same commander; **CLOSED by the 2026-08-14 sweep run, 5 hits**) and the
  whole nemesis DESCENT path (`decrement`,
  `cleared`, `wipe`) since nobody beat their nemesis.
  **STILL OPEN, needs a human at a character screen:** whether the grudge actually
  LANDS. Markers only prove the effect was reached. If the marker fired and no relation
  exists, `scope:bc_rivalry_foe` is declined too and the target form must be re-derived
  from a shipped call site. Also unchecked: the rules screen rendering three readable
  `bc_rivalry` options.
  **PLAN 5 "Before and After" DONE 2026-08-14, task 11 included**
  (`...expansion-plan-5-before-and-after.md`). **Read the sweep-run entry at the end of this
  section before trusting the eve/dead-knight details below — the run killed both designs and
  they were rebuilt.** Added `bc_was_wipe_trigger` (the mod's ONE opinion
  about `scope:wipe`) and wired it into three places: a 6th notability row, `bc_style_step_value`
  (a wipe advances the style streak by 2), and `bc_rivalry_step_value`. Bar stayed at
  `amount >= 2` — never add a row and raise the bar in one change. Dead-knight toast
  (`any_side_knight = { is_alive = no }`) in both graders. **The eve**: new
  `common/scripted_effects/bc_eve_effects.txt` + rewritten `events/bc_combat_start_events.txt`
  (`bc_chronicles.0010` hidden `scope = combat`, `.0011` the pop-up), 90-day `bc_eve_cooldown`
  flag SEPARATE from the 60-day `bc_popup_cooldown` (sharing it would starve mid-battle
  chronicles — the eve always fires first), `bc_eve_facing_nemesis_trigger` for the desc
  read-back. `on_combat_start` now raises `.0010`; the `.0900` probe is retired. Loc 124 → 133.
  **The plan's tasks 6-9 were written against the dead `combat_attacker`/`combat_defender`
  links and were REWRITTEN on `every_combat_side` + `enemy_side` + `side_commander`**, shipped
  behind 3 markers (`BC: eve fired` / `eve side` / `eve commander`) so a failure names which
  link died. That route also removed the original two-pass ordering requirement — each pass
  computes its own foe. `bc_eve_foe` is saved INSIDE the `is_ai = no` gate, which is what makes
  it iteration-safe: at most one of two opposing commanders is human.
  **PLAN 6 "Family 3, the flesh" tasks 1-5 DONE 2026-08-14** (`...expansion-plan-6-flesh.md`);
  task 6, the runtime run, was ATTEMPTED and came back inconclusive — still open. `bc_wound_effect` in `bc_ledger_effects.txt`, called
  from the DECISIVE ARM of `bc_record_effective_tier_effect` and nowhere else — **that
  placement is the gate**. Do NOT rewrite it against `var:bc_battle_tier`: that is a HIGH-WATER
  mark (`bc_write_style_effect` only writes upward), so a minor moment would wound a commander
  because a decisive one fired six moments earlier. The spec says to read it and the spec is
  wrong on that word. `change_trait_rank = { trait = wounded rank = 1 max = 1 }` — `rank` is a
  DELTA and `max` is what keeps "death never" structural; a mod-made `wounded_2` puts a man one
  vanilla wound from `wounded_3`, the doorway to every lethal path in `20_health_effects.txt`.
  Do not call `increase_wounds_no_death_effect` — it applies rank 3 outright to a
  `fragile_bones` character. **No duration, no timed removal, no recovery event**: vanilla's
  `wounded_recovery_pulse` (AGOT `health_on_actions.txt:369`, 4×/year off `yearly_health_pulse`)
  triggers on `has_trait = wounded`, so raw `change_trait_rank` inherits recovery free and
  anything written here would race it. `wounded_1` carries **`flag = no_message`** (AGOT
  `00_traits.txt:6329`) AND `disables_combat_leadership` — hence a mandatory toast; without it a
  commander silently stops being able to lead armies. `SWING` threaded through the ladder
  (3 `SWING = $SWING$` lines in the file now); the seam's 19-calls/18-SWINGs is unchanged and
  is stable across the whole expansion. 5th game rule `bc_wounds` (off/default, defaults ON,
  2 options not 3). Loc 133 → 141. **The `bc_battle_wounded` ×2 load-time debt is now paid** —
  plan 6 is the plan that writes the variable.
  **STATIC WORK ON THE WHOLE EXPANSION IS COMPLETE.**
- **SWEEP RUN 2026-08-14 (plan 5 task 11 + plan 6 task 6 batched). Two failures, both fixed;
  one question still unanswered.** Whole log: 5,623 `BC:` hits, 96 markers, 169 combat ends
  per side, 137 notable wins + 137 notable losses.
  - **The eve was dead** (68/136/0 — see the `on_combat_start` entry above). Fixed by moving
    it into the battle: `bc_eve_offer_effect` is now called from the END of
    `bc_battle_open_effect`, which already runs on the side commander and already holds
    `var:bc_battle_foe` and `var:bc_battle_size`. Once-per-battle via
    `NOT = { exists = var:bc_battle_moments }` — free, because `bc_record_moment_effect` (the
    only writer) runs immediately AFTER it at every call site. `bc_chronicles.0010` deleted,
    `bc_combat_start_events.txt` → `bc_eve_events.txt`, `on_combat_start` left unclaimed,
    4 loc keys reworded from dawn imagery to "the lines close".
  - **The dead-knight toast watched the wrong side** (0 over 274 notable runs — see the
    `combat_event.1001` entry above). Fixed: the `.0092` copy deleted, `.0091` reaches across
    to `enemy_side` and toasts the LOSER's commander, and the on_action file renamed
    `zz_bc_on_actions.txt` so it dispatches after `combat_event.1001`.
  - **Family 3 remains UNMEASURED.** `BC: moment decisive` fired 0× at its shipped line, so
    `BC: wound` was 0 for the uninformative reason. `decisive` needs
    `var:bc_battle_moments >= 5` — a long battle — and none occurred.
  - **Two process traps from this run.** (1) The logs were NOT cleared first, so every count
    spans several sessions; fine for ratios, fatal for absolute counts. (2) The one
    `BC: moment decisive` present was from a PREVIOUS BUILD — identifiable only because
    `probe` prints `file:line` and it said `:258` while the current build logs at `:273`.
    **When a log spans builds, the `file:line` is the only thing that says which build wrote
    a marker.**
- **CONFIRMATION RUN 2026-08-15 (logs cleared first; 40 combat ends/side, 28 notable wins,
  167 moments). Error sweep CLEAN — no `bc_` group in `error.log` at all.**
  - **THE OPENING IS DONE.** `BC: eve offered` → `BC: eve popup 0011`, and the pop-up **named
    the enemy commander** (confirmed by eye). So `scope:bc_eve_foe` survives the
    `trigger_event` and `bc_eve_facing_nemesis_trigger` picks the nemesis branch. Nothing
    left open on the eve.
  - **Dead knights STILL 0** after the `enemy_side` + `zz_` rework. Cause unknown because the
    block had one marker in the innermost `?=` — see the marker rule above. Now split into
    `BC: dk reached enemy side` / `BC: dk found dead` / `BC: dead knights`; next run names the
    step. The scope path is NOT the suspect (vanilla does the same at `combat_events.txt:850`).
  - **THE DECISIVE RUNG WAS MEASURED TOO HIGH AND IS NOW 4, NOT 5.** Battles average **~4.2
    moments** (167 over ~40 combat ends), so a floor of `var:bc_battle_moments >= 5` sat ABOVE
    the mean — `decisive` fired **once in 874 moments across two runs**. Not rare,
    near-unreachable, and family 3's wound hangs off that arm alone so it could never be
    measured. Ladder now minor 1-2 / major 3 / decisive 4+; **the major band is one moment
    wide and is the thing to re-measure first.** General lesson: **derive a threshold from a
    logged distribution, not from intuition** — this one was invented and was off by enough
    to make a whole feature dead.
  Outstanding: plan 6 task 6 (the wound, now reachable at `>= 4`), which step of the
  dead-knight block dies, and plan 4's 2 human-at-a-character-screen checks.
- **TIERED-MARKER RUN 2026-08-15 (clean log; 44 combat ends, 36 notable wins, 233 moments =
  5.3/battle, sizes 1/2/3 = 17/85/131).** Eve 2 → 2, closed.
  - **`events = { }` MERGE ORDER IS NOT ALPHABETICAL BY FILENAME. THIS CORRECTS AN EARLIER
    ENTRY.** Filename order decides which `effect` **block** wins when two files claim the
    same on_action — it does NOT order the merged `events` list. `zz_bc_on_actions.txt`
    sorted last and still dispatched **before** AGOT's `combat_event.1001`. Measured:
    `BC: dk reached enemy side` 33, `BC: dk found dead` 0. **No prefix can win a dispatch
    race.** The general fix is to step outside the dispatch — `trigger_event = { days = 1 }`
    into a follow-up event, since every event on the hook has run by the next tick. Open
    risk: a `combat_side` is transient and may not survive the day, so pair a marker at the
    call site with one inside the deferred event.
  - **A DEAD MARKER CAN MEAN THE RUNG ABOVE IT IS STARVING IT — CHECK CALL-SITE COUNTS
    BEFORE TOUCHING THE GATE.** `BC: wound` read 0 for three runs. The gates were fine:
    `bc_wound_effect` had **one** call site, the last line of the decisive arm, and decisive
    resolved **once** in 44 battles — one opportunity in a 500k-line log. Lowering the floor
    5 → 4 addressed the wrong constraint.
  - **HOW TO FIND THAT: count the REQUESTS, not just the outcomes.** `BC: fired
    bc_flank_collapses` 10, and both `TIER = decisive` sites pass identical args so they
    share one **arg-hash**, which also totalled 10 → the other site was never used. Of the
    10: 7 demoted to minor, 2 to major, 1 resolved. So only 10 of 233 moments ever ask for
    the top rung and 7 ask too early. **`probe` prints the arg-hash `[args#N]` per call —
    it partitions a scripted effect's hits by call site, which is how you tell "gate too
    tight" from "nobody calls it".**
  - Fix: wound now also called from the major arm (45 hits/run); its per-battle guard still
    caps the outcome. Added `BC: wound gates passed` between the outer limit and the nested
    size read. Floor stays at 4.
- **SESSION HANDOFF LIVES AT `docs/2026-08-15-battle-chronicles-handoff.md`** (in the `D:/ck3`
  repo). Working-systems inventory with measured rates, the engine facts + process rules that
  cost four game runs, and the remaining work split into sweepable / needs-a-human /
  waiting-on-the-world. **Read it first when resuming Battle Chronicles.** Its `## 0. UPDATE`
  section at the top records that Plan A is built and that the next thing the project needs is
  a game run, not more code.
- **DEPTH WORK: PLAN A IS BUILT AND SHIPPED (2026-08-15). PLAN B IS NOT.** Spec
  `docs/specs/2026-08-15-battle-chronicles-depth-design.md`.
  - **Plan A** (`docs/plans/2026-08-15-battle-chronicles-depth-plan-a-context.md`, 11 tasks) —
    **DONE**, mod commits `40f012c`..`27314a4`, `validate --strict battle_chronicles` at the
    0-errors/2-warnings baseline. Shipped: 3 new `validate` checks (custom-loc arms resolve,
    `bc_` `Custom()` calls resolve, ground partition stays complete), 6 `bc_ground_is_*_trigger`
    extracted to `bc_ground_triggers.txt`, `bc_write_ground_effect` + `bc_write_bond_effect`,
    the `bc_ground_held` family-2 modifier, a one-fragment spike on The Banner Falls, and the
    eve widened (names the foe + the ground, option d offers to use it). Needed no game run.
  - **Plan B** (`...-plan-b-prose.md`, 14 tasks) — **NOT STARTED.** 22 customizable-localization
    definitions supplying 110 fragment keys (core 30 / ground 70 / bond 6 / scale 4) so every
    moment toast assembles as `core + ground + bond + scale`. Task 1 is a human gate: confirm
    Plan A's spike renders on screen. **That gate is now narrow, not open** — vanilla proves the
    mechanism works: `common/court_positions/tasks/00_court_poet_tasks.txt:94-98` sends a
    `send_interface_toast` whose `desc = court_poet_poetry_desc`, and that key at
    `localization/english/court_positions_2_l_english.yml:150` is
    `"[court_poet_from_task.Custom('GeneratePoem_Outro_Rhyming')]"` — the spike's exact shape.
    So a blank clause in the Banner Falls toast means the **anchor** or the **variable**, not
    `Custom()`-in-a-toast.
  - Bands: `desert`/`open`/`rough`/`forest`/`jungle`/`winter`. Bonds: `nemesis`/`kin`/
    `countryman`/`heathen`/`stranger`. **`bc_battle_ground` and `bc_battle_bond` are flags but
    `bc_battle_size` is a NUMBER (3/2/1)** — a `flag:` compare against size is a silent no-match.
  - **The six bands are an exhaustive PROSE partition of the 23 AGOT terrain helpers, not a
    tactical one.** Membership is mixed on purpose: `desert` holds `desert_mountains` and
    `canyon`, `rough` holds `wetlands` and `bog`. Any gate written on a band is therefore
    band-accurate and terrain-approximate. Do not "fix" that by splitting a band (it changes the
    flag `bc_terrain_bucket_effect` writes and desyncs the reputation streak from the prose) nor
    by adding a bespoke terrain trigger elsewhere (`validate.py`'s partition check reads ONLY
    `bc_ground_triggers.txt`, so a second ladder drifts from AGOT uncaught).
  - **Saved-scope lifetime past the raising execution is UNVERIFIED** — `api saved_scopes`
    returns "not in the 1.19.0.6 script_docs dump". Every scope read in the eve is
    `exists`-guarded, so both readings are safe. Do not spend a session closing a hypothetical
    cross-battle scope leak until a run shows one.
  - **Marker denominator for the ground/bond/creed debug lines is the ten `BC: fired bc_*`
    markers, NOT the moment count.** Bands are written once per phase-event fire; moments are
    recorded once per seam call, and 8 of the 18 seam sites are pop-up options — so the two
    differ in both directions.
  - **DUMP EVERY GATE BEFORE OPENING A NEW CONTENT AXIS.** The mod is 290 templates across
    two files as of batch 143 (2026-08-18); reading headers is not enough and "the mod has never asked X" is a claim that
    must be checked, not asserted. In batch 72 it was wrong: `bc_facing_his_own_house_trigger`
    duplicated the shipped `bc_foe_is_house_trigger`, and the new knight template was a strict
    subset of `bc_knight_the_other_branch` (ready + house gate, no side row). Reverted. Run from
    the mod root, and read the whole output:
    ```
    python - <<'PY'
    import re
    for f in ['common/combat_phase_events/bc_commander_phase_events.txt',
              'common/combat_phase_events/bc_knight_phase_events.txt']:
        s=open(f,encoding='utf-8-sig').read(); print('=====',f)
        for m in re.finditer(r'\n(bc_\w+) = \{\n\ttype = \w+\n\n?\t(?:#[^\n]*\n\t)*is_valid = \{\n(.*?)\n\t\}\n', s, re.S):
            rows=[l.strip() for l in m.group(2).split('\n') if l.strip() and not l.strip().startswith('#')]
            rows=[r for r in rows if r not in ('is_alive = yes','bc_chronicle_ready_trigger = yes','bc_chronicle_ready_commander_trigger = yes')]
            print(m.group(1),'|',' ; '.join(rows))
    PY
    ```
    Two rules it enforces: a new gate may not be a strict SUBSET of a shipped one (the shipped
    one already covers every case), and a new template may not reuse another's ARGUMENT even
    with a different gate. Templates with no side row are the dangerous ones — everything with
    the same first row is a subset of them.
  - **CONTENT-BATCH LOOP (proven over batches ~60–100, one commit each).** Pick an axis by
    censusing engine surfaces the mod has never read (`grep -rho <keyword> --include=*.txt
    common/ | wc -l`, expect 0) and confirm the keyword IS in the dump (`ck3.py api --kind
    triggers --partial X`) — never spend the 0-error baseline on an undocumented keyword.
    Then: write `_trigNN.tmp` / `_cmdNN.tmp` / `_knNN.tmp` / `_locNN.tmp` with the Write tool,
    append them with a `_appNN.py` that strips BOM, converts CRLF→LF and opens dst `'ab'`
    (expect `bom True crlf 0` per file); `validate --strict` back to 0 errors / 2 warnings;
    `grep -c <key>_toast_desc` = 1 for both loc keys (bare `_toast` returns 2 — it is a prefix);
    re-run the census `grep -rho 'KIND = [a-z]* SWING = [a-z]*' --include=*.txt . | sort |
    uniq -c`; update the three number blocks in `bc_ledger_effects.txt` and the six count
    sentences in `README.md` via a throwaway `_bNN.py`/`_rNN.py` using an
    `assert s.count(old)==1` helper. Two templates per batch, one per pool, and the two gates
    are made disjoint by an explicit `NOT` naming the other. **Never pass mod prose through
    `python -c` from bash** — backticks; always write the script to a temp `.py` first.
    Files are UTF-8 **with** BOM except `README.md`, which has none.
  - **AGOT's own `common/scripted_relations/` is the richest untouched axis source** (batches
    105–106). Keys there: `agot_squire`/`agot_knight`, `bodyguard`/`bodyguard_target`,
    `agot_parent_in_law`/`agot_child_in_law`, `agot_dragon`, `unfruitful_marriage`,
    `kicked_from_marriage_bed`, `small_councillor`, `agot_personal_coa_slave`. **Always check the
    `corresponding =` pair AND grep for the `set_relation_*` call site** — the direction is
    counter-intuitive in both cases so far: the *squire* takes `set_relation_agot_knight`, and the
    *guarded person* takes `set_relation_bodyguard`, so the sworn sword holds `bodyguard_target`.
    Also verify AGOT actually sets the relation somewhere, or the gate is dead content.
- **A `send_interface_toast` DOES take a `desc = { ... }` block with `triggered_desc` arms,
  and `first_valid` inside its `title`.** Vanilla: `events/dlc/ach/ach_coronation_events.txt:3316-3324`
  and `common/scripted_effects/01_ep1_court_event_effects.txt:14-22`. So "toast prose must be a
  single fixed key unless you use customizable localization" is FALSE — a toast can branch inline
  exactly like an event desc. This is the fallback if `Custom()` turns out not to render in a toast.
- **Vanilla's exact `random_valid` precedent is `GetSmallFood`, `common/customizable_localization/00_appropriate_generic_words.txt:1`**
  — `type = character`, `random_valid = yes`, every arm trigger-less. `00_servants.txt:3` also has
  `random_valid = yes` but all its arms carry triggers, so it is the wrong citation for the
  pick-randomly-among-equals shape.
- **A customizable-localization arm-shape check must be written against MULTI-LINE arms.**
  The natural regex `text = \{(.*?)\n\t\}` cannot see a one-line `text = { localization_key = X }`,
  so a `random_valid` class of collapsed arms reports `arms 0` — and a check written as
  `unguarded == list(range(len(arms)))` scores `[] == []` as **passing**. Caught in review
  2026-08-15 before it shipped. Either mandate three-line arms or match both shapes; and note
  that a *partial* collapse (`arms 2` of 3) passes every whole-file check too.
