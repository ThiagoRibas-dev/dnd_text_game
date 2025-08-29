# GEMINI.md

## Project Description and Game Spec Summary

The game is a single-player, text-first RPG based on D&D 3.5e rules. It will feature a grid-based combat system, exploration, and downtime activities. The core of the game is an effects and state engine, where all game mechanics (races, classes, feats, spells, etc.) are defined as content blueprints (JSON/YAML) that are instantiated at runtime.

The game is divided into three modes:
*   **Encounter Mode:** For combat, traps, and NPC interactions. It's turn-based on a grid.
*   **Exploration/Travel Mode:** For moving around the world, searching, and handling random encounters.
*   **Downtime Mode:** For longer-term tasks like crafting, resting, and preparing spells.

A central "Mode Manager" handles transitions between these states. The game will also feature a detailed command-line interface for interacting with the world, and an "explain" command to provide a detailed breakdown of the last action's resolution (dice rolls, modifiers, etc.). The engine will follow specific, documented policies for rules like damage reduction, cover, and ability stacking to ensure deterministic and predictable outcomes.

### Notes and Rules ###

**Workflow:** Examination > Planning (what, where, how, why) > Refining (break into components, detail), Iteration > request and wait permission to Execute/Implement > Summarize changes > Ask for next step.

**Planning:** Before making any changes, we will perform an iterative planning step, laying out a detailed step-by-step implementation plan (what, where, how, why). Only once the plan has been accepted, we will execute the plan and edit the files in question.

**Ruff Linter:** An is an extremely fast Python linter and code formatter. After performing a batch of changes, we will always run `ruff check . --fix` to ensure things are in order.

## v1.0 Roadmap (milestones)

M1 — Project foundation and core models
- [x] Repo bootstrap finalized (pyproject, src layout, tests, CI)
- [ ] Pydantic models: Entity, GameState, Item, Weapon, Armor
- [ ] Core stats and derived stats:
  - [ ] Abilities (base, temp, damage, drain)
  - [ ] AC breakdown (armor, shield, natural, deflection, dodge, size, misc)
  - [ ] Saves (base, ability mod, misc), initiative
  - [ ] Attack bonuses (melee/ranged/touch), crit profile (range/multiplier)
- [ ] Content loader (JSON/YAML) + content folder
- [ ] Expression engine wrapper + functions: ability_mod, level/class_level, caster_level, initiator_level, HD, min/max/floor/ceil
- [ ] JSON Schemas: EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
- [ ] Deterministic RNG (seed per encounter; include seed in explain logs)
- [ ] Basic unit test harness (pytest + hypothesis)

Acceptance: Can load a player, stats compute correctly, content files validate, and tests run green.

M2 — Effects/State engine (definitions → instances)
- [ ] EffectDefinition/EffectInstance implemented (blueprint vs runtime)
- [ ] ResourceDefinition/ResourceState implemented (capacity formulas, refresh cadence)
- [ ] ConditionDefinition/ConditionInstance implemented
- [ ] Modifiers engine with stacking rules:
  - [ ] Typed bonuses (enhancement, morale, luck, insight, competence, sacred, profane, resistance, deflection, dodge, size, natural armor)
  - [ ] Unnamed bonuses + same-sourceKey non-stacking
  - [ ] Operator ordering: set/replace → add/sub (stacking) → mul/div → min/max → cap/clamp
- [ ] Rule hooks registry (incoming.effect, on.attack pre/post, on.save pre/post, scheduler ticks, incoming.damage)
- [ ] Operations: damage/heal (HP/nonlethal/ability dmg/drain), apply/remove condition, (create/spend/restore) resource, attach/detach effects, create zone
- [ ] Antimagic/suppression flags per abilityType (Ex/Su/Sp/Spell)

Acceptance: Can attach a self-buff with typed modifiers and a timed duration; modifiers apply and expire correctly; untyped same-source does not stack.

M3 — Gates and damage pipeline
- [ ] Gates per target:
  - [ ] SR gate (one CL check per target per use; SR:Yes only)
  - [ ] Save gate (Fort/Ref/Will, DC expressions, branch policies: negates/half/partial/none)
  - [ ] Attack gate (melee/ranged/touch/ray; crit confirm; concealment/miss chance)
- [ ] Damage pipeline:
  - [ ] 1) Immunity → 2) Type conversion → 3) Resist/DR/ablative pools → 4) Vulnerability → 5) Apply to HP/THP → 6) Injury rider negation (if DR reduced to 0) → 7) Post hooks
  - [ ] DR policy: apply to total physical damage per attack (documented)
  - [ ] Energy resist per packet, vulnerabilities, Temp HP before HP
