# Battle Chronicles — depth and scenarios, design

Written 2026-08-15, after the tiered-marker run and the session handoff
(`docs/2026-08-15-battle-chronicles-handoff.md`). It answers the handoff's job 1:
**add depth to the systems that already work, and a lot more cases and
scenarios.**

It does not touch job 2. Everything on the handoff's §3.1/§3.2 list needs a game
run or a human at a character screen, and this design is deliberately built to
need neither.

---

## 0. The problem, measured

The 2026-08-15 tiered-marker run: 44 combat ends, 233 moments, **5.3 per
battle**, drawn from **ten** phase-event templates each carrying **exactly one**
title and one description. A player who fights forty battles reads the same ten
paragraphs twenty-three times.

Every situational input except battle ratio is unread. A battle in a bog in
winter against a brother reads identically to a summer field battle against a
stranger.

## 1. Decisions taken before design

| question | answer |
|---|---|
| where does depth land | prose, the eve, and outcomes. New *moments* are designed but deferred — see §6 |
| are new *outcomes* in scope | yes, non-lethal rule intact |
| what happens to measured pacing | **hold it.** Variety comes from branching inside existing keys, not from new keys competing for rolls |
| which inputs may be read | terrain, foe identity, size/odds, commander-vs-foe culture and faith, relation to the foe |
| which inputs are excluded | **war type** (`combat_war` is documented but has never run here — unverified scope risk) and **season** and **troop composition** (no readable path found) |
| mechanism | script decides *which* situation obtains and writes a flag; loc only *reads* flags |

The pacing answer is the load-bearing one. Handoff §2.4 established that the
tier ladder's real constraint is **call-site distribution**, not template count —
only 10 of 233 moments ever request `decisive` and 7 of those request it too
early. Adding templates spreads that distribution thinner, not richer.

The mechanism answer is the second load-bearing one, and §2 is where it is
argued. It applies uniformly: **no localization arm ever classifies anything.**

## 2. Section 1 — how a moment learns its context

### The two rules

**1. No new saved scope carries meaning.** `bc_eve_effects.txt:41-45` and
`bc_scripted_triggers.txt:294-302` record the hazard: a saved scope cannot be
unsaved, so a scope saved in one battle can name a previous battle's commander.
Meaning goes in **scratch variables**, which `bc_clear_scratch_effect`
(`bc_ledger_effects.txt:507-514`) already strips at combat end.

The one exception is the eve, which renders after its own state may be gone and
therefore needs durability — §5 handles it by the *existing* pattern, freshness
from the variable and durability from the scope, not by inventing a second one.

**2. Classification happens in script, never in a loc arm.** Reasons, and the
third is the one that matters:

1. a 23-helper terrain ladder is written once instead of being retyped per arm
2. the flavour system then needs exactly one custom-loc `type` and no province
   scope
3. **a custom-loc arm cannot be instrumented.** There is no `debug_log` in
   localization. Putting the ladder in script is the only way any of these
   distributions is ever measurable — and the terrain census (DIAG Q5) only ever
   measured the *world*, never what the *mod chose*.

### Six band triggers, one source of truth

New scripted triggers, called **on a province**, collapsing AGOT's 23 terrain
helpers into six bands:

```
bc_ground_is_rough_trigger      bc_ground_is_bog_trigger
bc_ground_is_forest_trigger     bc_ground_is_mountain_trigger
bc_ground_is_open_trigger       bc_ground_is_frozen_trigger
```

They are triggers rather than an inline ladder because **two callers need the
same classification**: the script ladder below, and the eve's ground paragraph
(§5), which reads a saved province scope at render time and so cannot use the
variable. One definition, two readers.

They never test `terrain = X` bare. AGOT defines road variants as distinct
terrain types; bare keys silently missed 424 and 51 provinces from the first
live run onward (`bc_scripted_triggers.txt:36-43`).

### The change to `bc_battle_open_effect`

That effect already runs on the side commander at **all ten** phase-event call
sites, once each, at the top of the `effect` block, and already writes
`bc_battle_foe` and `bc_battle_size`. It gains, in this order:

1. `save_scope_as = bc_chronicle_subject` on the side commander — the one loc
   anchor common to all ten toasts, and the unambiguous left-hand side for the
   bond comparisons below.
