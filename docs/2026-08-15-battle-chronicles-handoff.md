# Battle Chronicles — session handoff, 2026-08-15

Written at the end of the run-sweep session so the next one starts with the map
rather than rebuilding it. The next session has two jobs:

1. **Add depth** to the systems that already work, and **a lot more cases and
   scenarios**.
2. **Finish what is left** — the short list in §3.

Do not start writing content before §2 is read. Three separate features have
already been built twice because a premise was assumed instead of measured.

---

## 0. Where things live

- **Mod:** `D:/ck3/mods/battle_chronicles` — *its own git repo*. `git status` run
  from `D:/ck3` will not show mod changes.
- **Docs:** `D:/ck3` repo — `docs/specs/`, `docs/plans/`, `docs/reference/`,
  `docs/api/`.
- **Mod README** (`mods/battle_chronicles/README.md`) is the real record: rules
  the mod lives by, a run log per session, and a "Not yet verified in game"
  list. It is long and it is worth reading in full before designing anything.

Tooling, all via `python tools/ck3.py <cmd>` from `D:/ck3`:

| command | note |
|---|---|
| `validate --strict battle_chronicles` | baseline is **0 errors, 2 warnings** — both `namespace also defined in` false positives. Anything else is new. |
| `deploy battle_chronicles` | writes the `.mod` into the CK3 user dir |
| `conflicts` | takes **no** mod argument; run bare and filter for the mod name |
| `probe '<marker>'` | reads `debug_log` output. See §2. |
| `api <key>` | the engine's own `script_docs` dump for the **loaded playset**. Ask this before searching anything. |
| `index -q` | refresh before `conflicts`, or the pass is meaningless |

---

## 1. What actually works, and is the surface to deepen

Everything below is measured, not assumed.

| system | shape | measured rate (44-battle run) |
|---|---|---|
| **10 combat-phase moments** | 7 commander, 3 knight | 233 moments, **5.3 per battle** |
| **Momentum ladder** | 3 tiers each way, prose-named modifiers on the commander | fires with the moments |
| **The tier ladder** | minor 1-2 moments, major 3, decisive 4+ | minor 187 / major 45 / decisive 1 |
| **The opening ("eve")** | pop-up before the lines close, 3 options, names the enemy commander if he is a nemesis | 2 offered, 2 opened, name confirmed by eye |
| **Aftermath grading** | `.0091` winner / `.0092` loser, symmetric notability | 36 notable wins, 36 notable losses |
| **Battle memories** | 40-year province memory to every surviving knight | fires with grading |
| **Notable-win counter + nickname** | 3 wins, `martial >= 14`, no nickname → named from 27 AGOT nicknames | path proven; real gate not yet hit |
| **Nemesis / grudge** | escalating rungs, set at combat end | `BC: nemesis new` 32, `rung grudge` 26 |
| **Wipe detection** | symmetric across both graders | 38/38 |
| **3 game rules** | frequency, swing, aftermath — all default to the middle option | render untested for rivalry |

**Where the depth obviously goes.** These are observations, not decisions — the
next session should brainstorm them properly rather than take this as a plan:

- **Moments are the content unit and there are only ten.** 233 firings drawn
  from 10 templates in 44 battles means heavy repetition. This is the single
  biggest lever for "more cases and scenarios".
- **Terrain, season, war type, culture, faith, relations and troop composition
  are all unread.** Every moment currently gates on ratio thresholds and little
  else, so a battle in a swamp in winter against a brother reads identically to
  a summer field battle against a stranger.
- **The eve has three options and one branch pair** (nemesis / stranger). It is
  the natural home for scenario variety, and it is now proven to work.
- **The tier ladder demotes but never promotes.** Only **2** call sites ever
  request `decisive`, both `{ TIER = decisive KIND = wild SWING = down }`, and
  one of them is a pop-up option that is rarely taken. If the top rung is meant
  to feel reachable, that is a content problem, not a threshold problem — see
  §2.4.
- **Outcomes are thin relative to inputs.** A battle produces momentum, a
  memory, a counter tick, sometimes a grudge or a nickname. Wounds are the only
  lasting personal consequence and they have never fired.

---

