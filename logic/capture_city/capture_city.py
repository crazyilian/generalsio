from logic.utils import GG, tile2vert
from logic.army_gather import gather_army_limit


def get_capture_moves():
    best_city = None
    best_moves = []
    for tile in GG.gamemap.cities:
        v = tile2vert(tile)
        if tile.tile == GG.self or GG.dists_from_general_cities[v] is None:
            continue
        target_increase = 0.5 if tile.tile == GG.enemy else 0
        moves, collected = gather_army_limit(v, 1, [5, 10, 15, 20, 25, 30, 35], target_increase=target_increase)
        if collected < 1:
            continue
        if best_city is None or len(best_moves) > len(moves):
            best_city = v
            best_moves = moves
    return best_moves


def init():
    pass
