"""Version-one execution boundary, independent of any framework or storage engine."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ContextManager, Protocol

from .errors import AdapterError


class Capability(str, Enum):
    """Independent operations; model support is never required for behavioral grading."""

    HTTP = "http"
    OFFLINE = "offline"
    INSPECT = "model-inspection"
    GENERATE = "input-generation"


@dataclass(frozen=True)
class AdapterConfig:
    """Implementation identity and capabilities, separate from scenario requirements."""

    condition: str
    language: str
    framework: str
    capabilities: frozenset[Capability]
    version: int = 1

    def __post_init__(self):
        """Refuse unknown versions and loosely coerced configuration."""
        if type(self.version) is not int or self.version != 1:
            raise AdapterError("configuration", "Unsupported adapter contract version")
        if any(
            type(x) is not str or not x
            for x in (self.condition, self.language, self.framework)
        ):
            raise AdapterError(
                "configuration",
                "Condition, language and framework must be nonempty strings",
            )
        if not isinstance(self.capabilities, frozenset) or any(
            not isinstance(x, Capability) for x in self.capabilities
        ):
            raise AdapterError(
                "configuration", "Capabilities must be explicit Capability values"
            )

    def require(self, capability: Capability) -> None:
        """Reject unsupported operations before starting any candidate process."""
        if capability not in self.capabilities:
            raise AdapterError(
                "unsupported", f"{self.condition} does not declare {capability.value}"
            )


@dataclass(frozen=True)
class ExecutionResult:
    """Successful transport observation; payload correctness belongs to the independent verifier."""

    capability: Capability
    payload: object
    version: int = 1

    def __post_init__(self):
        """Reject incompatible result envelopes before a scenario consumes the payload."""
        if (
            type(self.version) is not int
            or self.version != 1
            or not isinstance(self.capability, Capability)
        ):
            raise AdapterError("protocol", "Unsupported execution result envelope")


class Adapter(Protocol):
    """Small v1 host protocol; implementations may reject undeclared capabilities."""

    config: AdapterConfig

    def build(self, folder: Path, log=None) -> str:
        """Build checked inputs and return their build-manifest digest."""
        ...

    def start(
        self,
        folder: Path,
        output: Path,
        environment: dict[str, str],
        arguments: list[str],
    ) -> ContextManager:
        """Start a managed HTTP host; context exit owns cleanup, not the verifier."""
        ...

    def execute(
        self, folder: Path, capability: Capability, argument: str
    ) -> ExecutionResult:
        """Produce an observation or raise a classified nonbehavioral failure."""
        ...

    def observe(self, folder: Path) -> str:
        """Verify unchanged build inputs/outputs and return their evidence identity."""
        ...
