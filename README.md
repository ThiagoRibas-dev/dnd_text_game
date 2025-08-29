# D&D 3.5e Text RPG

## Project Overview

The game is a single-player, text-first RPG based on D&D 3.5e rules. It will feature a grid-based combat system, exploration, and downtime activities. The core of the game is an effects and state engine, where all game mechanics (races, classes, feats, spells, etc.) are defined as content blueprints (JSON/YAML) that are instantiated at runtime.

## Key Features

*   **Three Game Modes:** Encounter (combat, traps, NPC interactions), Exploration/Travel (world movement, searching, random encounters), and Downtime (crafting, resting, spell preparation).
*   **D&D 3.5e Ruleset:** Adherence to core D&D 3.5e mechanics for character creation, combat, and interactions.
*   **Content-Driven Engine:** Game mechanics defined via JSON/YAML blueprints for easy extensibility.
*   **Detailed Command-Line Interface (CLI):** Interact with the game world through a robust CLI.
*   **"Explain" Command:** Get a detailed breakdown of the last action's resolution (dice rolls, modifiers, etc.).
*   **Deterministic Outcomes:** Predictable and consistent application of game rules.

## Installation

This project requires Python 3.11 or higher.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ThiagoRibas-dev/dnd_text_game
    cd dndrpg
    ```
2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate  # On Windows
    # source .venv/bin/activate    # On macOS/Linux
    pip install -e .
    ```

## How to Play

To start the game, run the following command from the project root:

```bash
uv run python -m dndrpg
```

This will launch the Textual UI. If you prefer a CLI-only experience, the game also supports a fallback mode.

## Project Status

This project is currently under active development. Refer to the `GEMINI.md` file for the detailed roadmap and current milestones.

## Contributing

Contributions are welcome! Please refer to the `GEMINI.md` for development guidelines and the project roadmap.

## License

[License Information - e.g., MIT License]