2. `bc_write_ground_effect = yes`, writing `var:bc_battle_ground` as a flag
   (`rough` / `forest` / `open` / `bog` / `mountain` / `frozen`) from an ordered
   if-ladder over the six band triggers, evaluated against
   `scope:combat_side.combat.location`. Each arm carries a `BC: ground <band>`
   marker.
3. `bc_write_bond_effect = yes`, writing `var:bc_battle_bond` as a flag from an
   ordered if-ladder, first match wins, each arm carrying a `BC: bond <band>`
   marker:

   | band | test |
   |---|---|
   | `nemesis` | `bc_facing_nemesis_trigger = yes` |
   | `kin` | `var:bc_battle_foe = { is_close_family_of = scope:bc_chronicle_subject }` |
   | `countryman` | `var:bc_battle_foe = { culture = scope:bc_chronicle_subject.culture }` |
   | `heathen` | `NOT = { var:bc_battle_foe = { faith = scope:bc_chronicle_subject.faith } }` |
   | `stranger` | fallback |

   Every row that *reads* `var:bc_battle_foe` is nested behind
   `exists = var:bc_battle_foe`, never a sibling of it: CK3 does not
   short-circuit and guarantees no evaluation order among siblings (handoff
   §2.3).

**Ordering inside the effect is load-bearing.** All three writes go **above** the
`bc_eve_offer_effect` call, which `bc_ledger_effects.txt:154-158` documents is
raised last precisely so that everything it reads is already written. The bond
ladder must come after both the anchor save and the `bc_battle_foe` write, since
it reads both.

**All three writes are unconditional, not write-if-unset**, following the
doctrine at `bc_ledger_effects.txt:34-43`: scratch is cleared on
`side_commander`, so a commander replaced mid-combat is never cleared, and under
write-if-unset his stale values would freeze **permanently** rather than for one
battle.

`bc_clear_scratch_effect` gains `remove_variable = bc_battle_ground` and
`remove_variable = bc_battle_bond`. **Writers and removers must ship in the same
commit** — a remover without a writer produces
`Variable 'X' is used but is never set` twice per boot, the exact debt the
2026-08-15 run just finished retiring.

### Why staleness is safe for the anchor

`scope:bc_chronicle_subject` can go stale between battles; nothing can unsave a
scope. But every arm it feeds tests a **scratch variable**, and scratch is wiped
at combat end. A stale subject therefore resolves to an arm's **fallback**, never
to wrong flavour. This inverts the `bc_open_foe` hazard rather than repeating it.

## 3. Section 2 — the prose fragments

New file `common/customizable_localization/bc_flavour.txt`. Additive; the
directory is vanilla (`00_journey_focus_custom_loc.txt` is the shape) and no mod
in the playset ships a file of that name. The file needs a UTF-8 BOM like every
other script file in this mod (handoff §2.3).

**Note the divergence from the vanilla model file:** it tests `terrain = oasis`
directly. BC arms never test terrain, culture, faith or kinship at all. They test
`var:bc_battle_ground`, `var:bc_battle_bond` and `var:bc_battle_size` — flags the
script ladders already decided. This is rule 2 of §2, and it is what makes every
arm's selection visible in `debug_log`.

### Shape

All definitions are `type = character`, called on the anchor. The full assembled
form, showing all four classes concatenated:

```
bc_banner_falls_toast_desc:0 "[bc_chronicle_subject.Custom('bc_banner_falls_core')] [bc_chronicle_subject.Custom('bc_banner_falls_ground')] [bc_chronicle_subject.Custom('bc_bond_clause')] [bc_chronicle_subject.Custom('bc_scale_clause')]"
```

| class | count | keyed on | shared or per-moment |
|---|---|---|---|
| core | 10 × 3 | nothing — `random_valid = yes` | per-moment |
| ground | 10 × 6 | `var:bc_battle_ground` | per-moment |
| bond | 5 | `var:bc_battle_bond` | shared |
| scale | 4 | `var:bc_battle_size` | shared |

Ground clauses are per-moment because the verb has to agree: a standard goes down
*in the mud*, a flank collapses *among the trees*. Bond and scale clauses are
moment-agnostic and shared.

