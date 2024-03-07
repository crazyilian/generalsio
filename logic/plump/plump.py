from logic.utils import GG, tile2vert, vert2tile, TILE_EMPTY, manhattan


def dfs(v, graph, res, used):
    if v in used:
        return False
    used.add(v)
    for u in graph[v]:
        if u not in res:
            res[u] = v
            return True
    for u in graph[v]:
        if dfs(res[u], graph, res, used):
            res[u] = v
            return True
    return False


def bipartite_matching(graph, vert_order):
    res = dict()
    for v in vert_order:
        dfs(v, graph, res, set())
    return res


def get_plump_moves():
    graph = dict()
    for v_tile in GG.gamemap.tiles[GG.self]:
        v = tile2vert(v_tile)
        sides = sorted([u for u in GG.side_graph[v] if can_expand(v, u)], key=lambda u: -manhattan(GG.my_general, u))
        if len(sides) > 0:
            graph[v] = sides
    vert_order = sorted(graph.keys(), key=lambda v: -manhattan(GG.my_general, v))
    expand_from = bipartite_matching(graph, vert_order)
    GG.plump_moves = [(v, u) for u, v in expand_from.items()]


def can_expand(v, u):
    v_tile = vert2tile(v)
    u_tile = vert2tile(u)
    return v_tile.tile == GG.self and u_tile.army < v_tile.army - 1 and u_tile.tile in (TILE_EMPTY, 1 - GG.self)


def init():
    GG.plump_moves = []
