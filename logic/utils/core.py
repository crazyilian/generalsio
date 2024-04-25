from typing import List
from base.base.bot_base import GeneralsBot
from base.base.client.map import Map
from base.base.client.tile import Tile


class GameGlobals:
    bot: GeneralsBot = None
    gamemap: Map = None
    self: int = None
    enemy: int = None
    my_general: Tile = None
    H: int = None
    W: int = None
    phase: int = None
    planned_moves: dict = None
    my_general_exposed: bool = None
    verts_closer_than: dict = None
    attack_phase_start_turn: int = None
    queue = None
    urgent_queue = None

    my_cities: list = None
    captured_cities: list = None
    cities: list = None
    side_graph: List[List[int]] = None
    side_graph_cities: List[List[int]] = None
    dists_from_general: List[int] = None
    dists_from_general_cities: List[int] = None
    enemy_general: Tile = None
    maybe_generals: List[Tile] = None
    armies: List[int] = None

    def clear(self):
        for attr in dir(self):
            if not callable(getattr(self, attr)) and not attr.startswith("__"):
                setattr(self, attr, None)


def tile2vert(tile):
    return tile.y * GG.W + tile.x


def vert2tile(v):
    return GG.gamemap.grid[v // GG.W][v % GG.W]


def manhattan(tile1, tile2):
    if isinstance(tile1, int):
        tile1 = vert2tile(tile1)
    if isinstance(tile2, int):
        tile2 = vert2tile(tile2)
    return abs(tile1.y - tile2.y) + abs(tile1.x - tile2.x)


GG = GameGlobals()
