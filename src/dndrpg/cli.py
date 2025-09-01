import typer
from dndrpg.engine.engine import GameEngine
from dndrpg.engine.chargen import CharBuildState, build_entity_from_state
from dndrpg.engine.save import delete_save

app = typer.Typer()

@app.command()
def new(campaign_id: str = "camp.srd_sandbox", name: str = "Hero", clazz: str = "fighter", race: str = "human"):
    eng = GameEngine()
    picks = CharBuildState(name=name, clazz=clazz, race=race)
    # minimal set
    build_entity_from_state(eng.content, eng.state, picks, eng.effects, eng.resources, eng.conditions, eng.hooks)
    for line in eng.start_new_game(campaign_id, eng.state.player, slot_id="slot1"):
        typer.echo(line)

@app.command()
def continue_latest():
    eng = GameEngine()
    for line in eng.continue_latest():
        typer.echo(line)

@app.command()
def load(slot_id: str):
    eng = GameEngine()
    for line in eng.load_slot(slot_id):
        typer.echo(line)

@app.command()
def delete(slot_id: str):
    delete_save(slot_id)
    typer.echo(f"Deleted save: {slot_id}")

@app.command()
def create_character():
    typer.echo("Starting character creation wizard (CLI)...")
    name = typer.prompt("Enter character name", default="Hero")
    alignment = typer.prompt("Enter alignment (e.g., lawful good)", default="neutral")
    race = typer.prompt("Enter race (e.g., human)", default="human")
    clazz = typer.prompt("Enter class (e.g., fighter)", default="fighter")

    # Simplified ability score generation for CLI
    typer.echo("Enter ability scores (STR, DEX, CON, INT, WIS, CHA) separated by spaces:")
    scores_input = typer.prompt("e.g., 15 14 13 12 10 8", default="15 14 13 12 10 8")
    scores_list = [int(s.strip()) for s in scores_input.split()]
    abilities_dict = {"str": scores_list[0], "dex": scores_list[1], "con": scores_list[2],
                      "int": scores_list[3], "wis": scores_list[4], "cha": scores_list[5]}

    picks = CharBuildState(name=name, alignment=alignment, race=race, clazz=clazz, abilities=abilities_dict)

    eng = GameEngine()
    build_entity_from_state(eng.content, eng.state, picks, eng.effects, eng.resources, eng.conditions, eng.hooks)
    
    typer.echo("Character created successfully!")
    typer.echo(f"Name: {eng.state.player.name}")
    typer.echo(f"Class: {eng.state.player.classes}")
    typer.echo(f"Abilities: {eng.state.player.abilities}")


if __name__ == "__main__":
    app()