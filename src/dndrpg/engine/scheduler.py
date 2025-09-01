from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Scheduled:
    when_round: Optional[int] = None
    when_seconds: Optional[int] = None
    target_entity_id: str = ""
    actions: list = field(default_factory=list)  # list of Operation or HookAction

class Scheduler:
    def __init__(self, state, effects, hooks):
        self.state = state
        self.effects = effects
        self.hooks = hooks
        self._queue: List[Scheduled] = []

    def schedule_in_rounds(self, target_entity_id: str, rounds: int, actions: list):
        self._queue.append(Scheduled(when_round=self.state.round_counter + max(1, rounds),
                                     target_entity_id=target_entity_id, actions=actions))

    def _drain_scheduled(self) -> List[str]:
        logs: List[str] = []
        now_round = self.state.round_counter
        due: List[Scheduled] = []
        keep: List[Scheduled] = []
        for s in self._queue:
            if s.when_round is not None and s.when_round <= now_round:
                due.append(s)
            else:
                keep.append(s)
        self._queue = keep
        # Execute due actions
        for s in due:
            for act in s.actions:
                # Delegate to effects.executor if it's an Operation; if HookAction, we can map to Operation union or extend executor to accept it
                # For MVP: only Operation union used here
                self.effects.execute_operations([act], self.state.player, self.state.player, logs=logs)
        return logs

    def advance_rounds(self, n: int = 1) -> List[str]:
        logs: List[str] = []
        for _ in range(max(0, n)):
            self.state.round_counter += 1
            self.state.clock_seconds += 6
            logs += self.hooks.scheduler_event(self.state.player.id, "startOfTurn")
            logs += self._drain_scheduled()
            # ... rest unchanged ...
        return logs
