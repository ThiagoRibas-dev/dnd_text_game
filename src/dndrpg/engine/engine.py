import random
from ..util.paths import content_dir
from .state import GameState, default_state
from .expr import expr_cache_info
from .loader import load_content, ContentIndex
from .campaigns import CampaignDefinition
from .models import Entity
from .save import save_game, load_game, list_saves, latest_save
from .effects_runtime import EffectsEngine
from .resources_runtime import ResourceEngine
from .conditions_runtime import ConditionsEngine
from .modifiers_runtime import ModifiersEngine
from .rulehooks_runtime import RuleHooksRegistry
from .damage_runtime import DamageEngine
from .zones_runtime import ZoneEngine
from .schema_models import EffectDefinition, Operation, Gates, AttackGate
from .settings import load_settings, Settings # Import settings

ENGINE_VERSION = "0.1.0"

class GameEngine:
    def __init__(self):
        self.content_dir = content_dir()
        self.content: ContentIndex = load_content(self.content_dir)
        self.campaign: CampaignDefinition | None = None
        self.state: GameState = default_state(self.content)
        self.resources = ResourceEngine(self.content, self.state)
        self.conditions = ConditionsEngine(self.content, self.state)
        self.damage = DamageEngine(self.content, self.state)
        self.modifiers = ModifiersEngine(self.content, self.state)
        self.hooks = RuleHooksRegistry(self.content, self.state, None, self.conditions, self.resources)  # temporary None; rebind below
        self.zones = ZoneEngine(self.content, self.state, self.hooks)
        self.settings: Settings = load_settings() # Load settings
        self.rng = random.Random(self._get_rng_seed()) # Use seed from settings
        self.effects = EffectsEngine(self.content, self.state,
                                     resources=self.resources,
                                     conditions=self.conditions,
                                     hooks=self.hooks,
                                     damage=self.damage,
                                     zones=self.zones,
                                     modifiers=self.modifiers,
                                     rng=self.rng)
        # rebind effects in hooks
        self.hooks.effects = self.effects
        self.slot_id: str | None = None
        self.should_quit: bool = False

    def _get_rng_seed(self) -> int:
        if self.settings.rng_seed_mode == "random":
            return random.randint(0, 2**32 - 1)
        elif self.settings.rng_seed_mode == "session":
            return int(self.state.clock_seconds) # Use current time as seed for session
        return 1337 # Fixed seed for "fixed" mode

    def start_new_game(self, camp_id: str, entity: Entity, slot_id: str = "slot1") -> list[str]:
        self.campaign = self.content.campaigns[camp_id]
        self.state = GameState(player=entity)
        self.slot_id = slot_id
        save_game(slot_id, self.campaign.id, ENGINE_VERSION, self.state, description=entity.name)
        return [f"New game started in campaign: {self.campaign.name}", f"Character: {entity.name}"]

    def continue_latest(self) -> list[str]:
        meta = latest_save()
        if not meta:
            return ["No saves found."]
        self.slot_id = meta.slot_id
        self.state = load_game(meta.slot_id, GameState)
        self.campaign = self.content.campaigns.get(meta.campaign_id)
        # Re-seed RNG from loaded state
        if meta.rng_seed is not None:
            self.rng.seed(meta.rng_seed)
        return [f"Loaded latest save: {meta.slot_id} ({meta.description})"]

    def load_slot(self, slot_id: str) -> list[str]:
        try:
            self.state = load_game(slot_id, GameState)
            md = next((m for m in list_saves() if m.slot_id == slot_id), None)
            if not md:
                return [f"Error: Save slot '{slot_id}' not found in metadata."]
            self.campaign = self.content.campaigns.get(md.campaign_id)
            self.slot_id = slot_id
            # Re-seed RNG from loaded state
            if md.rng_seed is not None:
                self.rng.seed(md.rng_seed)
            return [f"Loaded save: {slot_id}"]
        except Exception as e:
            return [f"Error loading save slot '{slot_id}': {e}"]

    def save_current(self) -> list[str]:
        if not self.slot_id or not self.campaign:
            return ["No active slot/campaign."]
        save_game(self.slot_id, self.campaign.id, ENGINE_VERSION, self.state, description=self.state.player.name)
        return ["Game saved."]

    def attack(self, actor: Entity, target: Entity) -> list[str]:
        logs: list[str] = []
        weapon = actor.equipped_main_weapon()
        if not weapon:
            logs.append(f"{actor.name} is not wielding a weapon.")
            return logs

        # Create a temporary effect definition for the attack
        attack_effect = EffectDefinition(
            id="attack.runtime.weapon",
            name=f"Attack with {weapon.name}",
            abilityType="Ex",
            gates=Gates(attack=AttackGate(type="melee")),
            operations=[
                Operation(
                    op="damage",
                    amount=weapon.damage,
                    damage_type=weapon.damage_type,
                )
            ]
        )

        # Temporarily add it to content
        self.content.effects[attack_effect.id] = attack_effect

        # Call attach
        logs.extend(self.effects.attach(attack_effect.id, actor, target))

        # Remove from content
        del self.content.effects[attack_effect.id]

        return logs

    def execute(self, cmd: str) -> list[str]:
        c = cmd.lower().strip()
        out: list[str] = []
        if c in ("help","?"):
            out.append("Commands: status, inventory, resources, conditions, list effects, cast <effect_id>, next (advance 1 round), attack <target>, quit")
        elif c == "expr stats":
            out.append(expr_cache_info())
        elif c == "conditions":
            lst = self.conditions.list_for_entity(self.state.player.id)
            if not lst:
                out.append("No active conditions.")
            else:
                for inst in lst:
                    dr = inst.duration_type
                    if inst.remaining_rounds is not None:
                        dr += f" {inst.remaining_rounds} rounds"
                    out.append(f"- {inst.name} [{dr}]")
        elif c == "next":
            # startOfTurn for player
            out += self.hooks.scheduler_event(self.state.player.id, "startOfTurn")
            # tick conditions/resources per-round
            out += self.conditions.tick_round()
            out += self.effects.tick_round()
            self.resources.refresh_cadence("per_round")
            out += self.zones.tick_round()
            # endOfTurn
            out += self.hooks.scheduler_event(self.state.player.id, "endOfTurn")
        elif c.startswith("status"):
            p = self.state.player
            out.append(f"{p.name} | HP {p.hp_current}/{p.hp_max} AC {p.ac_total} (T{p.ac_touch}/FF{p.ac_ff}) | Melee +{p.attack_melee_bonus}")
        elif c.startswith("inventory"):
            names = [it.name for it in self.state.player.inventory]
            out.append("Inventory: " + (", ".join(names) if names else "(empty)"))
        elif c.startswith("list effects"):
            lst = self.effects.list_for_entity(self.state.player.id)
            if not lst:
                out.append("No active effects.")
            else:
                for inst in lst:
                    dr = f"{inst.duration_type}"
                    if inst.remaining_rounds is not None:
                        dr += f" {inst.remaining_rounds} rounds"
                    sup = " [suppressed]" if inst.suppressed else ""
                    out.append(f"- {inst.name}{sup} [{dr}] (id={inst.instance_id})")
        elif c.startswith("cast "):
            _, _, eff_id = cmd.partition(" ")
            eff_id = eff_id.strip()
            if not eff_id:
                out.append("Usage: cast <effect_id> (e.g., cast spell.divine_power)")
            else:
                out += self.effects.attach(eff_id, self.state.player, self.state.player)
        elif c.startswith("attack "):
            _, _, target_name = cmd.partition(" ")
            target_name = target_name.strip()
            if not target_name:
                out.append("Who do you want to attack? (e.g., attack goblin)")
            else:
                target = None
                for npc in self.state.npcs:
                    if npc.name.lower().startswith(target_name.lower()):
                        target = npc
                        break
                
                if not target:
                    out.append(f"Target not found: {target_name}")
                else:
                    out.extend(self.attack(self.state.player, target))
        elif c.startswith("rest"):
            out.append("You rest. (stub)")
        elif c.startswith("travel"):
            out.append("You travel. (stub)")
        elif c.startswith("save"):
            out.append(self.save_current()[0])
        elif c.startswith("resources"):
            info = self.state.resources_summary()
            if not info:
                out.append("No resources.")
            else:
                for k, v in info.items():
                    out.append(f"{k}: {v}")
        elif c.startswith("explain"):
            if not self.state.last_trace:
                out.append("(no trace recorded)")
            else:
                out.extend(self.state.last_trace)
        elif c in ("quit", "exit"):
            self.should_quit = True
            out.append("Exiting...")
        else:
            out.append(f"Unknown command: {cmd}")
        return out