## 2. Read this before writing anything

These cost four game runs to learn. Each one is a rule now.

### 2.1 The marker rule

**A `debug_log` inside a `?=` or a nested `if` only proves the innermost step.**
A zero from it is indistinguishable from "the block never ran". Mark **every**
step whose failure would need a different fix, and write the decision table into
the source comment next to the markers.

This trap hid three separate features' failures — the eve for two runs, the
dead knights for two, the wound for three.

### 2.2 `probe` reads *every* `*.log` in the CK3 log dir

So a stale `debug.log` produces hits indistinguishable from this session's.

- **Clear the logs with the game closed** before any run that asks a question
  about *counts*. Windows holds `debug.log` open while `ck3.exe` runs.
- **Verify they are actually clear.** The user has twice said "logs cleared"
  when they were not — once the file was 53 MB and still contained markers from
  deleted files, once the game was still running with the previous build loaded.
  Check, every time, before sweeping. This is not distrust, it is that the
  failure is silent and expensive.
- **`probe` prints `file:line` per marker.** When a log spans builds, that is the
  *only* thing that says which build wrote a hit. A marker at a line the current
  source does not have is from a previous build.
- **`probe` also prints an arg-hash, `[args#N]`, per call.** It partitions a
  scripted effect's hits by call site. This is how you tell "the gate is too
  tight" from "nobody calls it" — see §2.4.

### 2.3 Engine facts, measured

- **No commander is assigned to a combat side at `on_combat_start`.** Measured
  68 fired / 136 sides / **0** commanders. There is no other pre-battle hook in
  the on_action dump. Anything needing a commander before the fighting must hang
  off the first phase event instead — which is what the eve now does.
- **Vanilla kills knights on `enemy_side` only**, inside `combat_event.1001`
  (AGOT `combat_events.txt:849`), raised from `on_combat_end_winner`. The dead of
  any battle are the **loser's**, and they are made dead on the **winner's**
  hook.
- **Alphabetical filename order in `common/on_action` settles `effect` block
  fights and nothing else.** It does **not** order the merged `events = { }`
  list. `zz_bc_on_actions.txt` sorts last and still dispatched before AGOT's
  1001. **No prefix can win a dispatch race.** To run after another mod's event
  on the same hook, step outside the dispatch: `trigger_event = { days = 1 }`
  into a follow-up event, since every event on the hook has run by the next tick.
- **`flag:$PARAM$ = flag:literal`, never bare `$PARAM$ = literal`.** The bare
  form substitutes to an unknown key, which is a **silent no-op that `validate`
  passes** — the gate simply never rejects anything.
- **`send_interface_toast` bodies do run for AI characters**, but state still
  goes in the `effect` block. See the README's rules list.
- **CK3 does not short-circuit and guarantees no evaluation order among
  siblings.** A `var:` comparison in a `limit` evaluates even when the variable
  is absent. Nest the read behind an `exists`, do not rely on ordering.
- **Every script `.txt` in this mod carries a UTF-8 BOM** (`ef bb bf`). The
  `Write` tool does not add one — add it with python if creating a new file.

### 2.4 Diagnose starvation before touching a gate

`BC: wound` read zero for three runs. The gates were fine. `bc_wound_effect` had
**one** call site, on an arm that resolved **once** in 44 battles.

**Count the requests, not just the outcomes.** `BC: fired bc_flank_collapses`
10; both `TIER = decisive` sites pass identical arguments so they share one
arg-hash, which also totalled 10 — proving the other site was never used. Of
those 10, seven demoted to minor because they arrived while the ledger still
held 1-2 moments.

So the `5 → 4` floor change addressed the wrong constraint. **When a marker
reads zero, check the population that reaches it before changing what it tests.**

### 2.5 Thresholds come from logged distributions

The decisive floor was invented at 5 and sat above the mean battle length, which
killed a whole feature. It is now 4, derived from a run. But the mean itself
moved between runs (4.2 → 5.3), so **any threshold set against it is soft and
must be re-measured with its call-site counts, never alone.**

---

## 3. What is left

### 3.1 Awaiting the next game run — code is in, unverified

Both shipped 2026-08-15 (mod commit `06e4021`). Nothing to write; just run and
sweep.