- [ ] Explain/trace for last action (rolls, stacking, damage breakdown)

Acceptance: “Attack goblin” performs a full resolution with explain trace; DR/resist/vulnerability behave per spec.

M4 — Scheduler/Time + Mode Manager
- [ ] Scheduler (rounds/minutes/hours/days; durations; recurring ticks; ongoing saves)
- [ ] Mode Manager: encounter | exploration | downtime + transitions
  - [ ] Encounter enter/exit rules (per-encounter reset; end-of-encounter effect removal)
  - [ ] Exploration ticks (minutes/hours)
  - [ ] Downtime ticks (days/weeks) + daily refresh cycle
- [ ] Rest/prep windows (arcane 8h+1h prep, divine dawn+1h; interrupts cancel prep)
- [ ] Resource refresh cadence: per_round, per_encounter, per_day

Acceptance: Can rest and prepare spells; encounter boundaries reset per-encounter resources; durations and recurring effects advance across modes.

M5 — Targeting, geometry, and zones/traps
- [ ] Grid (5-ft squares), diagonal 5-10-5 policy
- [ ] Range/LoS/LoE checks; cover (+4 std, +2 partial); concealment (20%); total concealment (50%)
- [ ] Area shapes: square, burst, line, cone, wall (basic)
- [ ] Zones/hazards: on-enter/on-leave/start/end-of-turn hooks
- [ ] Traps as zones: pit (fall), darts (attack), scythe, glyph (spell effect)
- [ ] Light/vision basics: light sources with durations; low-light doubles bright radius; darkvision BW; concealment in dim light

Acceptance: Grease zone works (saves each round; Balance DC to move); pit/darts trigger properly; light affects concealment.

M6 — Core content pack (SRD)
- Races (passive effects for traits)
  - [ ] Human, Dwarf (+ stonecunning, vs poison/spells, armor speed), Elf (LLV, weapon profs, vs enchantments, secret door check), Gnome, Halfling, Half-Elf, Half-Orc
- Classes
  - [ ] Fighter (bonus feats)
  - [ ] Cleric (alignment/deity; spells/day; domains; spontaneous cure/inflict; turn/rebuke undead)
  - [ ] Sorcerer (spells known/day; familiar stub)
  - [ ] Monk (AC bonus, unarmed, flurry, evasion, fast movement)
  - [ ] Crusader (maneuvers known/readied, granted-refresh cycle, steely resolve, furious counterstrike, smite)
  - [ ] Totemist (soulmelds shaped, essentia pool, totem bind, rebind)
- Feats
  - [ ] Power Attack (per-round choice, two-handed scaling)
  - [ ] Blind-Fight (reroll miss chance; melee vs invisible handling; speed penalty halved when blind)
  - [ ] Augment Summoning (+4 Str/Con on summons)
  - [ ] Law Devotion (+attack/+AC 1 min; turn-attempt conversions)
  - [ ] Luck Devotion (raise low damage to half max; turn-attempt conversions)
  - [ ] Maximize Spell (slot +3; max variable numeric effects)
- Spells
  - [ ] Grease (square zone)
  - [ ] Divine Power (+6 Str enh, BAB=min level, temp HP/CL)
  - [ ] Luminous Armor (breastplate AC, light aura, -4 melee attack penalty to attackers, Str damage cost)
  - [ ] Battletide (party debuff; haste-like benefits; ends if no enemy affected)
  - [ ] Arcane Spellsurge (casting time reduction; interactions noted)
  - [ ] Conjure Ice Beast I (summon construct with template; no fire subtype)
- Conditions (full catalog)
  - [ ] Blinded, Deafened, Prone, Stunned, Dazed, Fatigued/Exhausted, Nauseated/Sickened, Entangled, Frightened/Shaken/Panicked, Paralyzed, Petrified, Confused, Disabled/Dying/Stable, Invisible, Energy Drained, etc.
- Items/Materials
  - [ ] Basic weapons/armor/shields; ammo; silver/cold-iron/adamantine materials; holy symbol; light sources
- Tasks (downtime)
  - [ ] Rest 8h; Prepare spells
  - [ ] Craft (RAW weekly progress)
  - [ ] Profession (earn gp/week)
  - [ ] Research (days, DCs)
  - [ ] Scribe Scroll / Craft Wondrous (time, gp/xp, prereqs)

