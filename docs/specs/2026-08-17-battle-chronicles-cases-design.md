# Battle Chronicles — more cases: design

Written 2026-08-17, during a live game run whose sweep is not yet in. Scope is
deliberately confined to work that **needs no runtime answer**: new combat phase
events, new gates, new prose. Plan B tasks 5-14 stay blocked; nothing here
touches them.

## 1. The problem, in one number

Ten moment templates produced **233 firings in 44 battles** (2026-08-15
tiered-marker run), and the run in progress today has already fired
`bc_banner_falls` **31 times**. A player who fights a war sees the same ten
sentences repeatedly, and the handoff names this as the single biggest lever for
variety.

## 2. Why adding templates is safe — and where it is not

**The rate limiter is the cooldown, not the weights.** `bc_commander_phase_events.txt`'s
header states it and the code agrees: `bc_chronicle_ready_commander_trigger`
fails while `bc_chronicle_recent` is live, so a commander who has just taken a
moment makes **every** Battle Chronicles event invalid for the next
`bc_chronicle_flag_days_value` days (10/20/40 by battle size). A blocked roll is
not a Battle Chronicles roll at all — it goes to vanilla's `commander_none`.

So the honest statement is two-part, and only the first half is a pure win:

- **Variety rises with no rate cost** wherever a new template fires in a slot an
  old one already owned.
- **Rate rises modestly** in the situations where *no* BC event is currently
  valid. Today an even battle, on open ground, neither outnumbered nor
  outnumbering, with a commander at `prowess < 8`, matches **nothing** — there
  are seven commander templates and six of them carry a situational gate. Those
  battles are silent now and will not be after this work.

That second half is a deliberate accepted cost, not an oversight. It is also
self-limiting: the cooldown still caps a single commander at one moment per
10-40 days of battle.

