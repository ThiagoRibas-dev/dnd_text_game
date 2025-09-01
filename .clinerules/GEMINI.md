# ROADMAP_MILESTONES.md

## Project Description and Game Spec Summary

The game is a single-player, text-first RPG based on D&D 3.5e rules. It will feature a grid-based combat system, exploration, and downtime activities. The core of the game is an effects and state engine, where all game mechanics (races, classes, feats, spells, etc.) are defined as content blueprints (JSON/YAML) that are instantiated at runtime.
The game is divided into three modes:
*   **Encounter Mode:** For combat, traps, and NPC interactions. It's turn-based on a grid.
*   **Exploration/Travel Mode:** For moving around the world, searching, and handling random encounters.
*   **Downtime Mode:** For longer-term tasks like crafting, resting, and preparing spells.

A central "Mode Manager" handles transitions between these states. The game will also feature a detailed command-line interface for interacting with the world, and an "explain" command to provide a detailed breakdown of the last action's resolution (dice rolls, modifiers, etc.). The engine will follow specific, documented policies for rules like damage reduction, cover, and ability stacking to ensure deterministic and predictable outcomes.

---

### Notes and Rules ###

**Coding/Development Workflow:** 
  - Examination
  - Planning (what, where, how, why), including details of implementation
  - Refining (break into components, detail, consider possibilities, brainstorm)
  - Iteration
  - Request and wait for permission to Execute/Implement
  - Execution/implementation (reading files, creating/editing/deleting, etc)
  - Run ruff to check for errors
  - Run the game to check for errors
  - Update Roadmap (ROADMAP_MILESTONES.md file)
  - Summarize changes
  - Ask for next step
Always ponder and consider the possible downstream effects of changes.

**Planning:** Before making any changes, we will perform an iterative planning step, laying out a detailed step-by-step implementation plan (what, where, how, why). Only once the plan has been accepted, we will execute the plan and edit the files in question.

**Editing Files:** Avoid trying to edit whole files at once if possible. Edit specific, directed, targeted snippets at a time, always planning the whole chain of edits beforehand. Be aware of replacing snippets that exist in multiple parts of a given file.

**Ruff Linter:** During Execution, after performing a batch of changes, always run `ruff check . --fix` to ensure things are in order.

**Running the Game:** Use the command `uv run python -m dndrpg`.

---

## References: 
ROADMAP_MILESTONES.md
/docs/D&D 3.5e Effects and State Specification.txt
/docs/D&D 3.5e Text RPG Game Spec.txt
