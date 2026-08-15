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

Every situational input except battle ratio is unread. A battle on the glacier
against a brother reads identically to a field battle in the Reach against a
stranger.

## 1. Decisions taken before design

| question | answer |
|---|---|
| where does depth land | prose, the eve, and outcomes. New *moments* are designed but deferred — see §7 |
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

## 2. How a moment learns its context

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

### Six band triggers, extracted from the partition the mod already has

**The mod already classifies terrain into six bands.**
`bc_terrain_bucket_effect` (`bc_reputation_effects.txt:267-339`) maps AGOT's 23
helpers onto `desert` / `open` / `rough` / `forest` / `jungle` / `winter`, and
its header records that the ladder was verified exhaustive over all 23,
`5 + 5 + 7 + 2 + 2 + 2 = 23`, every helper once.

**This design reuses that partition unchanged rather than inventing a second
one.** An earlier draft proposed `rough`/`forest`/`open`/`bog`/`mountain`/
`frozen`, which left the whole desert family (drylands, desert, desert_mountains,
oasis, canyon) and the jungle family (jungle, cloudforest) with no home — seven
of the 23 helpers and a large share of the AGOT map, Dorne and Essos and
Sothoryos. Two disagreeing terrain vocabularies in one mod is also how a later
reader "unifies" them and silently changes which commander trait gets awarded.

The 23-helper ladder is **extracted** into six scripted triggers, called on a
province:

```
bc_ground_is_desert_trigger     bc_ground_is_forest_trigger
bc_ground_is_open_trigger       bc_ground_is_jungle_trigger
bc_ground_is_rough_trigger      bc_ground_is_winter_trigger
```

`bc_terrain_bucket_effect` is then rewritten to call them. **That rewrite is
behaviour-preserving**: the same helper sits in the same band and writes the same
flag value, so `var:bc_terrain_this`, the streak logic and the commander-trait
award are untouched. Three callers then share one definition — the bucket effect,
the ladder below, and the eve's ground paragraph (§5), which reads a saved
province scope at render time and so cannot use a variable at all.

They never test `terrain = X` bare. AGOT defines road variants as distinct
terrain types and ~26% of the map is invisible to a bare check, silently
(`bc_reputation_effects.txt:246-254`, `bc_scripted_triggers.txt:36-43`).

`var:bc_battle_ground` and `var:bc_terrain_this` stay **separate variables**.
They carry the same vocabulary, but they are written at different times from
different sources: `bc_terrain_this` is written once at combat end from
`scope:bc_battle_province`, which the grader saved, and is removed by
`bc_reputation_effect` itself (`bc_reputation_effects.txt:581`) after the streak
comparison — it never reaches `bc_clear_scratch_effect` at all.
`bc_battle_ground` is written on every moment from `combat.location`, is read
while the battle is still running, and is scratch. Merging them would mean one
write site serving two clocks.

### The change to `bc_battle_open_effect`

That effect already runs on the side commander at **all ten** phase-event call
sites, once each at its single call site in each event — directly in the seven
commander events, and inside `scope:combat_side.side_commander ?= { }` in the
three knight events. It already writes `bc_battle_foe` and `bc_battle_size`. It
gains, in this order:

**1. `save_scope_as = bc_chronicle_subject`** on the side commander — the one loc
anchor common to all ten toasts, and the unambiguous left-hand side for the bond
comparisons below.

**2. `bc_write_ground_effect = yes`**, writing `var:bc_battle_ground` as a flag
from an ordered if-ladder over the six band triggers. Each arm carries a
`BC: ground <band>` marker.

`combat.location` may not resolve — the graders already guard their memory writes
for that reason (`bc_reputation_effects.txt:234-236`). **The guard is a chained
`exists` in an `if`, not `?=`**, because `?=` takes no `else` and the failure
path has to be instrumented.

Both halves of that path are already shipped: `bc_battle_open_effect` itself
resolves `scope:combat_side.combat` at `bc_ledger_effects.txt:100` and `:105`,
and `combat.location` is reached at `bc_aftermath_events.txt:86`. The shape:

```
remove_variable = bc_battle_ground              # first, so a failure cannot leave a stale band
if = {
    limit = { exists = scope:combat_side.combat.location }
    scope:combat_side.combat.location = {       # ladder runs in PROVINCE scope; the variable
        if / else_if × 6 ->                     #   must land back on the commander, so it is
            scope:bc_chronicle_subject = { set_variable = ... }   + BC: ground <band>
        else = { debug_log = "BC: ground NONE MATCHED" }
    }
}
else = { debug_log = "BC: ground missing" }
```

