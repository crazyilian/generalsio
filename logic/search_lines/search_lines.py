from logic.utils import GG, bfs, bfs_limit, tile2vert, vert2tile, seen_by
import itertools
from sortedcontainers import SortedSet


def process_score(v, score_raw):
    if score_raw[v] is None:
        return None
    dd = bfs_limit(v, GG.side_graph, 2, lambda v: score_raw[v] is None)
    sm, cnt = 0, 0
    for u in dd.keys():
        if not vert2tile(u).maybe_general:
            continue
        k = 3 - dd[u]
        sm += score_raw[u] * k
        cnt += k
    if cnt == 0:
        return None
    return sm / cnt


def dijkstra_finish(starts, finish):
    if isinstance(starts, int):
        starts = [starts]
    graph = GG.side_graph
    finish = set(finish)
    dist = [None] * len(graph)
    pred = [None] * len(graph)
    Q = SortedSet()
    for s in starts:
        Q.add((0, s))
        dist[s] = 0
    while len(Q) > 0:
        d, v = Q.pop(0)
        finish.discard(v)
        if len(finish) == 0:
            break
        for u in graph[v]:
            nd = d + (1 + GG.armies[v])
            if dist[u] is None or dist[u] > nd:
                Q.discard((dist[u], u))
                dist[u] = nd
                pred[u] = v
                Q.add((nd, u))
    return dist, pred


def get_path(pred, v):
    path = [v]
    while pred[path[-1]] is not None:
        path.append(pred[path[-1]])
    return path[::-1]


def calc_score_raw():
    dist_to_my = bfs([tile2vert(tile) for tile in GG.gamemap.tiles[GG.self]], GG.side_graph)
    dist_to_enemy = bfs([tile2vert(tile) for tile in GG.gamemap.tiles[GG.enemy]], GG.side_graph,
                        lambda v: vert2tile(v).tile in (GG.self, -1))  # my or empty

    score_raw = [None if None in (dist_to_my[v], dist_to_enemy[v]) else 1.1 ** dist_to_my[v] - 1.1 ** dist_to_enemy[v]
                 for v in range(GG.W * GG.H)]
    return score_raw


def calc_score():
    score_raw = calc_score_raw()
    score = [process_score(v, score_raw) for v in range(GG.W * GG.H)]
    return score


def get_score(v):
    score_raw = calc_score_raw()
    res = process_score(v, score_raw)
    if res is None:
        res = -float('inf')
    print(f'get_score {vert2tile(v)} - res={res}')
    return res


def get_moves():
    score = calc_score()
    best = None
    for v in range(GG.W * GG.H):
        if score[v] is None:
            continue
        if best is None or score[v] > score[best]:
            best = v
    area = list(bfs_limit(best, GG.side_graph, 2, lambda v: score[v] is None).keys())
    print(f'search lines: best={(best // GG.W, best % GG.W)}, area={area}')

    dist_inside, pred_inside = dict(), dict()
    for v in area:
        dist_inside[v], pred_inside[v] = dijkstra_finish(v, area)
    dist_outside, pred_outside = dijkstra_finish([tile2vert(tile) for tile in GG.gamemap.tiles[GG.self]], area)

    best_pathes = []
    for dests in itertools.product(area, repeat=min(3, len(area))):
        dests = list(dict.fromkeys(dests).keys())  # remove duplicates, keep order ([1, 2, 1] and [1, 1, 2] are [1, 2])
        path = get_path(pred_outside, dests[0])
        for i in range(1, len(dests)):
            path += get_path(pred_inside[dests[i - 1]], dests[i])[1:]

        seen = set()
        pathset = set()
        for v in path:
            pathset.add(v)
            for u in seen_by(v):
                seen.add(u)

        cnt_seen = 0
        for v in area:
            if vert2tile(v).maybe_general and v in seen:
                cnt_seen += 1
        army = 0
        for v in pathset:
            if vert2tile(v).tile != GG.self:
                army += GG.armies[v]

        best_pathes.append({
            'path': path,
            'cnt_seen': cnt_seen,
            'army': army
        })

    best_pathes.sort(key=lambda x: (-x['cnt_seen'], x['army'] + len(x['path'])))
    best_path = best_pathes[0]
    return best_path['path'], best_path['army'] + len(best_path['path']), best
