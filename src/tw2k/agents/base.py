"""Agent protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..engine import Action, Observation


class BaseAgent(ABC):
    name: str
    player_id: str
    kind: str = "base"

    def __init__(self, player_id: str, name: str):
        self.player_id = player_id
        self.name = name

    @abstractmethod
    async def act(self, observation: Observation) -> Action:
        """Given the current observation, return the agent's next action."""
        raise NotImplementedError

    async def close(self) -> None:
        """Called once when the match ends. Clean up any external resources."""
        return None
