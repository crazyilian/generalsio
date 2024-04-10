from logic.utils import GG, bfs_limit, tile2vert, vert2tile, bfs
from collections import deque
import time
from logic.army_gather import gather_army_limit

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


def get_sector(y, x, y0, x0):
    for t in range(len(sector_borders)):
        a = (y - y0) * sector_borders[t - 1][0] + (x - x0) * sector_borders[t - 1][1]
        b = (y - y0) * sector_borders[t][0] + (x - x0) * sector_borders[t][1]
        if a >= 0 >= b:  # if (y, x) in sector t (between lines t and t-1)
            return t
    assert False


# find "destination" tile in each sector to which opening lines will be directed
def get_all_destinations(eps):
    S = len(sector_borders)
    y0 = GG.H / 2
    x0 = GG.W / 2

    field = [[' ' for _ in range(GG.W)] for _ in range(GG.H)]

    # split field to sectors
    sector_sm = [[0, 0] for _ in range(S)]  # sum of coordinates of maybe-general tiles in sector
    sectors = [[] for _ in range(S)]  # all maybe-general tiles in sector
    for y in range(GG.H):
        for x in range(GG.W):
            t = get_sector(y, x, y0, x0)
            if GG.gamemap.grid[y][x].maybe_general:
                field[y][x] = '0123456789abcdefghij'[t]
                sectors[t].append((y, x))
                sector_sm[t][0] += y - y0
                sector_sm[t][1] += x - x0

    for el in field:
        print(''.join(el))
    # find "destination" tile in each sector
    destinations = [None] * S
    weights = [len(sectors[t]) for t in range(S)]  # number of maybe-general tiles in sector ("priority" of sector)
    for t in range(S):
        if weights[t] <= eps:
            continue
        # (dy, dx) - "average" tile in sector
        ideal_y = sector_sm[t][0] / weights[t] + y0
        ideal_x = sector_sm[t][1] / weights[t] + x0

        # (best_y, best_x) - nearest maybe-general tile in sector to (dy, dx)
        best_y, best_x = None, None
        best_dist = float('inf')
        for y, x in sectors[t]:
            dist = abs(y - ideal_y) + abs(x - ideal_x)
            if dist < best_dist:
                best_dist = dist
                best_y, best_x = y, x
        destinations[t] = best_y * GG.W + best_x
        # print(f'sector: {sectors[t]}, dest: {(destinations[t] // GG.W, destinations[t] % GG.W)}')

    my_sector = get_sector(GG.my_general.y, GG.my_general.x, GG.H / 2, GG.W / 2)
    near_sector_priority = destinations[my_sector:] + destinations[:my_sector]
    print('dest:', destinations)
    print('my sector:', my_sector)

    weights = [weights[i] for i in range(S) if destinations[i] is not None]
    destinations = [destinations[i] for i in range(S) if destinations[i] is not None]

    return destinations, weights, near_sector_priority


INF = 10 ** 9


def bfs_finish(starts_dists, finish):
    graph = GG.side_graph
    finish = set(finish)
    dist = [None] * len(graph)
    pred = [None] * len(graph)
    starts_dists.sort(key=lambda sd: -sd[1])
    for (s, d) in starts_dists:
        dist[s] = d
    Q = deque()
    while len(finish) > 0 and (len(Q) > 0 or len(starts_dists) > 0):
        while len(Q) == 0 or (len(starts_dists) > 0 and starts_dists[-1][1] <= dist[Q[0]]):
            Q.appendleft(starts_dists[-1][0])
            starts_dists.pop()
        v = Q.popleft()
        for u in graph[v]:
            if dist[u] is None:
                finish.discard(u)
                dist[u] = dist[v] + 1
                pred[u] = v
                Q.append(u)
    return dist, pred


def bigbfs(dests):
    dists = [[0] * len(GG.side_graph)]
    preds = [[None] * len(GG.side_graph)]
    for i in range(1, len(dests)):
        starts_dists = [(v, dists[i - 1][v]) for v in dests[i - 1] if dists[i - 1][v] is not None]
        dist, pred = bfs_finish(starts_dists, dests[i])
        if all(dist[v] is None for v in dests[i]):
            dests = dests[:i]
            break
        dists.append(dist)
        preds.append(pred)

    if len(dests) == 1:
        return []
    last = None
    for final in dests[-1]:
        if dists[-1][final] is not None and (last is None or dists[-1][last] > dists[-1][final]):
            last = final
    path = [last]
    for i in range(len(dists) - 1, 0, -1):
        while preds[i][last] is not None:
            last = preds[i][last]
            path.append(last)
    return path[::-1]


