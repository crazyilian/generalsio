from base.base.client.constants import *
from enum import Enum
from sortedcontainers import SortedSet
from collections import deque
from .core import GG, vert2tile, tile2vert, manhattan
from logic.moves_queue import MovesQueue


class Phase(Enum):
    PREPARE = 0
    OPENING = 1
    EARLY_S_LINES = 2
    S_LINES = 3
    ATTACK_GENERAL = 4


def init(bot, gamemap):
    GG.clear()
    GG.bot = bot
    GG.gamemap = gamemap
    GG.self = gamemap.player_index
    GG.enemy = 1 - GG.self
    GG.my_general = gamemap.generals[GG.self]
    GG.H = gamemap.rows
    GG.W = gamemap.cols
    GG.phase = Phase.PREPARE
    GG.planned_moves = dict()
    GG.my_general_exposed = False
    GG.verts_closer_than = dict()
    GG.attack_phase_start_turn = -1000
    GG.queue = MovesQueue()
    GG.urgent_queue = MovesQueue()

    recalc_cities()  # recalc_side_graph() called there
    recalc_maybe_general(use_previous=False)
    recalc_last_seen(is_first=True)
    update()


def verts_closer_than(dist):
    if dist not in GG.verts_closer_than:
        GG.verts_closer_than[dist] = [v for v in range(GG.W * GG.H) if
                                      GG.dists_from_general_cities[v] is not None
                                      and GG.dists_from_general_cities[v] <= dist]
    return GG.verts_closer_than[dist]


def update():
    GG.armies = [vert2tile(v).army for v in range(GG.W * GG.H)]
    recalc_cities()
    recalc_maybe_general()
    update_general_exposed()
    recalc_last_seen()


def update_general_exposed():
    if GG.my_general_exposed:
        return
    for v in seen_by(tile2vert(GG.my_general)):
        if vert2tile(v).tile == GG.enemy:
            GG.my_general_exposed = True
            return


def is_blocked_vert(v):
    tile = GG.gamemap.grid[v // GG.W][v % GG.W]
    if tile.isCity:
        return tile.tile < 0
    else:
        return tile.tile == TILE_OBSTACLE or tile.tile == TILE_MOUNTAIN or tile.isSwamp


def is_blocked_vert_city(v):
    tile = GG.gamemap.grid[v // GG.W][v % GG.W]
    return not tile.isCity and (tile.tile == TILE_OBSTACLE or tile.tile == TILE_MOUNTAIN or tile.isSwamp)


def seen_by(v):
    y0 = v // GG.W
    x0 = v % GG.W
    res = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            y = y0 + dy
            x = x0 + dx
            v = y * GG.W + x
            if 0 <= y < GG.H and 0 <= x < GG.W and GG.dists_from_general_cities[v] is not None:
                res.append(v)
    return res


def get_graph(is_blocked):
    graph = [[] for i in range(GG.W * GG.H)]
    for v in range(GG.W * GG.H):
        if is_blocked(v):
            continue
        if v >= GG.W and not is_blocked(v - GG.W):
            graph[v].append(v - GG.W)
            graph[v - GG.W].append(v)
        if v % GG.W > 0 and not is_blocked(v - 1):
            graph[v].append(v - 1)
            graph[v - 1].append(v)
    return graph


def recalc_side_graph():
    GG.side_graph = get_graph(is_blocked_vert)
    GG.dists_from_general = bfs(tile2vert(GG.my_general), GG.side_graph)


def recalc_cities():
    GG.my_cities = [c for c in GG.gamemap.cities if c.tile == GG.self]

    new_captured_cities = [c for c in GG.gamemap.cities if c.tile >= 0]
    if GG.captured_cities != new_captured_cities:
        GG.captured_cities = new_captured_cities
        recalc_side_graph()  # is_blocked_vert changed

    if GG.cities != GG.gamemap.cities:
        GG.cities = GG.gamemap.cities.copy()
        print('cities', GG.cities)
        GG.side_graph_cities = get_graph(is_blocked_vert_city)
        GG.dists_from_general_cities = bfs(tile2vert(GG.my_general), GG.side_graph_cities)
        GG.verts_closer_than.clear()  # dists_from_general_cities changed


def bfs(starts, graph, is_blocked=lambda v: False):
    if isinstance(starts, int):
        starts = [starts]
    dist = [None for i in range(len(graph))]
    Q = deque(starts)
    for s in starts:
        dist[s] = 0
    while len(Q) > 0:
        v = Q.popleft()
        for u in graph[v]:
            if dist[u] is None and not is_blocked(u):
                dist[u] = dist[v] + 1
                Q.append(u)
    return dist


def dijkstra(start, graph, is_blocked=lambda v: False, get_weight=lambda v: 1):
    dist = [None for i in range(len(graph))]
    dist[start] = 0
    Q = SortedSet([(0, start)])
    while len(Q) > 0:
        d, v = Q.pop(0)
        for u in graph[v]:
            nd = d + get_weight(u)
            if not is_blocked(u) and (dist[u] is None or dist[u] > nd):
                Q.discard((dist[u], u))
                dist[u] = nd
                Q.add((nd, u))
    return dist


def bfs_limit(start, graph, dist_limit, is_blocked=lambda v: False):
    dist = dict()
    dist[start] = 0
    if dist_limit == 0:
        return dist
    Q = deque([start])
    while len(Q) > 0:
        v = Q.popleft()
        for u in graph[v]:
            if u not in dist and not is_blocked(u):
                dist[u] = dist[v] + 1
                if dist[u] < dist_limit:
                    Q.append(u)
    return dist


def recalc_maybe_general(use_previous=True):
    if not use_previous:
        GG.enemy_general = None
        GG.maybe_generals = [vert2tile(v) for v in range(GG.H * GG.W)]

    GG.enemy_general = GG.gamemap.generals[1 - GG.self]
    if GG.enemy_general is not None:
        # print('OTHER GENERAL:', (GG.enemy_general.y, GG.enemy_general.x))
        if len(GG.maybe_generals) > 1:
            for tile in GG.maybe_generals:
                if tile != GG.enemy_general:
                    tile.maybe_general = False
            GG.maybe_generals = [GG.enemy_general]
        return

    new_maybe_generals = []
    for cell in GG.maybe_generals:
        cell.maybe_general = (GG.dists_from_general[tile2vert(cell)] is not None
                              and cell.tile == TILE_FOG
                              and manhattan(cell, GG.my_general) >= 15)
        if cell.maybe_general:
            new_maybe_generals.append(cell)
    GG.maybe_generals = new_maybe_generals
    # print('\n\nRECALC MAYBE GENERALS')
    # print([(tile.y, tile.x) for tile in GG.maybe_generals])
    # print('\n')
    assert len(new_maybe_generals) >= 1
    if len(new_maybe_generals) == 1:
        GG.enemy_general = new_maybe_generals[0]
    # table = ""
    # for y in range(GG.H):
    #     for x in range(GG.W):
    #         if GG.gamemap.grid[y][x].maybe_general:
    #             table += "#"
    #         else:
    #             table += "."
    #     table += '\n'
    # print(table)


def recalc_last_seen(is_first=False):
    if is_first:
        for y in range(GG.H):
            for x in range(GG.W):
                GG.gamemap.grid[y][x].last_seen = -1000
    else:
        for tile in list(GG.gamemap.tiles[GG.self]):
            for u in seen_by(tile2vert(tile)):
                vert2tile(u).last_seen = GG.gamemap.turn
