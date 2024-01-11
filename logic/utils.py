from base.base.bot_base import GeneralsBot
from base.base.client.map import Map
from base.base.client.tile import Tile
from base.base.client.constants import *

from typing import List, Optional
from collections import deque


class GameGlobals:
    bot: GeneralsBot = None
    gamemap: Map = None
    my_general: Tile = None
    other_general: Tile = None
    maybe_generals: List[Tile] = []
    side_graph: List[List[int]] = None
    H, W = -1, -1


GG = GameGlobals()


def init(bot: GeneralsBot, gamemap: Map):
    GG.bot = bot
    GG.gamemap = gamemap
    GG.my_general = gamemap.generals[gamemap.player_index]
    GG.H = gamemap.rows
    GG.W = gamemap.cols
    make_side_graph()
    calc_unreachable()
    recalc_maybe_general(use_previous=False)


def tile2vert(tile):
    return tile.y * GG.W + tile.x


def vert2tile(v):
    return GG.gamemap.grid[v // GG.W][v % GG.W]


def is_blocked_vert(v):
    tile = GG.gamemap.grid[v // GG.W][v % GG.W]
    return tile.tile == TILE_OBSTACLE or tile.tile == TILE_MOUNTAIN or tile.isCity or tile.isSwamp


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
    return abs(tile1.y - tile2.y) + abs(tile1.x - tile2.x)


def bfs(start, graph, is_blocked=lambda v: False):
    dist: List[Optional[int]] = [None for i in range(len(graph))]
    dist[start] = 0
    Q = deque([start])
    while len(Q) > 0:
        v = Q.popleft()
        for u in graph[v]:
            if dist[u] is None and not is_blocked(u):
                dist[u] = dist[v] + 1
                Q.append(u)
    return dist


def calc_unreachable():
    dists_to_general = bfs(tile2vert(GG.my_general), GG.side_graph)
    for v in range(GG.W * GG.H):
        vert2tile(v).is_unreachable = dists_to_general[v] is None


def recalc_maybe_general(use_previous=True):
    if not use_previous:
        GG.other_general = None
        GG.maybe_generals = list(range(GG.H * GG.W))

    GG.other_general = GG.gamemap.generals[1 - GG.gamemap.player_index]
    if GG.other_general is not None:
        return

    new_maybe_generals = []
    for v in GG.maybe_generals:
        cell = vert2tile(v)
        cell.maybe_general = not cell.is_unreachable and cell.tile == TILE_FOG and manhattan(cell, GG.my_general) >= 15
        if cell.maybe_general:
            new_maybe_generals.append(cell)
    GG.maybe_generals = new_maybe_generals
    assert len(new_maybe_generals) >= 1
    if len(new_maybe_generals) == 1:
        GG.other_general = new_maybe_generals[0]