def get_nearest_sector(near_sector_priority, destinations):
    if GG.last_direction == -1:
        near_sector_priority = near_sector_priority[:1] + near_sector_priority[:0:-1]
    print('near sector priority = ', [(el // GG.W, el % GG.W) if el is not None else None for el in near_sector_priority])
    dest2sector = dict(zip(destinations, range(len(destinations))))
    for d in near_sector_priority:
        if d in dest2sector:
            print(dest2sector[d])
            return dest2sector[d]
    assert False


def get_moves():
    tic = time.time()
    destinations, weights, near_sector_priority = get_all_destinations(3 if len(GG.maybe_generals) > 40 else 0)
    dest_areas = [list(bfs_limit(v, GG.side_graph, 1).keys()) for v in destinations]
    for i in range(len(destinations)):
        if any(vert2tile(v).tile == GG.self for v in dest_areas[i]):
            destinations[i] = None
    weights = [weights[i] for i in range(len(destinations)) if destinations[i] is not None]
    dest_areas = [dest_areas[i] for i in range(len(destinations)) if destinations[i] is not None]
    destinations = [destinations[i] for i in range(len(destinations)) if destinations[i] is not None]
    for area in range(len(dest_areas)):
        print(f'{area} - dest: {(destinations[area] // GG.W, destinations[area] % GG.W)}, area: {[(v // GG.W, v % GG.W) for v in dest_areas[area]]}, weight: {weights[area]}')
    if len(destinations) == 0:
        return [], []

    vert2areas = dict()
    for area in range(len(dest_areas)):
        for v in dest_areas[area]:
            if v not in vert2areas:
                vert2areas[v] = []
            vert2areas[v].append(area)

    best_pathes = []
    GG.last_direction *= -1
    print(f'last_direction={GG.last_direction}')

    my_sector = get_nearest_sector(near_sector_priority, destinations)

    # for start in range(len(destinations)):
    for start in [(my_sector + i * GG.last_direction) % len(destinations) for i in range(3)]:
        dest = [[tile2vert(tile) for tile in GG.gamemap.tiles[GG.self]]]
        for it in range(6):
            ind = (start + it * GG.last_direction) % len(destinations)
            dest.append(dest_areas[ind])
        path = bigbfs(dest)

        if len(path) <= 1:
            continue
        path = path[:15]
        moves_gather, army = gather_army_limit(path[0], len(path) - 1, (5, 10, 15, 20, 25))
        path = path[:1 + army]
        print(f'start={start}, len(path)={len(path)}, len(moves_gather)={len(moves_gather)}, root={path[0]}')
        if len(path) <= 1:
            continue

        captured = set()
        max_area_sz = -1
        dist_max_area = -1
        kek = []
        for i in range(len(path)):
            v = path[i]
            for area in vert2areas.get(v, []):
                captured.add(area)
                kek.append(area)
                if weights[area] > max_area_sz:
                    max_area_sz = weights[area]
                    dist_max_area = i
        print(f'captured_areas={kek}')
        best_pathes.append({
            'path': path,
            'captured_areas': captured,
            'max_area_sz': max_area_sz,
            'dist_max_area': dist_max_area,
            'moves_gather': moves_gather
        })
    if len(best_pathes) == 0:
        return [], []
    best_pathes.sort(key=lambda x: -len(x['captured_areas']))
    best_pathes = best_pathes[:4]

    best_pathes.sort(key=lambda x: (
        -x['max_area_sz'] // 4,  # max area with eps
        abs(2 * x['dist_max_area'] - len(x['captured_areas']) - 1)  # abs(ind - (n - ind - 1))
    ))
    best_path = best_pathes[0]['path']
    best_moves_gather = best_pathes[0]['moves_gather']
    print('best path:', best_path)
    print('--------- get_moves ----------', time.time() - tic)
    return best_path, best_moves_gather
