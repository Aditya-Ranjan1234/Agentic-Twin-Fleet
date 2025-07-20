"""Abstract base class for all agents."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Common interface for agents."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def observe(self, data: Dict[str, Any]):
        """Consume an observation (vehicle telemetry, twin state, etc.)."""

    @abstractmethod
    def decide(self):
        """Make a decision based on internal state. Should set self._decision.
        Returns the decision object (dict).
        """

    @abstractmethod
    def act(self, decision: Dict[str, Any]):
        """Execute / publish the decision."""