Roughly **100 loc keys covering some hundreds of readings**, against 10 today.
Cost is additive, coverage is multiplicative.

Every class carries a **fallback arm with no trigger, last**. That arm is what a
stale anchor or a cleared variable resolves to, and it must read as complete
prose on its own.

### `random_valid = yes` is restricted to toasts

Vanilla uses it at `00_servants.txt:3`. It picks randomly among valid arms, which
is a repetition-killer needing no inputs at all.

**It must never appear on a memory or nickname description.** Those re-render
every time the player opens the window, so a random arm would make the same
remembered battle read differently each time it is looked at. Toasts fire once
and are safe. This is reasoned, not measured; the rule is cheap and the bug would
be very hard to attribute.

### `Custom2` is deliberately not used

The two-argument form exists (`board_game_events_l_english.yml:114`) and would be
the obvious way to compare two characters inside loc. It is rejected: across all
of vanilla's English localization every `Custom2` second argument is a saved
scope or `ROOT.Char`, and **nothing passes a variable-held character**. The foe
lives in `var:bc_battle_foe`, so using `Custom2` would require either a new
meaning-carrying saved scope — forbidden by §2 rule 1, and `scope:bc_open_foe` is
the documented stale-foe hazard — or an unproven `.Var()`-into-`Custom2` form.
The bond ladder in §2 removes the need entirely and is instrumentable besides.

## 4. Section 3 — verification, with no game run

This section is sequenced **first**, because it is what makes the rest
statically checkable.

### The toolchain gap this design creates

`validate.py` collects top-level definitions from any `common/**/*.txt` and
checks loc files for BOM, header and duplicates. It does **not** check that a
custom-loc arm's `localization_key` exists, and it does **not** check that a
`[X.Custom('key')]` reference resolves.

This design multiplies loc keys roughly tenfold and **every one of those links
would be invisible to the toolchain** — the same failure class as
`flag:$PARAM$`: silently wrong, validate passes clean.

### So the tooling comes first

`ck3.py validate` gains two checks, and they land **before any fragment is
written**:

1. every `localization_key` inside a `common/customizable_localization/` arm
   resolves to a loc key defined in the mod
2. every `Custom('...')` reference in the mod's loc whose key begins `bc_`
   resolves to a custom-loc definition in the mod

Check 2 is scoped to the `bc_` prefix on purpose. An unscoped check would
false-positive the moment the mod references a vanilla or AGOT definition, and
designing in a warning the mod then has to suppress is worse than not checking.

`LOC_EXPECTED` is left alone — custom-loc definition keys are not themselves
localized, and adding the category would produce false warnings.

### The one unproven premise

`.Custom()` appears **nowhere** in this mod today. The nearest existing form — a
saved scope inside a toast desc, `bc_l_english.yml:123` — is itself on the
README's *"Not yet verified in game"* list.

What *is* proven by eye, in the 2026-08-13 confirmation run, is reading a
variable from loc: `[ROOT.Var('battle_location').GetProvince.GetName]` renders.

So the first content step ships **one** fragment on **one** moment, with the
script-side band markers, and nothing else. That is the `bc_spike` discipline
this project already uses. **This is a gate, and §7 sequences the rest behind
it.** It costs no dedicated run — the spike is observed in ordinary play, in the
player's first battle — but the work behind it does not start until the player
confirms it rendered.

### New permanent markers

- `BC: ground rough|forest|open|bog|mountain|frozen`
- `BC: bond nemesis|kin|countryman|heathen|stranger`

Eleven, from the two script ladders. They give band distributions the terrain
census never measured for the mod's own choices, and they are the only
instrumentation the flavour system can have.

## 5. Section 4 — the eve

`bc_chronicles.0011` today: one intro desc, a two-way `first_valid` on nemesis vs
stranger, three options.

It fires **only for a human commanding in person** (`is_ai = no`) at
`var:bc_battle_size >= 3` behind a 90-day flag — 2 offers in 44 battles. So it is
rare but **100% seen**, the inverse of the moments, most of which happen to AI
commanders nobody watches.

### The eve must not read scratch

