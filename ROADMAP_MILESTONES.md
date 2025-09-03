## v1.0 Roadmap (milestones)

M0 — Boot flow: Campaigns, Saves, Character Creation [x]
- [x] Title screen & boot flow
  - [x] Title screen (Textual screen): New Game, Continue, Load Game, Delete Save, Settings, Quit
  - [x] “Continue” loads most recent save; “Load” shows save list with metadata (campaign, party, in-game time)
  - [x] Save slot folder structure: saves/<slot-id>/save.json (+ meta.json, replay seed, optional screenshots)
  - [x] Save index (saves/index.json) with versioning and last-played timestamps
  - [x] Engine version and content pack hashes recorded for migration checks
- [x] CampaignDefinition content
  - [x] Content schema + loader for campaigns (campaigns/*.yaml)
  - [x] Fields: id, name, description, start_area, start_coords, start_time, start_level, allowed_races/classes/feats, starting_gold_policy, starting_equipment_packs, random_encounter_tables, rest_rules, houserules (toggles)
  - [x] Default campaign: “SRD Sandbox”
- [x] Character Creation (wizard)
  - [x] Ability scores: choose method (4d6 drop lowest, point-buy 25/28/32, standard array)
  - [x] Race (with subrace), alignment (gated by class), deity (optional), domains (for cleric)
  - [x] Class/level 1: class pick (Fighter/Cleric/Sorcerer/Monk; later Crusader/Totemist), HP rule (max at 1st), BAB/saves bases
  - [x] Skills: skill ranks allocation (auto-calc class/cross-class costs; human bonus; INT mod)
  - [ ] Feats: pick by level/race/class; prerequisites validation
  - [x] Spells:
    - [x] Cleric: pick domains; prepared spells (domain slots auto); spontaneous cure/inflict flag
    - [x] Sorcerer: spells known; per-day slots computed
    - [x] Wizard (later): spellbook contents + prepared list
  - [x] Starting wealth:
    - [x] Option A: class kits (from content) or Option B: roll class gold and shop
  - [x] Equipment: pick from kits or purchase; auto-equip reasonable defaults
  - [x] Summary screen with validation (encumbrance, illegal combos) -> confirm and start
  - [x] Output: fully-built Entity + initial GameState seeded to campaign start
- [x] CLI fallback (no TUI)
  - [x] Commands: new, continue, load <slot>, delete <slot>, create-character (wizard in prompts)

Acceptance: From the title screen, you can New Game -> choose SRD Sandbox -> build a level 1 character -> spawn into world; Continue/Load works with save slots; saves record campaign id/version.

M1 — Project foundation and core models
- [x] Repo bootstrap finalized (pyproject, src layout, tests, CI)
- [x] Pydantic models: Entity, GameState, Item, Weapon, Armor
- [x] Core stats and derived stats:
  - [x] Abilities (base, temp, damage, drain)
  - [x] AC breakdown (armor, shield, natural, deflection, dodge, size, misc)
  - [x] Saves (base, ability mod, misc), initiative
  - [x] Attack bonuses (melee/ranged/touch), crit profile (range/multiplier)
- [x] Content loader (JSON/YAML) + content folder
- [x] Expression engine wrapper + functions: ability_mod, level/class_level, caster_level, initiator_level, HD, min/max/floor/ceil
- [x] JSON Schemas: EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
- [ ] Deterministic RNG (seed per encounter; include seed in explain logs)
- [ ] Basic unit test harness (pytest + hypothesis)
- [x] JSON Schemas (Items)
  - [x] Export JSON Schemas for Item, Weapon, Armor, Shield (Pydantic v2 .model_json_schema) to docs/schemas/
  - [x] CLI: validate-content (loads all content files, validates against schemas)
  - [x] CI: run validate-content on PRs; fail on schema or parse errors
  - [x] Pre-commit hook: run validate-content on changed files  
- [ ] Schema hardening & content lints
  - [x] Operations: switch from free-form params to a discriminated union
    - [x] Define op kinds (damage, heal, condition.apply/remove, resource.create/spend/restore, zone.create, save, attach/detach, move/teleport, transform, dispel/suppress, schedule, etc.)
    - [x] Per-op required/optional fields (e.g., damage: amount, type; save: type, dc, onSuccess/onFail actions)
  - [x] RuleHook.action: typed action union
    - [x] Actions (modify, reroll, cap, multiply, reflect/redirect, absorbIntoPool, setOutcome, save, condition.apply/remove, resource.*, schedule)
    - [x] Validate allowed actions per hook scope
  - [x] EffectDefinition tightening
    - [x] range.type == "fixed-ft" -> require distance_ft
    - [x] area.shape constraints (require size_ft or radius_ft/length_ft/width_ft as appropriate)
    - [x] duration rules (non-instant effects must have duration; concentration needs concentration:true)
    - [x] gates consistency (attack.ac_type required for touch/flat-footed modes; sr applies only to Spell/Sp)
    - [x] stacking policy shape (named:no_stack_highest|latest, sameSource, bonusType policy) validated
  - [x] Modifier constraints
    - [x] targetPath allowlist prefixes (abilities.*, ac.*, save.*, resist.*, dr.*, speed.*, senses.*, tags.*, resources.*)
    - [x] Require bonusType for additive stat bonuses where applicable; forbid invalid operator+target combos
    - [x] Deprecate replaceFormula; prefer set or replace with typed fields
  - [x] ConditionDefinition tightening
    - [x] tags enum (blinded, stunned, prone, etc.); precedence unique; default_duration must be allowed combos
  - [x] ResourceDefinition tightening
    - [x] capacity.formula required; capacity.cap >= 0
    - [x] refresh.behavior == "increment_by" -> require increment_by
    - [x] absorption.absorbTypes enum; absorbPerHit >= 0; absorbOrder enum
    - [x] freezeOnAttach boolean; scope enum enforced
  - [x] TaskDefinition tightening
    - [x] timeUnit ∈ {minutes,hours,days,weeks}; step > 0
    - [x] hooks limited to scope == "scheduler"; must specify events (eachStep, onStart, onComplete)
    - [x] progress/completion required shape; costs resource kinds enum (gp,xp,resource:<id>)
  - [x] ZoneDefinition tightening
    - [x] shape != none; duration rules (instant vs timed); hooks scopes limited to on-enter/on-leave/scheduler/incoming.effect
    - [x] suppression fields enum (antimagic, spell_globe:<=N, etc.)
  - [x] Expression prevalidation
    - [x] Parse all Expr fields at load; allowlist functions (min, max, floor, ceil, ability_mod, level, class_level, caster_level, initiator_level, hd)
    - [x] Unknown symbols/functions produce validation errors under --strict-expr
  - [x] Cross-reference validation
    - [x] Verify references exist: condition ids, resource ids, zone ids, item ids, kit ids, effect ids
    - [x] Warn on unused content ids
  - [x] ID policy & versioning
    - [x] Enforce id regex ^[a-z0-9_.:-]+$ and namespace prefixes (spell., feat., cond., res., zone., task., kit., item.)
    - [x] schema_version in files; migration hooks documented
  - [x] CLI & CI
    - [x] dndrpg-tools validate-content --strict (expr + refs + typing) in CI
    - [x] Lint output with warnings vs errors; fail on errors only

Acceptance: Can load a player, stats compute correctly, content files validate, and tests run green.

M2 — Effects/State engine (definitions -> instances)
- [x] EffectDefinition/EffectInstance implemented (blueprint vs runtime)
- [x] ResourceDefinition/ResourceState implemented (capacity formulas, refresh cadence)
- [x] ConditionDefinition/ConditionInstance implemented
- [x] Modifiers engine with stacking rules:
  - [x] Typed bonuses (enhancement, morale, luck, insight, competence, sacred, profane, resistance, deflection, dodge, size, natural armor)
  - [x] Unnamed bonuses + same-sourceKey non-stacking
  - [x] Operator ordering: set/replace -> add/sub (stacking) -> mul/div -> min/max -> cap/clamp
- [x] Rule hooks registry (incoming.effect, on.attack pre/post, on.save pre/post, scheduler ticks, incoming.damage)
- [x] Operations: damage/heal (HP/nonlethal/ability dmg/drain), apply/remove condition, (create/spend/restore) resource, attach/detach effects, create zone
- [x] Antimagic/suppression flags per abilityType (Ex/Su/Sp/Spell)
- [x] Expression compilation cache
  - [x] Precompile expressions to AST on load; cache by string
  - [x] Benchmark: ensure eval hot paths (damage, saves) avoid re-parsing
- [x] TargetPath registry
  - [x] Central registry with metadata (type, allowed ops, requires bonusType?) used by schema and runtime checks

Acceptance: Can attach a self-buff with typed modifiers and a timed duration; modifiers apply and expire correctly; untyped same-source does not stack.

M3 — Gates and damage pipeline
- [x] Gates per target:
  - [x] SR gate (one CL check per target per use; SR:Yes only)
  - [x] Save gate (Fort/Ref/Will, DC expressions, branch policies: negates/half/partial/none)
  - [x] Attack gate (melee/ranged/touch/ray; crit confirm; concealment/miss chance)
- [x] Damage pipeline:
  - [x] 1) Immunity -> 2) Type conversion -> 3) Resist/DR/ablative pools -> 4) Vulnerability -> 5) Apply to HP/THP -> 6) Injury rider negation (if DR reduced to 0) -> 7) Post hooks
  - [x] DR policy: apply to total physical damage per attack (documented)
  - [x] Energy resist per packet, vulnerabilities, Temp HP before HP
- [x] Explain/trace for last action (rolls, stacking, damage breakdown)

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
- [ ] Campaigns & kits
  - [ ] CampaignDefinition: “SRD Sandbox” with permissive allowed lists and default encounter tables
  - [ ] Starting equipment packs per class (fighter/cleric/sorcerer/monk): item lists + auto-equip mapping
  - [ ] Point-buy presets (25, 28, 32) and Standard Array (15,14,13,12,10,8) as content toggles
  - [ ] Default deities/domains (minimal SRD subset for cleric flow)
- [ ] Premade characters (optional)
  - [ ] Sample premades (.yaml) to speed testing: Human Fighter 1, Human Cleric 1, Elf Sorcerer 1, Human Monk 1
- [ ] Content conformance tests
  - [ ] Unit tests: sample effects/conditions/resources validate under strict schema
  - [ ] Property tests: all content in pack parses; no unknown descriptors/tags; all refs resolve
  - [ ] Snapshot tests for a few complex effects (Grease, Divine Power, Battletide) against the strict schema

Acceptance: A level-1 Cleric and Fighter can adventure, cast/attack, travel, and rest. Crusader & Totemist minimal loops function.

M7 — Exploration/Travel systems
- [ ] Travel pacing (fast/normal/slow), encumbrance, terrain/weather modifiers
- [ ] Forced march -> Fatigue/Exhausted (conditions)
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
- [ ] Content hot-reload
  - [ ] File watcher (watchdog) on content/; on change -> reparse into ContentIndex; log added/updated/removed ids
  - [ ] Manual command: reload content (forces a full rescan)
  - [ ] Toggle command: content watch on/off
  - [ ] Safety policy: existing entities keep deep-copied items; only new clones use updated definitions (log when diverging)
  - [ ] UI: flash a brief “Content reloaded (N updated, M added, K removed)” notice in log
- [ ] Equip/Unequip commands
  - [ ] Commands: equip <id|name>, unequip <slot|name>; auto-resolve slot (armor/shield/main_hand/off_hand/ranged)
  - [ ] Auto-unequip conflicting item in slot; update derived stats immediately
  - [ ] UI Right panel: add Equipped section (Armor, Shield, Main Hand, Off Hand, Ranged); highlight items currently equipped
  - [ ] Help: include equip/unequip examples; error messages for unknown ids/illegal slots
- [ ] Multi-screen flow
  - [ ] Screen: Title (New/Continue/Load/Delete/Settings)
  - [ ] Screen: Campaign select (list from content/campaigns)
  - [ ] Screens: Character Creation steps (Back/Next, summary, validation)
  - [ ] Screen: Load/Manage Saves (list with sort; delete confirmation)
  - [ ] Settings: rules toggles (point-buy value, hp at level 1, rest rules), keybinds, content pack selection
- [ ] Character creation UX details
  - [ ] Point-buy calculator with live total and ability mods
  - [ ] Prereq validation with inline hints (why a feat/class choice is invalid)
  - [ ] Autocomplete search for feats/spells
  - [ ] “Recommend” button for reasonable defaults per class
  - [ ] Summary diff: show AC/HP/attacks/saves as you change equipment

Acceptance: Usable TUI with discoverable commands and clear state. Explain traces visible and scrollable.

M10 — Save/Load, packaging, docs
- [ ] Save/load JSON with version & migrations
- [ ] Autosave on quit; quicksave/quickload commands
- [ ] Packaging: PyInstaller single-file binaries (Win/macOS/Linux) + content folder
- [ ] CLI fallback mode (no TUI) for headless usage (simple REPL)
- [ ] README (play instructions), Content Authoring Guide (schemas + examples), Engine Policies (DR policy, rounding, SR once per target, etc.)
- [ ] License/OGL SRD notes + content provenance
- [ ] Save format & migration
  - [ ] save.json includes: engine_version, content_hashes, campaign_id, game_clock, mode, RNG seeds, all entities (PC/NPC), zones, scheduler queue, map position, tasks
  - [ ] Migration: simple version gate; warn if content pack mismatch; attempt non-breaking field defaults
  - [ ] Quicksave/Quickload keybinds; autosave on zone enter/exit and on quit
- [ ] Docs
  - [ ] Campaign authoring guide (CampaignDefinition schema + examples)
  - [ ] Character creation checklist (how choices map to EffectDefinitions and entity fields)
  - [ ] Save data spec and compatibility policy
- [ ] Schema docs generation
  - [ ] Export JSON Schemas + human docs (mkdocs) with examples
  - [ ] Generate TypeScript types (quicktype) for external tooling
- [ ] Authoring lints
  - [ ] dndrpg-tools lint: conventions (id prefixes, bonusType required, area/range/duration combos), common mistakes (e.g., dodge stacking misuse)
  - [ ] --fix option for simple rewrites (rename fields, normalize shapes)

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
  - [ ] Travel hour: light burn, random encounter, stealth vs perception -> surprise
  - [ ] Craft 2 weeks (take 10): progress & completion

## Post-1.0 nice-to-haves (backlog)
- Map rendering (mini ASCII map) and fog of war
- Advanced combat maneuvers (trip, grapple, disarm, bull rush)
- Concentration checks and casting defensively
- More spells and ToB disciplines; more Incarnum soulmelds; Binding; Shadowcasting; Truenaming; Invocations; Auras (Dragon Shaman and Marshal)
- NPC dialog scaffolding and quest/task chains
- World State
- Mod manager for content packs
- AI Integration