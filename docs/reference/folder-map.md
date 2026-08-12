# CK3 folder map

A mod mirrors the layout of `<game>/game/`. Any file you place at the same
relative path as a vanilla file **replaces it wholesale** — there is no merging,
so overriding a 3000-line vanilla file to change one number means you now own
every future patch's changes to that file too. Prefer adding a new file with a
unique name over replacing a vanilla one.

## Top level

| Folder | Contents | Override granularity |
|---|---|---|
| `common/` | Nearly all gameplay script: traits, decisions, laws, cultures, faiths, buildings, MAA, modifiers, scripted effects/triggers/values | per file |
| `events/` | Event definitions, grouped by `namespace` | per file |
| `history/` | Starting world state: characters, titles, provinces, wars | per file |
| `localization/` | `.yml` text, one folder per language | per file |
| `gui/` | `.gui` interface layout | per file |
| `gfx/` | Textures, models, portraits, coat-of-arms art, `.asset`/`.gfx` definitions | per file |
| `map_data/` | Heightmap, provinces bitmap, terrain, rivers, adjacencies | per file |
| `music/`, `sound/` | Audio + `.asset` declarations | per file |
| `data_binding/` | Script-side datafunction promotes used by `gui/` | per file |
| `notifications/` | Toast/alert definitions | per file |
| `dlc/` | DLC-gated content (mods rarely touch) | per file |
| `tests/` | Paradox's own script tests | n/a |

## `common/` subfolders that matter most

**Script building blocks** — write these first, reuse them everywhere:
- `scripted_effects/` — named reusable effect blocks
- `scripted_triggers/` — named reusable boolean conditions
- `script_values/` — named numeric formulas (`value`, `add`, `multiply`, `if`)
- `scripted_guis/` — bridges a `.gui` widget to script effects/triggers
- `scripted_lists/`, `scripted_modifiers/`, `scripted_rules/`, `scripted_costs/`
- `customizable_localization/` — script-driven text branches
- `on_action/` — hooks that fire on game events (birth, death, monthly pulse, war end)

**Character content**: `traits/`, `nicknames/`, `character_interactions/`,
`character_interaction_categories/`, `character_backgrounds/`, `focuses/`,
`lifestyles/`, `lifestyle_perks/`, `character_memory_types/`, `secret_types/`,
`hook_types/`, `opinion_modifiers/`, `scripted_relations/`, `deathreasons/`.

**Realm & politics**: `laws/`, `governments/`, `council_positions/`,
`council_tasks/`, `court_positions/`, `court_types/`, `court_amenities/`,
`factions/`, `casus_belli_types/`, `casus_belli_groups/`, `schemes/`,
`subject_contracts/`, `lease_contracts/`, `succession_election/`,
`succession_appointment/`, `diarchies/`, `tax_slots/`, `legitimacy/`,
`house_unities/`, `house_aspirations/`, `confederation_types/`.

**World**: `landed_titles/` (nested `e_ > k_ > d_ > c_ > b_`), `province_terrain/`,
`terrain_types/`, `holdings/`, `buildings/`, `great_projects/`, `culture/`,
`religion/`, `struggle/`, `situation/`, `legends/`, `epidemics/`, `travel/`,
`domiciles/`, `raids/`.

**Player-facing systems**: `decisions/` + `decision_group_types/`, `activities/`,
`artifacts/`, `accolade_types/` + `accolade_icons/` + `accolade_names/`,
`inspirations/`, `story_cycles/`, `task_contracts/`, `guest_system/`,
`courtier_guest_management/`, `pool_character_selectors/`.

**Numbers & tuning**: `defines/` (global constants — override only the specific
define, the file is read additively per key), `modifiers/`,
`modifier_definition_formats/`, `men_at_arms_types/`, `combat_effects/`,
`combat_phase_events/`, `game_rules/`, `ai_goaltypes/`, `ai_war_stances/`,
`playable_difficulty_infos/`.

**Presentation**: `event_backgrounds/`, `event_themes/`, `event_2d_effects/`,
`event_transitions/`, `flavorization/`, `game_concepts/`, `messages/`,
`message_filter_types/`, `message_group_types/`, `important_actions/`,
`suggestions/`, `named_colors/`, `coat_of_arms/`, `genes/`, `ethnicities/`,
`portrait_types/`, `dna_data/`, `bookmarks/` + `bookmark_portraits/`,
`effect_localization/`, `trigger_localization/`, `modifier_icons/`.

**Dynasty**: `dynasties/`, `dynasty_houses/`, `dynasty_legacies/`,
`dynasty_perks/`, `dynasty_house_mottos/`, `dynasty_house_motto_inserts/`,
`house_relation_types/`.

## Load order

Vanilla loads first, then each enabled mod in the order listed in
`dlc_load.json`. **The last source to provide a path wins.** Compatibility
patches therefore must sit *below* every mod they patch.

Query it instead of guessing:

    python tools/ck3.py where common/on_action/child_birth_on_actions.txt
    python tools/ck3.py conflicts
