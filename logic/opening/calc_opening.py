from logic.utils import *
from . import openings_list
from typing import List, Optional
from itertools import permutations
import time
import os

curdir = os.path.dirname(__file__)

BLOCKED = -3
EMPTY = -2
GENERAL = -1
sector_borders = [
    (0, -1),
    (2, -3),
    (3, -2),
    (1, 0),
    (3, 2),
    (2, 3),
    (0, 1),
    (-2, 3),
    (-3, 2),
    (-1, 0),
    (-3, -2),
    (-2, -3)
]


def calculate_opening_destinations():
    S = len(sector_borders)
    field = [[' ' for i in range(GG.W)] for j in range(GG.H)]
    y0 = GG.my_general.y
    x0 = GG.my_general.x
    sector_sm = [[0, 0] for i in range(S)]
    sectors = [[] for i in range(S)]

    for y in range(GG.H):
        for x in range(GG.W):
            for t in range(S):
                a = (y - y0) * sector_borders[t - 1][0] + (x - x0) * sector_borders[t - 1][1]
                b = (y - y0) * sector_borders[t][0] + (x - x0) * sector_borders[t][1]
                if a >= 0 >= b:
                    break
            if GG.gamemap.grid[y][x].maybe_general:
                field[y][x] = '0123456789abcdefghij'[t]
                sectors[t].append((y, x))
                sector_sm[t][0] += y - y0
                sector_sm[t][1] += x - x0
    destinations = [None] * S
    weights = [len(sectors[t]) for t in range(S)]
    for t in range(S):
        if weights[t] == 0:
            continue
        dy = sector_sm[t][0] / weights[t]
        dx = sector_sm[t][1] / weights[t]

        l, r = 0, 50
        for i in range(20):
            m = (l + r) / 2
            y = dy * m + y0
            x = dx * m + x0
            if x < 0 or y < 0 or x > GG.W - 1 or y > GG.H - 1:
                r = m
            else:
                l = m
        ideal_y = dy * l + y0
        ideal_x = dx * r + x0
        best_y, best_x = float('inf'), float('inf')
        best_dist = float('inf')
        for y, x in sectors[t]:
            dist = abs(y - ideal_y) + abs(x - ideal_x)
            if dist < best_dist:
                best_dist = dist
                best_y, best_x = y, x
        destinations[t] = best_y * GG.W + best_x
        field[best_y][best_x] = '#'
    for line in field:
        print(*line, sep='')

    return destinations, weights


def dfs(v, graph, size_limit, path, field, prefer_direction):
    path.append(v)
    mx_path = path.copy()
    if size_limit == len(mx_path):
        return mx_path
    sides = graph[v]

    prefer_u = v + prefer_direction
    if (0 <= prefer_u < GG.W * GG.H and sides[0] != prefer_u and prefer_u in sides and
            field[prefer_u] == EMPTY and prefer_u not in path):
        sides = sides.copy()
        ind = sides.index(prefer_u)
        sides[ind], sides[0] = sides[0], sides[ind]

    for u in sides:
        if field[u] != EMPTY or u in path:
            continue
        new_path = dfs(u, graph, size_limit, path, field, prefer_direction)
        if len(new_path) == size_limit:
            return new_path
        elif len(new_path) > len(mx_path):
            mx_path = new_path
    path.pop()
    return mx_path


def get_shortest_paths(start, graph, dist):
    prev: List[Optional[int]] = [None for i in range(GG.H * GG.W)]
    for v in range(GG.H * GG.W):
        d = dist[v]
        if d is None:
            continue
        p = None
        p_dist = float('inf')
        for u in graph[v]:
            if dist[u] != d - 1:
                continue
            dx = u // GG.W - start // GG.W
            dy = u % GG.W - start % GG.W
            u_dist = dx * dx + dy * dy
            if u_dist < p_dist:
                p_dist = u_dist
                p = u
        prev[v] = p
    return prev


