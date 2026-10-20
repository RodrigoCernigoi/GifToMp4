from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class JobStatus(Enum):
    PENDING = "Pendente"
    RUNNING = "Convertendo"
    SUCCEEDED = "Concluído"
    FAILED = "Falhou"
    SKIPPED = "Ignorado"


@dataclass(frozen=True)
class ConversionJob:
    source: Path
    destination: Path


@dataclass(frozen=True)
class ConversionEvent:
    source: Path
    status: JobStatus
    message: str
