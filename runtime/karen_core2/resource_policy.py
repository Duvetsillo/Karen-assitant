"""Small resource profiles; inference limits are not physical GPU reservations."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ResourcePolicy:
    profile: str = 'balanced'
    vram_reserve_mib: int = 1536

    def __post_init__(self):
        if self.profile not in {'economy', 'balanced', 'quality'}:
            raise ValueError('Perfil de recursos desconocido.')
        if type(self.vram_reserve_mib) is not int or not 1024 <= self.vram_reserve_mib <= 65536:
            raise ValueError('La reserva de VRAM debe ser un entero entre 1024 y 65536 MiB.')

    @classmethod
    def from_environment(cls):
        return cls(os.getenv('KAREN_RESOURCE_PROFILE', 'balanced'),
                   int(os.getenv('KAREN_VRAM_RESERVE_MIB', '1536')))

    @property
    def reserve_bytes(self):
        return self.vram_reserve_mib * 1024**2

    def context(self, kind):
        if self.profile == 'economy':
            return 2048
        return 2048 if kind in {'conversation', 'memory'} and self.profile != 'quality' else 4096

    def output_tokens(self, kind):
        limit = (512 if self.profile == 'quality' else 256) if kind == 'conversation' else 512 if kind in {'memory', 'vision'} else 1536
        return min(192, limit) if self.profile == 'economy' else limit