def make_opening_forward(opening, destinations, already_found_land):
    turn = 0
    if opening[0] is None:
        opening = opening[1:]
        turn = 1
    turn += opening[0][1] * 2
    land_expected = openings_list.get_land(opening)
    moves = []

    field = [BLOCKED if is_blocked_vert(v) else EMPTY for v in range(GG.W * GG.H)]
    general_v = tile2vert(GG.my_general)
    field[general_v] = GENERAL
    my_cells = [general_v]
    for i in range(len(opening)):
        inside, outside = opening[i]
        destination = destinations[i]
        dists_outside = bfs(destination, GG.side_graph, lambda v: field[v] != EMPTY)
        paths_outside = get_shortest_paths(destination, GG.side_graph, dists_outside)
        dists_inside = bfs(general_v, GG.side_graph, lambda v: field[v] <= EMPTY)
        paths_inside = get_shortest_paths(general_v, GG.side_graph, dists_inside)
        v_inside = None
        v_outside = None
        bad_borders = []
        if outside > 0:
            for v in my_cells:
                if dists_inside[v] != inside:
                    continue
                for u in GG.side_graph[v]:
                    if dists_outside[u] is None:
                        if field[u] == EMPTY:
                            bad_borders.append((v, u))
                        continue
                    if v_outside is None or dists_outside[v_outside] > dists_outside[u]:
                        v_outside = u
                        v_inside = v
        if v_inside is None and len(bad_borders) > 0 and 1 <= outside:
            mx_path = []
            mx_v = (None, None)
            for v_inside, v_outside in bad_borders:
                found_path = dfs(v_outside, GG.side_graph, min(5, outside), [], field, v_outside - v_inside)
                if len(found_path) > len(mx_path):
                    mx_path = found_path
                    mx_v = (v_inside, v_outside)
            v_inside, v_outside = mx_v
            cur_moves = []
            v, u = v_inside, paths_inside[v_inside]
            while u is not None:
                cur_moves.append((u, v))
                v, u = u, paths_inside[u]
            cur_moves.reverse()
            cur_moves.append((v_inside, v_outside))
            for j in range(1, len(mx_path)):
                cur_moves.append((mx_path[j - 1], mx_path[j]))
        elif v_inside is None:
            cur_moves = []
        else:
            cur_moves = []
            v, u = v_inside, paths_inside[v_inside]
            while u is not None:
                cur_moves.append((u, v))
                v, u = u, paths_inside[u]
            cur_moves.reverse()
            if v_outside is not None:
                cur_moves.append((v_inside, v_outside))
                v, u = v_outside, paths_outside[v_outside]
                cnt_expanded = 1
                while u is not None and cnt_expanded < outside:
                    cnt_expanded += 1
                    cur_moves.append((v, u))
                    v, u = u, paths_outside[u]
        cnt_new_land = 0
        for (v, u) in cur_moves:
            if field[u] == EMPTY:
                my_cells.append(u)
                field[u] = i
                cnt_new_land += 1
        if len(cur_moves) > 0:
            moves.append((turn, cur_moves))
        turn += inside + outside
        land_expected -= outside - cnt_new_land
        if land_expected < already_found_land:
            return 1, 0, []
    empty_neighs = []
    for v in my_cells:
        for u in GG.side_graph[v]:
            if field[u] == EMPTY:
                empty_neighs.append(u)
    return len(my_cells), len(set(empty_neighs)), moves


def make_place_function(moves):
    def place():
        for move in moves:
            GG.bot.place_move(vert2tile(move[0]), vert2tile(move[1]))

    return place


def bit(mask, i):
    return (mask >> i) & 1


def calculate_opening():
    tic = time.time()
    destinations, weights = calculate_opening_destinations()
    not_none_dest_inds = []
    for i in range(len(destinations)):
        if destinations[i] is not None:
            not_none_dest_inds.append(i)

    dest_covering: List[Optional[List[int]]] = [None] * max(len(destinations) + 1, 6)
    dest_covering_weights = [-1] * len(dest_covering)
    for mask in range(1, 2 ** len(not_none_dest_inds)):
        bcnt = mask.bit_count()
        w = 0
        covering: List[int] = []
        for ind_i in range(len(not_none_dest_inds)):
            i = not_none_dest_inds[ind_i]
            if bit(mask, ind_i):
                w += weights[i]
                covering.append(destinations[i])
            else:
                l_ind = (ind_i - 1) % len(not_none_dest_inds)
                r_ind = (ind_i + 1) % len(not_none_dest_inds)
                l = (i - 1) % len(destinations)
                r = (i + 1) % len(destinations)
                if ((not_none_dest_inds[l_ind] != l or not bit(mask, l_ind))
                        and (not_none_dest_inds[r_ind] != r or not bit(mask, r_ind))):
                    break
        else:
            if w > dest_covering_weights[bcnt]:
                dest_covering_weights[bcnt] = w
                dest_covering[bcnt] = covering
    for i in range(1, len(dest_covering)):
        if dest_covering[i] is None and dest_covering[i - 1] is not None:
            dests = dest_covering[i - 1].copy()
            while len(dests) < i:
                dests += dests.copy()
            dest_covering[i] = dests[:i]

    mx_land = 1
    mx_empty_neighs = 0
    mx_moves = []
    mx_dests = []
    mx_op_ind = None
    for op_ind, opening in enumerate(openings_list.openings):
        if GG.opening_already_started:
            print("OPENING ALREADY STARTED, STOP CALCULATING")
            break
        if openings_list.get_land(opening) < mx_land:
            continue
        if op_ind % 1 == 0:
            print('calc op:', op_ind)
        for dest_ind, dests in enumerate(permutations(dest_covering[len(opening)])):
            land, empty_neighs, moves = make_opening_forward(opening, dests, mx_land)
            if GG.opening_already_started:
                break
            if land > mx_land or (land == mx_land and empty_neighs > mx_empty_neighs):
                mx_land = land
                mx_empty_neighs = empty_neighs
                mx_moves = moves
                mx_dests = dests
                mx_op_ind = op_ind
                opening_turns = dict()
                for i in range(len(mx_moves)):
                    opening_turns[mx_moves[i][0]] = make_place_function(mx_moves[i][1].copy())
                GG.opening_turns = opening_turns
        else:
            continue
    print("destinations:", mx_dests)
    print("opening:", mx_op_ind)
    print("land:", mx_land)
    print("empty neighs:", mx_empty_neighs)
    with open(os.path.join(curdir, "opening_statistics2.log"), "a") as f:
        f.write(str(mx_op_ind) + '\n')
    if mx_land <= 18:
        with open(os.path.join(curdir, "bad_spawns.log"), "a") as f:
            f.write(f"land: {mx_land}, {GG.gamemap.replay_url}\n")
    print('Opening calculation time:', time.time() - tic)


def start_opening():
    GG.opening_already_started = True


def init():
    GG.opening_already_started = False
    GG.opening_turns = dict()
