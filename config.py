from dataclasses import dataclass
from typing import Dict

@dataclass
class Config:
    cell_size: int = 16
    map_width: int = 100
    map_height: int = 50
    max_layers: int = 383
    undo_limit: int = 100
    brush_min: int = 1
    brush_max: int = 10
    colors: Dict[str, str] = None

    def __post_init__(self):
        if self.colors is None:
            self.colors = {
                "WHITE": "#FFFFFF",
                "BLACK": "#000000",
                "L_GREY": "#D3D3D3",
                "GREY": "#9D9E80",
            }

    @property
    def width_px(self) -> int:
        return self.map_width * self.cell_size

    @property
    def height_px(self) -> int:
        return self.map_height * self.cell_size

CFG = Config()
EMPTY = 0