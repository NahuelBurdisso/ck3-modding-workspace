# Battle Chronicles — estructura y conexión con el juego

Todo lo de aquí está leído de los archivos del mod, no supuesto. Las cifras son
del 2026-08-18.

---

## 1. Cómo entra el mod al juego

    Steam ─── lanza ───► ck3.exe
                            │
                            │ lee
                            ▼
     D:/Documents/Paradox Interactive/Crusader Kings III/dlc_load.json
                            │
                            │ el ORDEN de la lista ES el orden de carga
                            │ (el último gana los conflictos)
                            ▼
      [1] AGOT ──► [2..43] submods, parches... ──► [44] Battle Chronicles
                                                                        │
                                                                        ▼
                                                     mod/battle_chronicles.mod
                                                        path="D:/ck3/mods/battle_chronicles"
                                                                        │
                            ┌───────────────────────────────────────────┘
                            ▼
              NO HAY COPIA. El descriptor apunta al código fuente.
              Editar el repo = editar lo que el juego carga.

**Cero colisiones de archivos.** Cada archivo del mod tiene un nombre único y
nuevo (`bc_*`), así que no reemplaza nada de vanilla ni de AGOT: el motor
*fusiona* las claves de cada carpeta.

---

## 2. Qué pasa durante una batalla

    ┌──────────────────────────── BATALLA EN CURSO ────────────────────────────┐
    │                                                                          │
    │  cada 5 días (COMBAT_EVENT_DAYS) el motor sortea UN evento de fase        │
    │                                                                          │
    │   BOLSA DEL COMANDANTE                    BOLSA DEL CABALLERO            │
    │   ┌────────────────────────┐              ┌────────────────────────┐     │
    │   │ commander_none  1.000  │              │ knight_none     2.000  │     │
    │   │ eventos de AGOT        │              │ eventos de AGOT        │     │
    │   │ ▓ BC: 238 plantillas   │              │ ▓ BC: 206 plantillas   │     │
    │   │   suma 11.010          │              │   suma 16.580          │     │
    │   └───────────┬────────────┘              └───────────┬────────────┘     │
    │               │  gana el sorteo                       │                  │
    │               ▼                                       ▼                  │
    │   ┌──────────────────────────────────────────────────────────────┐       │
    │   │ is_valid = { ... }   ← los 344 gates de bc_scripted_triggers  │       │
    │   │   · bc_chronicle_ready_commander_trigger  (¿sin cooldown?)    │       │
    │   │   · gate de situación (perdiendo / terreno / rasgo / familia) │       │
    │   └──────────────────────────────┬───────────────────────────────┘       │
    │                                  ▼                                       │
    │   ┌──────────────────────── effect = { } ────────────────────────┐       │
    │   │                                                              │       │
    │   │  1. save_scope_as = bc_commander                             │       │
    │   │                                                              │       │
    │   │  2. bc_battle_open_effect      ← SOLO en el primer momento    │       │
    │   │       escribe el contexto de la batalla en variables:         │       │
    │   │       foe · tamaño · terreno · vínculo · nemesis              │       │
    │   │       y lanza la VÍSPERA ──────────► bc_chronicles.0011       │       │
    │   │                                      (3 párrafos, 11 opciones)│       │
    │   │                                                              │       │
    │   │  3. bc_mark_chronicle_commander_effect                        │       │
    │   │       pone la bandera bc_chronicle_recent (15 días)           │       │
    │   │       ◄── ESTE ES EL FRENO REAL, no los pesos                 │       │
    │   │                                                              │       │
    │   │  4. ¿es el jugador y no hay cooldown de pop-up?               │       │
    │   │        SÍ ──► bc_chronicles.0001 … .0005   (ventana con       │       │
    │   │                                             decisión)         │       │
    │   │        NO ──► bc_record_moment_effect + send_interface_toast   │       │
    │   │               (aviso lateral, sin decisión)                   │       │
    │   └──────────────────────────────┬───────────────────────────────┘       │
    │                                  ▼                                       │
    │   ┌──────────── bc_record_moment_effect (TIER/KIND/SWING) ───────┐       │
    │   │  aplica la ESCALERA DE IMPULSO como modificador temporal:     │       │
    │   │                                                              │       │
    │   │     bc_momentum_decisive   advantage +10   ▲ va ganando       │       │
    │   │     bc_momentum_major      advantage  +6   │                  │       │
    │   │     bc_momentum_minor      advantage  +3   │                  │       │
    │   │     ─────────────────────────────────────  0                  │       │
    │   │     bc_faltering_minor     advantage  -3   │                  │       │
    │   │     bc_faltering_major     advantage  -6   │                  │       │
    │   │     bc_faltering_decisive  advantage -10   ▼ se desmorona     │       │
    │   │                                                              │       │
    │   │  El nombre del modificador SE IMPRIME tal cual en el desglose │       │
    │   │  de ventaja, junto a "Commander Martial Skill". Por eso están │       │
    │   │  escritos como prosa y no como etiquetas técnicas.            │       │
    │   └──────────────────────────────────────────────────────────────┘       │
    │                                                                          │
    │  ── vuelve a empezar en 5 días ──                                        │
    └──────────────────────────────────────────────────────────────────────────┘
                                       │
                                  fin del combate
                                       ▼
    ┌─────────────────────────── DESPUÉS DE LA BATALLA ────────────────────────┐
    │                                                                          │
    │   on_combat_end_winner ──► bc_chronicles.0091 ┐                           │
    │   on_combat_end_loser  ──► bc_chronicles.0092 ┤ ocultos, scope=combat_side│
    │                                               │                           │
    │   Un evento por gancho, NO uno compartido: dentro del evento no hay       │
    │   forma de saber qué gancho lo llamó.                                     │
    │                                               ▼                           │
    │        1. limpian el impulso  (si no, sobreviviría a su batalla)          │
    │        2. califican la batalla: ¿fue memorable?                           │
    │        3. si lo fue → memoria de 40 años a cada caballero vivo            │
    │        4. el vencedor suma en var:bc_notable_battles                      │
    │             3 victorias + martial >= 14 + sin apodo → APODO en el campo   │
    │        5. rivalidad: rival → nemesis según cuántas veces te ganó          │
    │                                               │                           │
    │                                    +1 día ────┴──► bc_chronicles.0093     │
    │                                                    (lee los caballeros    │
    │                                                     muertos; diferido     │
    │                                                     porque .0091 corre    │
    │                                                     ANTES de que el motor │
    │                                                     los mate)             │
    └──────────────────────────────────────────────────────────────────────────┘