Four things in that shape are load-bearing and none is decoration:

- **the leading `remove_variable`.** Without it, a battle whose location does not
  resolve leaves the *previous* battle's band standing on a commander whose
  scratch was never cleared, and the prose lies. Clearing first makes the failure
  mode "no ground clause", which the fallback arm covers.
- **writing through `scope:bc_chronicle_subject`.** Inside
  `combat.location = { }` the scope is a province and the variable has to land on
  the commander; `root` will not do it, because neither a scripted effect nor
  `side_commander ?=` rebinds ROOT. `bc_terrain_bucket_effect` records this lesson
  at `bc_reputation_effects.txt:238-244` and saves its own `bc_terrain_subject`
  for it. **No second scope is saved here** — the anchor from write 1 is the same
  character, saved four lines above, and one scope for one commander is one fewer
  thing for a later reader to "unify".
- **the inner `else`.** The ladder is exhaustive over all 23 base helpers, so it
  is unreachable in principle — which is exactly why it logs.
  `bc_terrain_bucket_effect` makes the identical argument at
  `bc_reputation_effects.txt:256-261`.
- **the outer `else`.** This is the one failure in §2 that can actually happen.
  Without the marker it is invisible, and §5 instruments the identical failure on
  its own side.

**3. `bc_write_bond_effect = yes`**, writing `var:bc_battle_bond` as a flag from
an ordered if-ladder, first match wins, each arm carrying a `BC: bond <band>`
marker:

| band | test | marker |
|---|---|---|
| `nemesis` | `bc_facing_nemesis_trigger = yes` | `BC: bond nemesis` |
| `kin` | `var:bc_battle_foe = { is_close_family_of = scope:bc_chronicle_subject }` | `BC: bond kin` |
| `countryman` | `var:bc_battle_foe = { culture = scope:bc_chronicle_subject.culture }` | `BC: bond countryman` |
| `heathen` | `NOT = { var:bc_battle_foe = { faith = scope:bc_chronicle_subject.faith } }` | `BC: bond heathen` |
| `stranger` | the **inner** `else` — a foe who matched none of the four | `BC: bond stranger` |
| `stranger` | the **outer** `else` — no foe at all | `BC: bond nofoe` |

**`stranger` is written from two sites and they are marked differently.** The
inner `else` is not optional: without it a foe of a different culture and the
same faith — a Reachman against a Westerman, both of the Seven, which is the
single largest match-up class on the AGOT map — would match nothing, leave
`bc_battle_bond` unwritten, and emit no marker at all. That is the same
unmarked-hole failure the ground ladder gets both an inner and an outer `else`
for, and the bond ladder gets both for the same reason.

The two sites share the flag value because the prose does not need to tell them
apart — §3's `stranger` arm must read as complete prose for a leaderless enemy
*and* for an unrelated commander. Only the markers distinguish them, which is
where the distinction is actually useful.

**The nesting is one outer `if`, not a guard per row.** CK3 does not
short-circuit and guarantees no evaluation order among siblings, so a
`var:bc_battle_foe` read may never sit beside its own `exists` — and that cannot
be expressed per-arm inside an ordered `if`/`else_if` chain. `bc_reputation_effects.txt:458-463`
records this exact constraint. The shape is therefore a single
`if = { limit = { exists = var:bc_battle_foe } }` wrapping the whole chain, with
the outer `else` writing `stranger`.

**4. `var:bc_battle_creed`**, written by the same effect, a flag of `same` or
`heathen`. It exists because the bond bands are *ordered and mutually exclusive*:
`nemesis`, `kin` and `countryman` each swallow the faith question, so a
different-faith foe who shares your culture lands in `countryman` and the bond
flag then says nothing about faith at all. §6's award needs faith orthogonally.

**It is therefore a second, independent `if`/`else`, beside the bond chain and
not an arm of it** — inside the same `exists = var:bc_battle_foe` guard, but on
its own:

```
if = {
    limit = { exists = var:bc_battle_foe }

    if / else_if × 4                             # nemesis, kin, countryman, heathen
    else = { flag:stranger  + "BC: bond stranger" }

    if = {                                       # SEPARATE CHAIN. Runs on every band,
                                                 #   nemesis and kin included.
        limit = { NOT = { var:bc_battle_foe = { faith = scope:bc_chronicle_subject.faith } } }
        set_variable = { name = bc_battle_creed value = flag:heathen }
        debug_log = "BC: creed heathen"
    }
    else = {
        set_variable = { name = bc_battle_creed value = flag:same }
        debug_log = "BC: creed same"
    }
}
else = {
    set_variable = { name = bc_battle_bond value = flag:stranger }
    debug_log = "BC: bond nofoe"
    remove_variable = bc_battle_creed             # no foe, no creed. NOT a default of `same`.
}
```

The creed arms are marked on both sides, not only on absence. §2 rule 2 argues
that classification lives in script *so that its distribution is measurable*;
instrumenting only the failure would leave §6's currency split unattributable.

Making creed an `else_if` arm of the bond chain would be the natural-looking
mistake and would defeat the entire point: it would go unwritten on exactly the
three bands it was invented to cover, and §6's nemesis row could then never pay.
The no-foe path clears rather than defaulting, because a foe who cannot be
identified is not a co-religionist.

**Ordering inside the effect is load-bearing.** All the writes go **above** the
`bc_eve_offer_effect` call, which `bc_ledger_effects.txt:154-158` documents is
raised last precisely so that everything it reads is already written. The bond
ladder must come after both the anchor save and the `bc_battle_foe` write, since
it reads both.

**Every write is unconditional, not write-if-unset**, following the doctrine at
`bc_ledger_effects.txt:34-43`: scratch is cleared on `side_commander`, so a
commander replaced mid-combat is never cleared, and under write-if-unset his
stale values would freeze **permanently** rather than for one battle. The leading
`remove_variable` in the ground effect serves the same doctrine by a different
route, since that one write can legitimately fail to happen.

`bc_clear_scratch_effect` gains `remove_variable` for `bc_battle_ground`,
`bc_battle_bond` and `bc_battle_creed`. **Writers and removers must ship in the
same commit** — a remover without a writer produces
`Variable 'X' is used but is never set` twice per boot, the exact debt the
2026-08-15 run just finished retiring.

### Why staleness is safe for the anchor

`scope:bc_chronicle_subject` can go stale between battles; nothing can unsave a
scope. But every arm it feeds tests a **scratch variable**, and scratch is wiped
at combat end. A stale subject therefore resolves to an arm's **fallback**, never
to wrong flavour. This inverts the `bc_open_foe` hazard rather than repeating it.

## 3. The prose fragments

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

| class | arms | keyed on | shared or per-moment | keys |
|---|---|---|---|---|
| core | 3 | nothing — `random_valid = yes` | per-moment | 30 |
| ground | 6 + fallback | `var:bc_battle_ground` | per-moment | 70 |
| bond | 5 + fallback | `var:bc_battle_bond` | shared | 6 |
| scale | 3 + fallback | `var:bc_battle_size` | shared | 4 |

Ground clauses are per-moment because the verb has to agree: a standard goes down
*in the sand*, a flank collapses *among the trees*. Bond and scale clauses are
moment-agnostic and shared.

**Every keyed class carries a fallback arm with no trigger, last**, and those
arms are load-bearing rather than decorative. They are what a stale anchor
resolves to, and what a battle whose `combat.location` did not resolve resolves
to. Each must read as complete prose on its own. The core class needs none — it
has no trigger to fail.

**A keyed arm's trigger is `exists` then read, nested, never bare.** Vanilla
ships bare `var:X = flag:Y` in custom-loc arms (`00_ai_value_custom_loc.txt:7`)
and it would usually be harmless, but for BC the absent case is *normal* — a
stale anchor, a render after `bc_clear_scratch_effect`, a failed location — and
the mod's hardest recurring rule is that a read may not sit beside its own
`exists` (handoff §2.3). The shape for every keyed arm is therefore:

```
text = {
    localization_key = bc_..._winter
    trigger = {
        exists = var:bc_battle_ground
        trigger_if = {
            limit = { exists = var:bc_battle_ground }
            var:bc_battle_ground = flag:winter
        }
    }
}
```

Both rows are needed and neither is redundant. `trigger_if` alone would evaluate
**true** when its limit fails — an absent variable would make every arm valid —
so the bare `exists` row is what actually rejects. And `exists` is safe as a
sibling while a read is not, which is precisely the pair
`bc_eve_facing_nemesis_trigger` ships and documents at
`bc_scripted_triggers.txt:308-310`. Stated once here rather than rediscovered
per arm.