**What is genuinely at risk is the pool share.** `chance` is a weight against
every other *valid* event (the engine's own `_combat_phase_events.info`), and the
pool includes vanilla `commander_none` at `base = 1000` plus AGOT's casualty
events. Seven templates at bases 40-100 total ~400. Adding thirteen at the same
bases would total ~1180 and roughly triple the share. **Therefore every new
commander template ships at `base = 30` unless its gate is narrow enough to
justify more**, which holds the added weight near +400 rather than +780, and
keeps the existing seven — which are calibrated — dominant among BC events.

## 3. The gate rules every new template obeys

These are not new rules; they are the existing ones restated so the plan can
cite them once.

1. **A gate is evaluated on every commander in the world on every roll.** Only
   ROOT character triggers and `scope:combat_side` links are safe. No bespoke
   scope walking.
2. **No `var:bc_*` read in `is_valid` or `chance`.** Every `bc_battle_*` scratch
   variable is written in the *effect*, and weights are evaluated before the
   effect, so the first roll of a battle sees nothing. The one exception is
   `bc_facing_nemesis_trigger`, which is built for exactly this and guards its
   own reads.
3. **Momentum and faltering do not stack.** A template granting momentum gates
   `NOT = { bc_has_momentum_trigger = yes }`; one granting faltering gates
   `NOT = { bc_is_faltering_trigger = yes }`. Ladders are tuned to a single
   live modifier and `bc_faltering_minor` / `bc_faltering_major` are different
   keys, so two at once runs off the end of the ladder.
4. **Ground is read through the band triggers, never `terrain =`.**
   `scope:combat_side.combat.location = { bc_ground_is_winter_trigger = yes }`.
   AGOT's road variants are distinct terrain types and a bare key silently
   misses about a quarter of the map.
5. **Every template ends with the standard three `chance` modifiers** —
   `bc_frequency_low` ×0.5, `bc_frequency_high` ×2, `bc_facing_nemesis_trigger`
   ×1.5 — so the game rules keep working and the grudge read-back stays uniform.
6. **Distinctness.** A new gate that is a strict subset of an existing one adds
   no cases; it only steals weight from a calibrated template. Every template
   below introduces at least one axis no shipped event reads.

## 4. The axes nothing reads today

| axis | how it is read | shipped readers |
|---|---|---|
| ground **band** (six) | `combat.location` + `bc_ground_is_*_trigger` | prose only — no *event* gates on a band |
| war length | `combat.combat_war` → `war_days` | none |
| total host size | `combat = { num_total_troops }` | notability, at combat end only |
| casualties so far | `percent_enemies_killed` | notability, at combat end only |
| the foe as a person | `enemy_side.side_commander` — kin, faith, culture | bond prose; `bc_facing_nemesis_trigger` for weights |
| the liege on the field | `side_primary_participant` | none |
| the commander's age | `age` | none |
| commander character | `has_trait` | none |

Every new template below is named by the axis it opens.

## 5. The templates

Thirteen: ten commander, three knight. Tier/kind/swing use the shipped
vocabulary — TIER `minor|major|decisive`, KIND
`bloodied|entrenched|wild|ordered|adapted|measured`, SWING `up|down`.

### Commander

**This table is the AS-SHIPPED record**, reconciled 2026-08-17 after commits
`7691114`, `1e18d67` and `f85a5d2`. Two commander keys were renamed during
implementation and one gate was changed; the notes column says which and why.

| key | axis opened | gate (beyond the ready trigger) | tier / kind / swing | effect | base |
|---|---|---|---|---|---|
| `bc_winter_bites` | winter band | winter ground, not faltering | minor / entrenched / down | faltering minor | 40 |
| `bc_dust_and_thirst` | desert band | desert ground, not faltering | minor / adapted / down | faltering minor | 40 |
| `bc_the_woods_hide_us` | forest band **as the weaker side** | forest ground, outnumbered, no momentum | minor / adapted / up | momentum minor | 30 |
| `bc_the_long_war` | war length | `war_days >= 730`, not faltering | minor / measured / down | faltering minor, stress 5 | 30 |
| `bc_too_wide_to_see` | total host size | `num_total_troops >= 15000`, **not faltering** | minor / wild / down | faltering minor | 30 |
| `bc_the_killing_is_general` | casualties in progress | `percent_enemies_killed >= 40`, no momentum | major / bloodied / up | momentum major | 30 |
| `bc_kin_across_the_line` | the foe as kin | enemy commander is close family | minor / measured / down | stress 15, no momentum | 50 |
| `bc_the_old_wolf` | age, upper | `age >= 55`, side winning, no momentum | minor / measured / up | momentum minor | 30 |
| `bc_the_green_boy` | age, lower | `age <= 21`, not faltering | minor / wild / down | faltering minor, stress 10 | 30 |
| `bc_his_lords_war` | the liege present | `side_primary_participant` is someone else, side winning, no momentum | minor / entrenched / up | momentum minor, prestige | 30 |

Three deviations from the draft above, all deliberate:

- **`bc_the_killing_is_general`** and **`bc_kin_across_the_line`** were drafted as
  `bc_the_field_is_a_slaughter` and `bc_kin_across_the_field`. Both spent the
  word **`field`**, which `bc_frag_bond_nemesis` and `bc_frag_bond_kin` already
  spend — and a bond fragment renders in the sentence *immediately after* every
  moment toast. Renaming was cheaper than bending the prose.
- **`bc_too_wide_to_see` gates `not faltering`, not `no momentum`.** It grants
  faltering, so rule 3 asks for the faltering gate; the draft named the wrong one.
- **`bc_his_lords_war` also requires the side to be winning.** Serving another
  man's war well is a momentum grant, and granting momentum to a side that is
  losing reads as a non-sequitur.

### Knight

Reconciled the same way. The whole knight block shipped at **`base = 80`**, not
at the commander batch's 30: vanilla `knight_none` is `base = 2000`, twice
`commander_none`, and the file header records that `base = 40` behind narrow
gates produced **zero** fires across an entire session. 80 is half the shipped
three's 150, which holds the mod's share of a knight roll roughly where it was.

| key | axis opened | gate | tier / kind / swing | effect |
|---|---|---|---|---|
| `bc_knight_unhorses_a_lord` | **the winning side** — every shipped knight case gated on losing | `prowess >= 12`, side winning | major / bloodied / up | prestige 150, liege opinion, momentum major |
| `bc_knight_takes_a_captive` | **outnumbering**, which no knight case read | `prowess >= 8`, side winning, outnumbering | minor / ordered / up | prestige 50, gold 25, momentum minor |
| `bc_knight_is_ridden_down` | **ground**, which no knight case read | side losing, **open band** | minor / bloodied / down | stress 10, faltering minor |

`bc_knight_is_ridden_down` gained the open-band row during implementation. The
draft's bare `side losing` was a strict **superset** of
`bc_knight_holds_the_breach`'s gate, so by rule 6 it would have added almost no
cases and only stolen weight from a calibrated event. The band narrows it to
horse country and is the case's only reason to exist.

**Momentum stacking, on the knight side, is guarded differently.** `is_valid` in
a knight event is rooted on the *knight*, and `bc_has_momentum_trigger` reads
`has_character_modifier` on its own root, so the gate there would test the wrong
man. All three grants above therefore sit behind an `if` evaluated *inside* the
`scope:combat_side.side_commander` scope. The three shipped knight events do not
carry this guard and can put a second live rung on a commander who already has
one — a real defect, recorded here, left for a run to confirm rather than folded
into a content batch.

**No deaths and no maiming.** The mod's standing rule. The wound family
(`bc_wound_effect`) remains the only lasting personal consequence and no
template here calls it.

## 6. Prose

Each template gets a title key and a desc key. **Every desc appends
`bc_bond_clause` and `bc_scale_clause`**, exactly as Plan B task 4 did to the
shipped ten — that is the safe half of the Plan B gate: a clause appended to a
desc that keeps its own literal sentence degrades to "no improvement" if
`Custom()` turns out not to compose, never to an empty toast. No template here
gets a per-moment `_ground` set; those are Plan B tasks 5-14 and stay blocked.

**Repetition is the thing being fixed, so the prose must not reintroduce it.**
The loc file already carries a shipped-phrase inventory (the `"the men"` /
`"again"` / `"out of"` list). New sentences are checked against it.

## 7. What this design does not do

- No new game rule. Five is enough and each one is baked into every save made
  with it.
- No new modifier. The four family-2 verbs and the six momentum/faltering keys
  cover every template here through the existing `(KIND, SWING)` table.
- No change to the notability trigger, the tier ladder, or any calibrated
  threshold. Those rest on measured distributions and this work adds no
  measurement.
- No new pop-up. Pop-ups cost a `bc_popup_cooldown` and the three shipped ones
  already compete with the eve.