---

## 3. Mapa de archivos

    battle_chronicles/
    │
    ├── descriptor.mod ............ nombre, versión, dependencia de AGOT
    │
    ├── common/
    │   ├── combat_phase_events/    ◄── LA PUERTA DE ENTRADA AL COMBATE
    │   │   ├── bc_commander_phase_events.txt ... 238 momentos del comandante
    │   │   └── bc_knight_phase_events.txt ...... 206 momentos del caballero
    │   │
    │   ├── scripted_triggers/      ◄── LAS PREGUNTAS ("¿se cumple la situación?")
    │   │   ├── bc_scripted_triggers.txt ........ 344 gates, todos en un sitio
    │   │   └── bc_ground_triggers.txt .......... las 6 bandas de terreno
    │   │
    │   ├── scripted_effects/       ◄── LAS ACCIONES ("qué se escribe y se aplica")
    │   │   ├── bc_context_effects.txt .......... abre la batalla, guarda el scope
    │   │   ├── bc_ledger_effects.txt ........... el libro mayor + la costura
    │   │   ├── bc_scripted_effects.txt ......... impulso: aplicar, limpiar, frenar
    │   │   ├── bc_reward_effects.txt ........... premios
    │   │   ├── bc_reputation_effects.txt ....... apodos y fama
    │   │   ├── bc_rivalry_effects.txt .......... escalera rival → nemesis
    │   │   └── bc_eve_effects.txt .............. arma la víspera
    │   │
    │   ├── modifiers/
    │   │   ├── bc_momentum_modifiers.txt ....... la escalera ±3/±6/±10
    │   │   └── bc_battle_modifiers.txt ......... bloodied, shieldwall,
    │   │                                          spent_horse, pursuit, ground_held
    │   │
    │   ├── on_action/
    │   │   └── zz_bc_on_actions.txt ............ SOLO events = { }, nunca effect = { }
    │   │
    │   ├── character_memory_types/
    │   │   └── bc_memories.txt ................. hermano de escudo, batalla
    │   │                                          ganada/perdida, nemesis, salvavidas
    │   │
    │   ├── script_values/ .......................  los 4 umbrales de proporción
    │   ├── opinion_modifiers/ ................... opiniones que deja la batalla
    │   ├── customizable_localization/
    │   │   └── bc_flavour.txt .................. 207 brazos de prosa variable
    │   └── game_rules/
    │       └── bc_game_rules.txt ............... bc_frequency · bc_swing ·
    │                                             bc_aftermath · bc_rivalry · bc_wounds
    │
    ├── events/
    │   ├── bc_events.txt ....................... .0001–.0005  pop-ups con decisión
    │   ├── bc_eve_events.txt ................... .0011        la víspera
    │   └── bc_aftermath_events.txt ............. .0091 .0092 .0093  ocultos, el balance
    │
    └── localization/english/
        └── bc_l_english.yml .................... 1.344 claves de texto

---

## 4. Las tres reglas de diseño que explican la forma del código

**No se reemplaza nada.** Todo archivo es nuevo y con nombre propio. Por eso el
mod puede cargar el último entre 44 sin romper a nadie.

**Nunca un `effect = { }` en `on_action`.** Las listas `events` se fusionan entre
mods; `effect` no — el motor conserva uno solo y elige por *orden alfabético de
archivo*, no por orden de carga. Un mod que carga último igual pierde. Por eso
todo cuelga de `events = { }` + un evento oculto.

**Primero el estado, después la presentación.** Ningún efecto de juego vive
dentro de un `send_interface_toast`. El aviso solo muestra; el `effect` cambia.

---

## 5. Dónde está el riesgo, visto en el diagrama

En el bloque 2, la caja de las bolsas: **11.010 contra 1.000** en comandante y
**16.580 contra 2.000** en caballero. Si los gates se cumplen, casi todo sorteo
lo gana el mod. Lo único que lo modera es la bandera `bc_chronicle_recent` de la
caja 3. Ese equilibrio se midió cuando el mod tenía 10 plantillas; hoy tiene 444
y nadie lo volvió a medir.
