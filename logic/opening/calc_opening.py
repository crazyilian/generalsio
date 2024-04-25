from logic.utils import GG, tile2vert, is_blocked_vert, bfs
from . import openings_list
from itertools import permutations
import time
import os

curdir = os.path.dirname(__file__)

BLOCKED, EMPTY, CAPTURED = 0, 1, 2

sector_borders = [  # line: y * el[0] + x * el[1] = 0
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


# find max path in graph that doesn't exceed size_limit, visit only empty tiles, with preferred direction (+-W +-1)
def dfs(v, graph, path_limit, path, field, prefer_direction):
    path.append(v)

    max_path = path.copy()
    if path_limit == len(max_path):
        return max_path

    sides = graph[v]
    prefer_u = v + prefer_direction
    if (0 <= prefer_u < GG.W * GG.H and sides[0] != prefer_u and prefer_u in sides and
            field[prefer_u] == EMPTY and prefer_u not in path):  # if preferred neighbor exists and not already first
        sides = sides.copy()
        ind = sides.index(prefer_u)
        sides[ind], sides[0] = sides[0], sides[ind]

    for u in sides:
        if field[u] != EMPTY or u in path:
            continue
        new_path = dfs(u, graph, path_limit, path, field, prefer_direction)
        if len(new_path) == path_limit:
            return new_path
        elif len(new_path) > len(max_path):
            max_path = new_path
    path.pop()
    return max_path


# find the shortest (manhattan) paths to start, trying to minimize euclidian distance
def get_shortest_paths(start, graph, dist):
    prev = [None] * (GG.H * GG.W)
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


def get_path(start, prev, limit=10000):
    path = [start]
    v, u = start, prev[start]
    while u is not None and len(path) < limit:
        path.append(u)
        v, u = u, prev[u]
    return path


# find opening moves given opening and ordered destinations
def calculate_one_opening(opening, destinations, already_found_land):
    turn = 0
    if opening[0] is None:
        opening = opening[1:]
        turn = 1
    turn += opening[0][1] * 2
    land_expected = openings_list.get_land(opening)  # max land that can still be captured
    moves = []

    field = [BLOCKED if is_blocked_vert(v) else EMPTY for v in range(GG.W * GG.H)]
    general_v = tile2vert(GG.my_general)
    field[general_v] = CAPTURED
    my_cells = [general_v]
    for i in range(len(opening)):
        inside, outside = opening[i]
        if outside == 0:
            turn += inside + outside
            continue
        destination = destinations[i]
        dists_outside = bfs(destination, GG.side_graph, lambda v: field[v] == CAPTURED)
        paths_outside = get_shortest_paths(destination, GG.side_graph, dists_outside)
        dists_inside = bfs(general_v, GG.side_graph, lambda v: field[v] == EMPTY)
        paths_inside = get_shortest_paths(general_v, GG.side_graph, dists_inside)

        # search for neighbors v-u, where v captured, u empty, dists_inside[v] = inside, exists path u -> destination
        v_inside, v_outside = None, None
        bad_borders = []  # neighbors v-u (same as searching for), but not exists path u -> destination
        for v in my_cells:
            if dists_inside[v] != inside:
                continue
            for u in GG.side_graph[v]:
                if dists_outside[u] is None:
                    if field[u] == EMPTY:
                        bad_borders.append((v, u))
                elif v_outside is None or dists_outside[v_outside] > dists_outside[u]:
                    v_inside, v_outside = v, u
        path = []
        if v_inside is None:
            # try to find outside path not to destination, but by dfs
            max_outside_path = []
            path_limit = min(5, outside)
            for v, u in bad_borders:
                new_outside_path = dfs(u, GG.side_graph, path_limit, [], field, u - v)
                if len(new_outside_path) > len(max_outside_path):
                    max_outside_path = new_outside_path
                    v_inside, v_outside = v, u
                if len(max_outside_path) == path_limit:
                    break
            if len(max_outside_path) > 0:
                path = get_path(v_inside, paths_inside)
                path.reverse()
                path += max_outside_path
        else:
            path = get_path(v_inside, paths_inside)
            path.reverse()
            path += get_path(v_outside, paths_outside, limit=outside)
        # applying path
        cnt_new_land = 0
        moves.append((turn, []))
        for j in range(1, len(path)):
            v, u = path[j - 1], path[j]
            moves[-1][1].append((v, u))
            if field[u] == EMPTY:
                my_cells.append(u)
                field[u] = CAPTURED
                cnt_new_land += 1
        land_expected -= outside - cnt_new_land
        if land_expected < already_found_land:  # if current opening can't become better than current best opening
            return 1, 0, []
        turn += inside + outside
    # calculating number empty tiles that are neighbors of captured tiles
    empty_neighs = []
    for v in my_cells:
        for u in GG.side_graph[v]:
            if field[u] == EMPTY:
                empty_neighs.append(u)
    return len(my_cells), len(set(empty_neighs)), moves


# find "destination" tile in each sector to which opening lines will be directed
def get_all_destinations():
    S = len(sector_borders)
    field = [[' ' for _ in range(GG.W)] for _ in range(GG.H)]
    y0 = GG.my_general.y
    x0 = GG.my_general.x

    # split field to sectors
    sector_sm = [[0, 0] for _ in range(S)]  # sum of coordinates of maybe-general tiles in sector
    sectors = [[] for _ in range(S)]  # all maybe-general tiles in sector
    for y in range(GG.H):
        for x in range(GG.W):
            for t in range(S):
                a = (y - y0) * sector_borders[t - 1][0] + (x - x0) * sector_borders[t - 1][1]
                b = (y - y0) * sector_borders[t][0] + (x - x0) * sector_borders[t][1]
                if a >= 0 >= b:  # if (y, x) in sector t (between lines t and t-1)
                    break
            if GG.gamemap.grid[y][x].maybe_general:
                field[y][x] = '0123456789abcdefghij'[t]
                sectors[t].append((y, x))
                sector_sm[t][0] += y - y0
                sector_sm[t][1] += x - x0

    # find "destination" tile in each sector
    destinations = [None] * S
    weights = [len(sectors[t]) for t in range(S)]  # number of maybe-general tiles in sector ("priority" of sector)
    for t in range(S):
        if weights[t] == 0:
            continue
        # (dy, dx) - "average" tile in sector
        dy = sector_sm[t][0] / weights[t]
        dx = sector_sm[t][1] / weights[t]
        # Consider ray my_general -> (dy, dx). It's direction of sector. Let's find the farthest tile in this direction
        l, r = 0, 50
        for i in range(20):
            m = (l + r) / 2
            y = dy * m + y0
            x = dx * m + x0
            if x < 0 or y < 0 or x > GG.W - 1 or y > GG.H - 1:
                r = m
            else:
                l = m
        # (ideal_y, ideal_x) - intersection of ray and border
        ideal_y = dy * l + y0
        ideal_x = dx * l + x0
        # (best_y, best_x) - nearest maybe-general tile in sector to (ideal_y, ideal_x)
        best_y, best_x = None, None
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


def bit(mask, i):
    return (mask >> i) & 1


# for each number of opening lines select best set of destinations
def get_destination_coverings(max_opening_len):
    destinations, weights = get_all_destinations()
    not_none_dest_inds = []  # inds of destinations of non-empty sectors
    for i in range(len(destinations)):
        if destinations[i] is not None:
            not_none_dest_inds.append(i)

    n = len(not_none_dest_inds)
    dest_covering = [[] for _ in range(max(n + 1, max_opening_len + 1))]  # found answers
    dest_covering_weight = [0] * len(dest_covering)  # weights of found answers (the more the better)
    for mask in range(1, 2 ** n):
        w = 0
        covering = []
        for i_ind in range(len(not_none_dest_inds)):
            i = not_none_dest_inds[i_ind]
            if bit(mask, i_ind):  # if take destination i
                w += weights[i]
                covering.append(destinations[i])
            else:
                # check if adjacent left or right destination is taken
                l_ind = (i_ind - 1) % n
                r_ind = (i_ind + 1) % n
                l = (i - 1) % len(destinations)
                r = (i + 1) % len(destinations)
                left_taken = not_none_dest_inds[l_ind] == l and bit(mask, l_ind)
                right_taken = not_none_dest_inds[r_ind] == r and bit(mask, r_ind)
                if not left_taken and not right_taken:  # sector is not covered
                    break
        else:  # if every non-empty sector is covered
            bcnt = str(mask).count('1')
            # bcnt = mask.bit_count()  # number of taken destinations
            if w > dest_covering_weight[bcnt]:
                dest_covering_weight[bcnt] = w
                dest_covering[bcnt] = covering

    # set dest_covering if opening lines number can't cover all sectors
    sorted_dest_inds = sorted(not_none_dest_inds, key=lambda i: -weights[i])
    for i in range(n + 1):
        if len(dest_covering[i]) != i:
            dest_covering[i] = sorted_dest_inds[:i]

    # set dest_covering if opening lines number is greater than destinations number
    for i in range(n + 1, len(dest_covering)):
        dest_covering[i] = not_none_dest_inds * (i // n) + dest_covering[i % n]
    return dest_covering


# goes over all openings and destination permutations searching for best opening (maximize land, then empty neighbors)
def get_opening():
    tic = time.time()
    destination_coverings = get_destination_coverings(
        max_opening_len=max(openings_list.get_number_lines(op) for op in openings_list.openings)
    )

    mx_land = 1
    mx_empty_neighs = 0
    mx_op_ind = None
    for op_ind, opening in enumerate(openings_list.openings):
        if GG.opening_already_started:
            print("OPENING ALREADY STARTED, STOP CALCULATING")
            break
        if openings_list.get_land(opening) < mx_land:  # current opening can't be better
            continue
        dest_covering = destination_coverings[openings_list.get_number_lines(opening)]
        for dests in set(permutations(dest_covering)):
            land, empty_neighs, moves = calculate_one_opening(opening, dests, mx_land)
            if GG.opening_already_started:
                break
            if land > mx_land or (land == mx_land and empty_neighs > mx_empty_neighs):
                mx_land = land
                mx_empty_neighs = empty_neighs
                mx_op_ind = op_ind
                GG.planned_moves = dict(moves)
        else:
            continue
    print("opening:", mx_op_ind)
    print("land:", mx_land)
    print("empty neighs:", mx_empty_neighs)
    print('Opening calculation time:', time.time() - tic)