An event desc renders when the player gets round to the pop-up, possibly after
the battle has ended and `bc_clear_scratch_effect` has run. The mod already paid
for this and recorded the fix at `bc_scripted_triggers.txt:294-302`:
`bc_eve_facing_nemesis_trigger` reads `scope:bc_eve_foe`, not
`var:bc_battle_foe` — *freshness from the variable, durability from the scope*.

Everything new in the eve follows that same pattern and **nothing in it reads
`var:bc_battle_ground` or `var:bc_battle_bond`**:

- the foe paragraph tests `scope:bc_eve_foe`, which already exists, against
  `root` — the same kin/culture/faith comparisons the bond ladder makes, written
  once more here because the scope is different. Each arm is nested behind
  `exists = scope:bc_eve_foe`.
- the ground paragraph tests a **new saved scope `bc_eve_ground`**, written from
  `scope:combat_side.combat.location` one line before the raise in
  `bc_eve_offer_effect`, exactly as `bc_eve_foe` is written one line before the
  raise today. Its arms call the six band triggers from §2 directly on that
  scope. This is not a meaning-carrying scope in the §2 rule-1 sense: it names a
  province, the band triggers are pure functions of that province, and freshness
  comes from its being rewritten at every raise.

### Changes

- **desc becomes three assembled paragraphs**, each its own small `first_valid`
  chain: the intro, the foe paragraph, the ground paragraph. Hand-written whole
  paragraphs, not fragments — this is the mod's showpiece and it is read every
  time it fires. Every chain ends in an untriggered fallback.
- **contextual options.** CK3 event options take a `trigger = { }` and are hidden
  when it fails. Two conditional options: one offered only on `rough`/`forest`
  ground via the band triggers on `scope:bc_eve_ground`, one offered only when
  `bc_eve_facing_nemesis_trigger = yes`.

**A late-opened eve degrades, it does not break.** If the pop-up is answered
after the battle, both new option triggers still evaluate — they read scopes, not
scratch — so the option set is stable. This is the whole reason for using scopes
here.

### What must not change

**No option may apply momentum.** The file's own header states it: the battle has
not started, the eve is about shape, not advantage. New options apply family-2
verb modifiers through `bc_add_verb_effect` or they apply nothing.

### The size gate stays at 3

Lowering it to 2 is **rate-safe** — the eve never calls
`bc_record_moment_effect`, so it cannot move moments-per-battle. It is an
*interrupt budget* question, not a pacing one. Recommendation: keep 3. Recorded
here so a future reader knows the lever exists and knows it is safe.

## 6. Section 5 — what a battle leaves behind

### Outcome varies with who the foe was

On a notable win, the prestige/piety award reads `var:bc_battle_bond` on the
commander: beating a man of your own faith is worth prestige, beating a
`heathen` is worth piety, beating a `nemesis` is worth more of whichever
applies. **No new state and no new comparison** — the flag the prose already
reads is the flag the award reads, which is the point of classifying in script.

The read is on the commander, in the graders, nested behind
`exists = var:bc_battle_bond`, and it runs **before** `bc_clear_scratch_effect`,
which `bc_aftermath_events.txt` already places last in both graders for exactly
this class of reason.

### Styled memories: designed, then rejected

The obvious second outcome is to make the battle memory remember *how* and not
only *where*, keying off `var:bc_battle_style`. It is rejected on three
independent grounds, recorded here so it is not re-proposed:

1. **Scope.** `bc_battle_memory_effect` is called from inside `every_side_knight`
   (`bc_aftermath_events.txt:95-109`, `:283-305`), so the scope is the **knight**.
   `var:bc_battle_style` lives on the side commander, and the mod's hardest
   invariant is that no `bc_` variable is ever written onto a knight
   (`bc_ledger_effects.txt:9-13`). The ladder would have to reach
   `root.side_commander.var:bc_battle_style` from inside a per-knight iteration,
   and `bc_chronicles.0092`'s own `trigger_if` shows `side_commander` is not
   guaranteed to exist there.