Acceptance: A level-1 Cleric and Fighter can adventure, cast/attack, travel, and rest. Crusader & Totemist minimal loops function.

M7 — Exploration/Travel systems
- [ ] Travel pacing (fast/normal/slow), encumbrance, terrain/weather modifiers
- [ ] Forced march → Fatigue/Exhausted (conditions)
- [ ] Foraging & navigation (Survival)
- [ ] Stealth/watch loop (group Stealth vs Perception; applies surprise at encounter start)
- [ ] Random encounter tables by biome/time/weather; cadence (per hour); transition to Encounter mode
- [ ] Tracking (Survival DC by terrain/time), scent/blindsense/blindsight hooks

Acceptance: Can travel for hours with light consumption, random encounter checks, stealth detection, and surprise initialization.

M8 — AI (baseline)
- [ ] Brute: melee focus, Power Attack when safe, target lowest AC
- [ ] Skirmisher: ranged focus + 5-ft step/backpedal
- [ ] Caster: opener control (grease/hold/web not all implemented, but grease+buffs), conserve slots, target low saves
- [ ] Morale: retreat under 25% HP when outmatched

Acceptance: 2–4 enemy archetypes present reasonable behavior.

M9 — TUI/UX polish
- [ ] Three-column layout refined:
  - Left: Stats (HP, AC, saves, attacks, initiative), active effects & durations
  - Center: Log with colors + Explain panel toggle for last action
  - Right: Tabbed Inventory | Spells/Prepared | Feats | Conditions | Resources
- [ ] Command input with history and basic autocomplete
- [ ] Mode/time indicators (encounter/exploration/downtime; clock)
- [ ] Commands (mode-aware):
  - [ ] Encounter: move, 5-foot, attack, powerattack N, cast, activate, initiate maneuver, end turn, explain
  - [ ] Exploration: travel, search, scout, hide, forage, track, wait/camp
  - [ ] Downtime: rest, prepare, start craft, work N days/weeks (take10|take20), research, scribe
- [ ] Explain last: detailed rolls, stacking breakdown, damage pipeline, durations started
- [ ] Hot reload of content (watchdog) with safe re-render

Acceptance: Usable TUI with discoverable commands and clear state. Explain traces visible and scrollable.

M10 — Save/Load, packaging, docs
- [ ] Save/load JSON with version & migrations
- [ ] Autosave on quit; quicksave/quickload commands
- [ ] Packaging: PyInstaller single-file binaries (Win/macOS/Linux) + content folder
- [ ] CLI fallback mode (no TUI) for headless usage (simple REPL)
- [ ] README (play instructions), Content Authoring Guide (schemas + examples), Engine Policies (DR policy, rounding, SR once per target, etc.)
- [ ] License/OGL SRD notes + content provenance

Acceptance: Users can download a binary, run the game, play a session, save/load, and read docs to add content.

Testing & QA (continuous across milestones)
- Unit tests
  - [ ] Stacking rules (typed vs untyped; same-sourceKey)
  - [ ] Gates ordering & SR-once semantics
  - [ ] Damage pipeline correctness, DR negates injury riders
  - [ ] Antimagic suppression (Su/Sp/Spell), Ex persists
  - [ ] Encounter boundaries reset and cleanup
  - [ ] Rest/prep windows vs interrupts
- Property tests
  - [ ] “DR never increases damage”
  - [ ] “Temp HP never increases max HP”
  - [ ] “Dodge stacks; enhancement does not”
  - [ ] “SR checked once per use per target”
- Scenario tests
  - [ ] Fighter vs Goblin with DR 5/silver; Power Attack math
  - [ ] Grease zone: saves each round; Balance DC to move
  - [ ] Divine Power: BAB floor, +6 Str, temp HP ticks, duration expiry
  - [ ] Travel hour: light burn, random encounter, stealth vs perception → surprise
  - [ ] Craft 2 weeks (take 10): progress & completion

Post-1.0 nice-to-haves (backlog)
- Map rendering (mini ASCII map) and fog of war
- Advanced combat maneuvers (trip, grapple, disarm, bull rush)
- Concentration checks and casting defensively
- More spells and ToB disciplines; more Incarnum soulmelds
- NPC dialog scaffolding and quest/task chains
- Discord bot interface; web UI (reusing engine)
- Mod manager for content packs


## References: 
/docs/D&D 3.5e Effects and State Specification.txt
/docs/D&D 3.5e Text RPG Game Spec.txt
