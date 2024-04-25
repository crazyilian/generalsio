from logic.utils import GG, tile2vert, vert2tile, manhattan
from base.base.client.constants import *


def dfs(v, graph, res, used, is_blocked):
    if v in used or is_blocked(v):
        return False
    used.add(v)
    for u in graph[v]:
        if not is_blocked(u) and u not in res:
            res[u] = v
            return True
    for u in graph[v]:
        if not is_blocked(u) and dfs(res[u], graph, res, used, is_blocked):
            res[u] = v
            return True
    return False


def bipartite_matching(graph, vert_order, is_blocked, limit=100):
    res = dict()
    for v in vert_order:
        dfs(v, graph, res, set(), is_blocked)
        if len(res) >= limit:
            break
    return res


def get_plump_moves(is_blocked=lambda v: False, limit=100):
    graph = dict()
    for v_tile in GG.gamemap.tiles[GG.self]:
        v = tile2vert(v_tile)
        for u in GG.side_graph[v]:
            if can_expand(v, u):
                if u not in graph:
                    graph[u] = []
                graph[u].append(v)
    vert_order = sorted(graph.keys(), key=lambda v: manhattan(GG.my_general, v))
    expand_from = bipartite_matching(graph, vert_order, is_blocked, limit)
    res = [(v, u) for v, u in expand_from.items()]
    res.sort(key=lambda vu: min(manhattan(GG.my_general, vu[0]), manhattan(GG.my_general, vu[1])))
    print('PLUMP MATCHING:')
    for v, u in res:
        print(vert2tile(v), vert2tile(u))
    return res


def validate(v, u, is50):
    if not can_expand(v, u):
        return False
    return not is50 or GG.armies[v] // 2 > GG.armies[u]


def can_expand(v, u):
    v_tile = vert2tile(v)
    u_tile = vert2tile(u)
    return v_tile.tile == GG.self and u_tile.army < v_tile.army - 1 and u_tile.tile in (TILE_EMPTY, GG.enemy)
