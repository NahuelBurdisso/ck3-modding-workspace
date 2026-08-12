# Script cheat sheet

Paradox script is `key = value` and `key = { ... }`. `#` starts a comment.
Everything below is CK3 (Jomini) flavour.

## Scopes

A scope is "the thing the current block is talking about". Scope types:
`character`, `title`, `province`, `culture`, `faith`, `dynasty`, `house`,
`war`, `army`, `scheme`, `activity`, `struggle`, `artifact`, `story`, `value`.

- `root` — the scope the block started in.
- `this` — the current scope.
- `prev` — the scope one level out.
- `scope:name` — a saved scope, created with `save_scope_as = name`.

Change scope by naming a link, then a block:

    liege = { add_gold = 100 }                 # single target
    every_vassal = { add_prestige = 50 }       # iterate, all
    random_courtier = { limit = { is_adult = yes } add_trait = brave }
    any_child = { is_alive = yes }             # trigger-side iterator

Iterator prefixes: `every_` (all, effect), `random_` (one, effect),
`ordered_` (sorted+limited, effect), `any_` (trigger, "does at least one match").
All of them take an optional `limit = { <triggers> }`.

## Triggers vs effects

- **Triggers** answer yes/no and live in `trigger`, `limit`, `is_shown`,
  `is_valid`, `potential`. `AND`/`OR`/`NOT`/`NAND`/`NOR` group them; a plain list
  is an implicit `AND`.
- **Effects** change state and live in `effect`, `immediate`, `option`,
  `on_action` bodies.

Common triggers: `is_alive`, `is_adult`, `is_ruler`, `has_trait`, `age >= 16`,
`gold >= 100`, `exists = scope:target`, `is_at_war`, `has_character_flag`,
`is_landed`, `culture = { ... }`, `faith = { ... }`, `opinion = { target = ... value >= 50 }`.

Common effects: `add_trait`, `remove_trait`, `add_gold`, `add_prestige`,
`add_piety`, `add_character_flag = { flag = x years = 5 }`, `trigger_event`,
`add_opinion = { target = ... modifier = ... }`, `death = { death_reason = ... }`,
`add_character_modifier = { modifier = x years = 10 }`, `save_scope_as`.

Conditionals inside effects:

    if = { limit = { has_trait = brave } add_prestige = 100 }
    else_if = { limit = { has_trait = craven } add_stress = 20 }
    else = { add_gold = 10 }

## Reusable blocks

    # common/scripted_triggers/mymod_scripted_triggers.txt
    mymod_is_eligible_trigger = {
        is_adult = yes
        is_landed = yes
        NOT = { has_character_flag = mymod_done }
    }

    # common/scripted_effects/mymod_scripted_effects.txt
    mymod_reward_effect = {
        add_gold = 100
        add_character_flag = { flag = mymod_done years = 10 }
    }

Call them by name where a trigger/effect is expected. Parameters use `$NAME$`
placeholders, passed as `mymod_effect = { NAME = value }`.

    # common/script_values/mymod_script_values.txt
    mymod_reward_value = {
        value = 50
        if = { limit = { has_trait = greedy } multiply = 2 }
        min = 10
    }

Script values are usable anywhere a number is: `add_gold = mymod_reward_value`.

## Events

    # events/mymod_events.txt
    namespace = mymod

    mymod.0001 = {
        type = character_event
        title = mymod.0001.t
        desc = mymod.0001.desc
        theme = default

        trigger = { is_adult = yes }
        immediate = { save_scope_as = actor }
        option = {
            name = mymod.0001.a
            add_prestige = 100
        }
    }

The event id must start with the file's `namespace`. Fire one with
`trigger_event = mymod.0001` or `trigger_event = { id = mymod.0001 days = 30 }`.

## on_actions

`common/on_action/` hooks script to game moments. Never replace a vanilla
on_action file — declare the same on_action name in *your own* file and CK3
appends your entries:

    on_birth_child = {
        events = { mymod.0001 }
        on_actions = { mymod_extra_on_action }
    }

Useful ones: `on_birth_child`, `on_death`, `on_marriage`, `yearly_playable_pulse`,
`three_year_pool_pulse`, `on_war_won_attacker`, `on_game_start`,
`on_game_start_after_lobby` (the right place for one-time setup).

## Combat

`common/combat_phase_events/` merges per key across files, so always ship a new
file. An entry rolls every `COMBAT_EVENT_DAYS = 5` while a battle runs:

    bc_banner_falls = {
        type = commander          # roots on the commander; `is_ai = no` means
                                  # the PLAYER is personally leading that army
        is_valid = { ... }        # gate hard here
        chance = { base = 60 modifier = { add = 40 martial >= 12 } }
        effect = { ... }
    }

`type = knight` has **no** `is_ai` gate — it fires for every knight on every side
of every combat in the world. One battle produced 41 fires. Gate hard, and do no
work before the gate.

Root's `scope:combat_side` is set for both types. From it:

| Link | Gives |
|---|---|
| `combat` | the combat; `.location` is a province |
| `enemy_side` | the other side |
| `side_commander` | may not exist — use `?=` |
| `side_primary_participant` | the ruler whose war it is |
| `side_strength` | soldiers still fighting, **divided by 1000** by the engine |
| `any_/every_/random_side_knight` | the knights |

A trigger can only compare one side's strength against the other's. For "are we
outnumbered by half again", the multiplied figure has to come out of a script
value — vanilla does exactly this in `00_combat_values.txt`:

    vastly_outnumbered_combat_side_threshold = { value = side_strength multiply = 5 }

An `advantage` term on a **character modifier** on the commander does reach the
combat roll and renders in the advantage breakdown under its localized name.
Verified. AGOT's own combat phase events use no `advantage` at all, so this is
unclaimed ground in that stack.

## Localization

    # localization/english/mymod_l_english.yml   (UTF-8 WITH BOM)
    l_english:
     mymod.0001.t:0 "A Curious Letter"
     mymod.0001.desc:0 "[ROOT.Char.GetFirstName] reads the letter."
     mymod.0001.a:0 "Burn it."

- `[Scope.Function]` calls a datafunction; `$KEY$` inlines another loc key.
- `#bold text#!`, `#V value#!`, `#weak ...#!` are formatting tags.
- `[trait_brave|E]` renders a game-concept link.
- Conventional key names: traits `trait_<key>` / `trait_<key>_desc`, decisions
  `<key>_decision` / `_desc` / `_confirm`, modifiers `<key>`.

## Where to look things up

**First: ask the engine.** `docs/api/<version>/` holds the `script_docs` dump —
every effect, trigger, scope link, modifier and on_action, as this binary defines
them:

    python tools/ck3.py api side_commander      # what scope does this take/give
    python tools/ck3.py api add_gold            # does it exist, in what scope
    python tools/ck3.py api knight --partial

Then the index, instead of grepping 30k files:

    python tools/ck3.py find add_courtly_glory       # where is this defined
    python tools/ck3.py find courtly --partial
    python tools/ck3.py loc trait_brave              # what text does a key show
    python tools/ck3.py where common/traits/00_traits.txt

For raw syntax examples, read the vanilla file the index points you at — vanilla
is the authoritative reference for what the engine accepts.