2. **The input is not reliable.** `var:bc_battle_style` is written only by
   `bc_write_style_effect`, reached only through `bc_record_moment_effect`.
   Notability is decided by `bc_battle_is_notable_trigger`, a `calc_true_if` over
   size, blood, odds, warscore and wipe that is **independent of whether any BC
   moment fired** — so a notable battle with zero moments has no style at all.
   Worse, `bc_ledger_effects.txt:495-506` documents a KNOWN LEAK in which a stale
   style from an unanswered pop-up survives into the next battle. Selecting a
   permanent, 40-year memory from that input would make the leak permanent too.
3. **Cost.** Style cannot be stored *on* the memory — the desc would have to
   print a flag, which loc cannot do, and reading it from a custom loc would need
   a `type = character_memory` that is **not known to exist**. Distinct memory
   types are the only mechanism, and that is 6 styles × win/lost = 12 new memory
   type definitions plus roughly 48 loc strings, none of which §3 counted.

The battle memory therefore keeps exactly its present shape.

**A standing constraint for whoever revisits it:** anything ever added to a
memory must go inside the **existing** `random_memory` block in
`bc_reward_effects.txt:40-54`. That block identifies the just-created memory by
`NOT = { has_variable = battle_location }`; after the first `set_variable` that
test is false, so a second block with the same limit would find an older memory
or none.

### What stays untouched

Non-lethal. No `death`, no maiming. `bc_wound_effect` is not widened by this
design; it is mid-measurement and handoff §3.1 owns it.

## 7. Section 6 — new moments, designed and deferred

This strand is **not implemented by this spec's plan.** It is recorded because
the analysis is worth keeping and because deferring it is itself a decision.

### The design

The pacing decision forbids diluting the pool. It does not forbid new keys — it
forbids new *aggregate weight*:

```
sum of BC commander phase-event `base` = 440   (60+60+40+60+60+60+100)
sum of BC knight phase-event    `base` = 360   (150+150+60)
```

Any new key is funded by reducing existing bases so these totals are unchanged.

The measured defect worth attacking is that `decisive` is starved by call-site
timing, not by its floor (handoff §2.4). A new commander key valid only late —
`exists = var:bc_battle_moments` nested over `var:bc_battle_moments >= 4` —
requesting `decisive`, puts a decisive *request* where the ledger can actually
grant it.

### Why it is deferred

Weight neutrality is **neutrality of declared base, not of realised rate.** The
pool weights only *valid* events, so a new key whose `is_valid` opens in
situations the old ones did not could still raise BC's aggregate valid weight.
That can only be settled by a run, and this design is built to need none.

It is also fully independent of §2 through §6: nothing in the flavour, eve or
outcome work depends on it, and it depends on nothing in them. It costs nothing
to hold.

## 8. Sequencing

| # | strand | gate |
|---|---|---|
| 1 | validator checks (§4) | none |
| 2 | six band triggers + context plumbing + markers (§2) | none |
| 3 | **one proving fragment on one moment** (§4) | ships; player reports whether it rendered |
| 4 | the remaining prose fragments (§3) | **blocked on step 3** |
| 5 | the eve (§5) | none — uses no `.Custom()` |
| 6 | foe-relative outcome (§6) | none |
| — | new moments (§7) | deferred out of this plan |

Steps 1, 2, 3, 5 and 6 are one deliverable and need no game testing. Step 4 is a
second deliverable, and the only thing standing between it and the first is one
sentence from the player after his next battle.

## 9. Risks

- **`.Custom()` is unproven in this mod.** Retired by step 3 at the cost of one
  fragment, and steps 5 and 6 are deliberately built not to need it.
- **`random_valid` re-render instability** on any surface that re-renders.
  Mitigated by rule, not by mechanism; a reviewer should check every use.
- **Custom-loc arms cannot be instrumented.** Accepted, and the reason both
  ladders live in script.
- **`type = character_memory` is not known to exist.** Avoided entirely — §6
  drops the styled memory rather than working around it.
- **The eve's new saved scope is one more scope that cannot be unsaved.** It
  names a province and is rewritten at every raise, so the worst case is last
  battle's ground on an eve whose own raise failed to write it — which cannot
  happen, since the raise and the write are adjacent lines in the same effect.
- **Weight-budget neutrality is predicted, not measured.** §7 only, and §7 is
  deferred for exactly that reason.
