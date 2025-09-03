# TODO List from Code Review

## Top-priority blockers (crashers or guaranteed breakage)

- [x] 1. `TypeError: build_entity_from_state() missing 1 required positional argument: 'campaign_id'`
- [ ] 2. `EffectsEngine.execute_operations` only handles damage
- [ ] 3. `EffectsEngine._snapshot_duration_rounds` is incompatible with `DurationSpec`
- [ ] 4. `RuleHooksRegistry` uses fields that `RegisteredHook` doesn’t define and references a missing `_is_parent_suppressed`
- [ ] 5. Loader doesn’t load zones (but the engine expects them)
- [ ] 6. Attack flow builds invalid damage operation and has no dice handling
- [ ] 7. `GameEngine.start_new_game` replaces state but doesn’t rebind engines
- [ ] 8. `GameState` lacks fields you use (“mode”, “clock_seconds”, “rng_seed”)
- [ ] 9. TargetPath registry mismatch vs schema and tests

## Medium-priority correctness gaps (rules/UX)

- [ ] 10. Cleric deity/domains schema mismatch
- [ ] 11. Domain content is not a valid `EffectDefinition`
- [ ] 12. CampaignDefinition vs YAML
- [ ] 13. Skills UX and math
- [ ] 14. Feat prerequisites are never enforced in UI
- [ ] 15. ValidateCharacter picks uses “first campaign” instead of selected campaign
- [ ] 16. Cleric prepared spells and slots
- [ ] 17. RNG determinism and persistence
- [ ] 18. Save/load engines
- [ ] 19. Zone suppression and antimagic

## Code quality and consistency

- [ ] 20. Duplicate initializer code in `EffectsEngine.__init__`
- [ ] 21. Two registries for target paths
- [ ] 22. DamageEngine entity lookup
- [x] 22. Logging
- [x] 23. UI issues
- [x] 24. Validation tooling vs runtime

## Tests

- [x] 25. `tests/test_resources.py` assumes a different `GameState` and `ContentIndex` shape
- [x] 26. `tests/test_schema_models.py` vs your registry
- [x] 27. `tests/test_smoke.py` temp HP resource

## Content fixes (quick wins)

- [x] 28. Update campaign YAML to use `wealth: { mode: kits }` not `starting_gold_policy`.
- [x] 29. Update deity YAML to `allowed_domains` + `allowed_alignments`.
- [x] 30. Convert domain files to valid “domain.<name>.grant” effect stubs.
- [x] 31. Ensure Grease zone is actually created via `zone.create`.
- [x] 32. Consider adding “it.torch” and light sources and tie them into M5 light/vision when you get there.

## Small diffs for bugs already visible

- [x] 34. `EffectsEngine.__init__` remove duplicate assignments.
- [x] 35. `StepSummary`: replace `self.app_ref.log.push` with `log_panel`.
- [x] 36. `StepWealthShop`: use selected campaign id (self.app_ref.engine.campaign.id) for `GameEngine.start_new_game`
- [x] 37. `StepSkills`: fix class skill name matching (lowercase both sides).