| markers | verdict |
|---|---|
| `BC: dk deferred` counts, `BC: dk deferred fired` absent | the `combat_side` object did not survive the day → re-hang the read on the commander character |
| both count, `BC: dk found dead` still 0 | a day is not enough, or knights are not dying at all |
| `BC: wound gates passed` counts, `BC: wound` 0 | the `var:bc_battle_size >= 3` read is the rejector |
| both 0 while `BC: moment major` counts | the five-row outer limit is — most likely `bc_wounds_off` or a pre-existing `wounded` trait |

Also newly live and unproven: **the `flag:$SWING$ = flag:down` row**. It was
inert while the wound hung off the decisive arm alone (both decisive sites pass
`down`). The major arm feeds it wins too — roughly a third of what reaches
`bc_wound_effect` is now `swing up` — so that row is the only thing standing
between the mod and wounding a man for winning. Nothing has proven it rejects.

### 3.2 Needs a human at a screen — cannot be swept

- **The nemesis relation, on a character screen.** `bc_rivalry_set_relation_effect`
  is proven to *run*; nothing proves the relation *landed*. Plan 4 targets
  `scope:bc_rivalry_foe` saved from `var:bc_nemesis`, on the argument that
  `set_relation_X = var:Y` has **zero** uses in vanilla or AGOT while
  `has_relation_X = var:Y` ships. **That argument is untested.** Open a commander
  who took a `BC: nemesis new` and look for a grudge against the right man with
  the reason *"beat him on the field"*. Marker fired + no relation = the target
  form is wrong and must be re-derived.
- **The rivalry game rule rendering** — *Battle Chronicles: Rivalry* with three
  readable options on the rules screen.
- **The shieldbrother memory**, and that `[shieldbrother.GetFullName]` resolves.
- **The 2026-08-14 loc fixes**: `[bc_named_commander.GetNicknameNoTooltip]`
  inside the award toast *including the liege branch*, where the scope has moved;
  and the 26 `nick_agot_*_desc` keys on hover, with no `Duplicate localization
  key` in `error.log`.

### 3.3 Waiting on the world, not on us

- **The nickname award under its real gate.** The path is proven; no commander
  has yet banked three notable wins with `martial >= 14` and no nickname
  unaided. `BC: nickname awarded` is a permanent marker, so `probe 'BC:'` will
  report it the first time it happens.

### 3.4 Open design questions

- **The major band is one moment wide** (major = exactly 3). Most likely thing
  to need a second look.
- **The decisive rung's real bottleneck is call-site rarity**, not the floor.
  Whether to add `TIER = decisive` sites is a *content* decision and belongs in
  the depth work, not in a threshold tweak.

---

## 4. Plans, and their state

`docs/plans/2026-08-13-battle-chronicles-expansion-plan-{1..6}-*.md`, plus
`-aftermath.md`. Design specs in `docs/specs/`.

- **Plan 5** task 11 — closed except for §3.1. Carries two RUN CORRECTIONs under
  steps 4 and 5; the step-5 pass-shape table has been retired **twice** and the
  corrections beneath it are what is true.
- **Plan 6** task 6 — **open**. Now records why the wound's zero was starvation
  and what the next run must show per candidate.
- **Plan 4** — the two human checks in §3.2 are its unreported remainder.

**Read the RUN RESULT / RUN CORRECTION blocks, not the original step text.** The
plans were written before the engine facts in §2.3 were known, and several steps
instruct things now known to be wrong. The correction blocks say so explicitly
wherever that is the case.

---

## 5. Working agreements

- **Caveman mode is on** (full). Terse output, articles and filler dropped;
  technical substance, code blocks and error strings unchanged. Commits, PRs and
  docs are written normally. Drop it for safety warnings and multi-step
  sequences.
- **Prefer static verification; avoid asking for game relaunches.** The user
  suspended this for the diagnostic runs and it has since been useful, but the
  default stands — a run costs the user real time.
- **Every brainstorming question carries an explicit recommendation**, first in
  the list, marked `(Recommended)`.
- **Confirm before risky or shared-state actions.** Local edits and commits in
  these two repos have been fine to make directly.