Roughly **110 loc keys covering some hundreds of readings**, against 10 today.
Cost is additive, coverage is multiplicative.

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

## 4. Verification, with no game run

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

`ck3.py validate` gains three checks, and they land **before any fragment is
written**:

1. every `localization_key` inside a `common/customizable_localization/` arm
   resolves to a loc key defined in the mod
2. every `Custom('...')` reference in the mod's loc whose key begins `bc_`
   resolves to a custom-loc definition in the mod
3. the six `bc_ground_is_*_trigger` definitions between them name each of AGOT's
   23 **base-terrain** helpers exactly once

Check 3 is what makes the `bc_terrain_bucket_effect` rewrite safe to do at all.
Exhaustiveness is currently guaranteed by a hand-verified comment
(`bc_reputation_effects.txt:256-261`); moving the ladder into triggers is the
moment to make it guaranteed by the toolchain instead. It also covers the new
ladder for free, since both read the same triggers.

Two things about it must be pinned down or it will be built wrong:

- **`agot_is_*_terrain` is not the right glob.** AGOT's
  `00_agot_terrain_type_triggers.txt` matches **26**: the 23 base helpers plus
  `agot_is_majorroad_terrain`, `agot_is_minorroad_terrain` — cross-cutting road
  families that overlap every band — and `agot_is_location_valid_vanilla_terrain`,
  which is character-scoped. A checker built to the glob reports three unhandled
  helpers forever. The check takes the **23 base names as an explicit list**,
  which is the same list the mod already hand-verified.
- **the AGOT file is outside the mod.** `validate_mod` iterates `iter_files`
  over the mod root only, so check 3 has to resolve AGOT through the playset
  sources the way `ck3.py api` and `ck3.py find` already do. If that resolution
  is unavailable the check must **skip loudly**, never pass silently.

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
this project already uses. **This is a gate, and §8 sequences the rest behind
it.** It costs no dedicated run — the spike is observed in ordinary play, in the
player's first battle — but the work behind it does not start until the player
confirms it rendered.

### New permanent markers

| marker | count | what a hit means |
|---|---|---|
| `BC: ground desert\|open\|rough\|forest\|jungle\|winter` | 6 | the band distribution, for the mod's own choices |
| `BC: ground NONE MATCHED` | 1 | unreachable in principle, which is why it logs |
| `BC: ground missing` | 1 | `combat.location` did not resolve on a moment |
| `BC: bond nemesis\|kin\|countryman\|heathen` | 4 | the bond distribution |
| `BC: bond stranger` | 1 | a foe who matched none of the four |
| `BC: bond nofoe` | 1 | no enemy commander at all |
| `BC: creed same\|heathen` | 2 | which currency §6 would pay in |
| `BC: eve ground missing` | 1 | the §5 hole, if it is real |
| `BC: award no creed` | 1 | a notable win graded with no creed flag — see §6 |

Eighteen. They are the only instrumentation the flavour system can have, and
between them they cover **every** classification arm and every failure path this
design introduces — which is the whole argument for classifying in script.
Nothing here needs a dedicated run; they accumulate in ordinary play and
`probe 'BC:'` reads them whenever someone next looks.

**They count different things and the decision table must say so.** Everything
written by `bc_battle_open_effect` — ground, bond, creed — fires **once per
moment**, so those counts share the 233-per-44-battles denominator. `BC: eve
ground missing` counts **eves offered**, and `BC: award no creed` counts
**notable wins graded**. Comparing a creed count against an award count directly
would be an error of exactly the kind handoff §2.4 was written about, so the
denominator goes into the source-comment decision table that handoff §2.1
requires beside every marker anyway.

## 5. The eve

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
  scope. It names a province and the band triggers are pure functions of that
  province, so it carries no classification of its own; freshness comes from its
  being rewritten at every raise.

The write is guarded and instrumented, and **the guard is a chained `exists` in
an `if`, not `?=`** — `?=` takes no `else`, so it cannot carry the marker. It
sits **inside `bc_eve_offer_effect`'s own `is_ai = no` gate**, next to the
`bc_eve_foe` save (`bc_eve_effects.txt:47-49`, `:67-70`), so
`BC: eve ground missing` counts eves that were actually offered and not battles:

```
if = {
    limit = { exists = scope:combat_side.combat.location }
    scope:combat_side.combat.location = { save_scope_as = bc_eve_ground }
}
else = { debug_log = "BC: eve ground missing" }
```

**The one hole, stated rather than argued away.** The raise below that block is
unconditional. If `combat.location` ever fails to resolve on a battle where a
*previous* eve succeeded, `scope:bc_eve_ground` still holds the earlier
province — so the ground paragraph and the ground-gated option resolve to a
**wrong band**, not to the fallback. Adjacency of the two lines does not prevent
this; only the location resolving does.

It is not closed by mechanism, because the cheap closures are both worse:
suppressing the whole eve when the location is missing throws away the paragraph
that does not depend on ground, and a freshness token would have to be scratch,
which is the thing this section exists to avoid. If `BC: eve ground missing` ever
reads non-zero the anchor needs rethinking; until then the exposure is one wrong
clause on a pop-up that fired twice in 44 battles, and no state is corrupted.
This is the handoff §2.4 discipline — measure the population before building for
it.

**Both new option triggers nest behind their own `exists`** — the ground option
behind `exists = scope:bc_eve_ground`, which does not exist at all on the first
eve of a save whose location failed, and the nemesis option behind whatever
`bc_eve_facing_nemesis_trigger` already guards.

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

## 6. What a battle leaves behind

### A notable win pays in the currency the foe implies

**This is a new award. There is no combat-end prestige or piety grant today** —
`add_prestige` appears only in phase events, the moment pop-ups and the eve. It
hangs in **`bc_chronicles.0091` only** — the winner grader; there is no notable-
*loss* award and `.0092` is not touched — on the notable path, inside the same
`side_commander ?= { if = { limit = { is_alive = yes } } }` block that already
calls `bc_reputation_effect`, and therefore **before** `bc_clear_scratch_effect`,
which both graders already place last and outside that gate for exactly this
class of reason.

It reads **two** flags, and reads them independently:

| flag | effect on the award |
|---|---|
| `var:bc_battle_creed` = `heathen` | pays **piety**; `same` pays **prestige** |
| `var:bc_battle_bond` = `nemesis` | pays more of whichever currency the creed flag chose |

The currency question is asked of `bc_battle_creed` and not of `bc_battle_bond`
because the bond bands are ordered and mutually exclusive: a different-faith foe
who shares your culture is filed under `countryman`, so the bond flag alone
cannot answer it. §2 writes both from one comparison for this reason.

Both reads are nested behind their own `exists`, never beside it. No new
comparison is performed here — §2 already did the work, which is the point of
classifying in script rather than in loc.

**A whole class of notable battles will not receive it, and that is expected.**
`var:bc_battle_creed` exists only if `bc_battle_open_effect` ran, i.e. only if
the battle produced at least one BC moment. `bc_battle_is_notable_trigger` is a
`calc_true_if` over size, blood, odds, warscore and wipe, and is **independent of
whether any moment fired** — the same argument §6 uses below to reject styled
memories. So a notable, momentless battle grades with no creed and pays nothing.

That is the correct behaviour: an award for how you beat a man should not fire
for a battle the chronicle never witnessed. But it must be *attributable*, or the
next reader will find a zero and start moving gates. The `else` of the creed read
logs **`BC: award no creed`**, and the ratio of that marker to the notable-win
count is the measurement — handoff §2.4, count the requests and not just the
outcomes.

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

## 7. New moments, designed and deferred

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
| 2a | extract the six band triggers, rewrite `bc_terrain_bucket_effect` onto them (§2) | none — behaviour-preserving |
| 2b | context plumbing: anchor, ground, bond, creed, markers (§2) | none |
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
- **The eve's new saved scope is one more scope that cannot be unsaved.** If
  `combat.location` fails to resolve, the eve renders a *previous* battle's
  ground band. Not closed by mechanism; instrumented with `BC: eve ground missing`
  and argued in §5.
- **The `bc_terrain_bucket_effect` rewrite touches shipped, working code.** It is
  behaviour-preserving by construction — same helper, same band, same flag value
  — and it is statically checkable by diffing the 23 helper names against the six
  new triggers. It is still the one change in this design that can regress
  something that already works, and it should be reviewed helper by helper.
- **Weight-budget neutrality is predicted, not measured.** §7 only, and §7 is
  deferred for exactly that reason.
