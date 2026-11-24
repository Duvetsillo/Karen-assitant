"""Domain contract for an Aetherion adapter; contains no benchmark runner or endpoints."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BenchmarkSelection:
    node: str
    node_url: str
    model: str
    # node_url is contextual metadata. The adapter must resolve an engine-authorized target.


@dataclass(frozen=True)
class BenchmarkUpdate:
    phase: str  # queued/running/completed/cancelled/failed
    progress: float | None = None  # 0..100 if supplied by the engine
    summary: str = ""


class BenchmarkGateway(Protocol):
    """Authentication and allowed targets belong to the supplied engine adapter."""
    def start(self, selection: BenchmarkSelection) -> str: ...
    def poll(self, job_id: str) -> BenchmarkUpdate: ...
    def cancel(self, job_id: str) -> None: ...
