from base.base.bot_base import GeneralsBot
from base.base.client.map import Map
from base.base.client.tile import Tile
from base.base.client.constants import *
from enum import Enum
from sortedcontainers import SortedSet

from typing import List, Optional
from collections import deque


class Phase(Enum):
    PREPARE = 0
    OPENING = 1
    EARLY_S_LINES = 2
    S_LINES = 3
    ATTACK_GENERAL = 4


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

    side_graph: List[List[int]] = None
    enemy_general: Tile = None
    maybe_generals: List[Tile] = None
    armies: List[int] = None


GG = GameGlobals()


def init(bot: GeneralsBot, gamemap: Map):
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
    make_side_graph()
    calc_unreachable()
    recalc_maybe_general(use_previous=False)
    update()


def update():
    GG.armies = [vert2tile(v).army for v in range(GG.W * GG.H)]
    recalc_maybe_general()
    update_general_exposed()


def update_general_exposed():
    if GG.my_general_exposed:
        return
    for v in seen_by(tile2vert(GG.my_general)):
        if vert2tile(v).tile == GG.enemy:
            GG.my_general_exposed = True
            return


def tile2vert(tile):
    return tile.y * GG.W + tile.x


def vert2tile(v):
    return GG.gamemap.grid[v // GG.W][v % GG.W]


def is_blocked_vert(v):
    tile = GG.gamemap.grid[v // GG.W][v % GG.W]
    return tile.tile == TILE_OBSTACLE or tile.tile == TILE_MOUNTAIN or tile.isCity or tile.isSwamp


def seen_by(v):
    y0 = v // GG.W
    x0 = v % GG.W
    res = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            y = y0 + dy
            x = x0 + dx
            if 0 <= y < GG.H and 0 <= x < GG.W:
                res.append(y * GG.W + x)
    return res


def make_side_graph():
    side_graph = [[] for i in range(GG.W * GG.H)]
    for v in range(GG.W * GG.H):
        if is_blocked_vert(v):
            continue
        if v >= GG.W and not is_blocked_vert(v - GG.W):
            side_graph[v].append(v - GG.W)
            side_graph[v - GG.W].append(v)
        if v % GG.W > 0 and not is_blocked_vert(v - 1):
            side_graph[v].append(v - 1)
            side_graph[v - 1].append(v)
    GG.side_graph = side_graph


def manhattan(tile1, tile2):
    if isinstance(tile1, int):
        tile1 = vert2tile(tile1)
    if isinstance(tile2, int):
        tile2 = vert2tile(tile2)
    return abs(tile1.y - tile2.y) + abs(tile1.x - tile2.x)


def bfs(starts, graph, is_blocked=lambda v: False):
    if isinstance(starts, int):
        starts = [starts]
    dist: List[Optional[int]] = [None for i in range(len(graph))]
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
    dist: List[Optional[int]] = [None for i in range(len(graph))]
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


def calc_unreachable():
    dists_to_general = bfs(tile2vert(GG.my_general), GG.side_graph)
    for v in range(GG.W * GG.H):
        vert2tile(v).is_unreachable = dists_to_general[v] is None


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
        cell.maybe_general = not cell.is_unreachable and cell.tile == TILE_FOG and manhattan(cell, GG.my_general) >= 15
        if cell.maybe_general:
            new_maybe_generals.append(cell)
    GG.maybe_generals = new_maybe_generals
    # print('\n\nRECALC MAYBE GENERALS')
    # print([(tile.y, tile.x) for tile in GG.maybe_generals])
    # print('\n')
    assert len(new_maybe_generals) >= 1
    if len(new_maybe_generals) == 1:
        GG.enemy_general = new_maybe_generals[0]
    table = ""
    for y in range(GG.H):
        for x in range(GG.W):
            if GG.gamemap.grid[y][x].maybe_general:
                table += "#"
            else:
                table += "."
        table += '\n'
    # print(table)
