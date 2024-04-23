import itertools

from logic.utils import dijkstra, bfs_limit
from logic.utils import GG, vert2tile, tile2vert
import time


def calc_useless(v, tree, armies, useless):
    useless[v] = armies[v] <= 1
    for u in tree[v]:
        useless[v] &= calc_useless(u, tree, armies, useless)
    return useless[v]


def calc_lazy(v, k, dp, tree, armies, dist, useless):
    if k == 0:
        return 0, None, None
    if k in dp[v]:
        return dp[v][k]
    ans = armies[v] - 1
    ansd = dist[v]
    anssm = (0,) * len(tree[v])
    if len(tree) >= 1:
        for sm in itertools.product(range(0, k), repeat=len(tree[v]) - 1):
            last = k - sum(sm) - 1
            if last < 0:
                continue
            sm = list(sm) + [last]

            bad = False
            for u, val in zip(tree[v], sm):
                if val != 0 and useless[u]:
                    bad = True
                    break
            if bad:
                continue

            res = armies[v] - 1
            resd = dist[v]
            for i in range(len(tree[v])):
                if sm[i] == 0:
                    continue
                x, d, _ = calc_lazy(tree[v][i], sm[i], dp, tree, armies, dist, useless)
                if x > 0:
                    res += x
                    resd = max(resd, d)
                else:
                    sm[i] = 0

            if res > ans or (res == ans and resd < ansd):
                ans = res
                ansd = resd
                anssm = tuple(sm)
    dp[v][k] = (ans, ansd, anssm)
    return dp[v][k]


def restore_moves(v, k, dp, tree):
    moves = []
    sm = dp[v][k][2]
    for i in range(len(tree[v])):
        if sm[i] == 0:
            continue
        u = tree[v][i]
        moves.extend(restore_moves(u, sm[i], dp, tree))
        moves.append((u, v))
    return moves


INF = 10 ** 9


def get_oriented_armies():
    turn = GG.gamemap.turn
    armies = [GG.armies[v] if vert2tile(v).tile == GG.self else -GG.armies[v] for v in range(len(GG.armies))]
    for v in range(len(armies)):
        if armies[v] >= 0:
            continue
        age = turn - vert2tile(v).last_seen
        armies[v] = -1 + 3 * (armies[v] + 1) / (2 + 2 ** min(age / 2, 100))
    return armies


def calc_utility(is_blocked):
    graph = GG.side_graph
    armies = get_oriented_armies()
    # armies = [GG.armies[v] if vert2tile(v).tile == GG.self else -GG.armies[v] for v in range(len(GG.armies))]

    utility = [0] * len(graph)
    for start in range(len(graph)):
        if is_blocked(start):
            continue
        dist = bfs_limit(start, graph, 15, is_blocked)
        ut = 0
        for (u, d) in dist.items():
            ut += (armies[u] - 1) * 0.75 ** d
        utility[start] = ut
    return utility


def _is_blocked(v, block_general):
    return block_general and tile2vert(GG.my_general) == v


def gather_pre(root, block_general=False):
    graph = GG.side_graph
    dists = dijkstra(root, GG.side_graph, lambda v: _is_blocked(v, block_general), lambda v: 1 + 3 * (
            vert2tile(v).tile != GG.self))
    dists = [d if d is not None else INF for d in dists]
    utility = calc_utility(lambda v: dists[v] == INF)
    bfs_tree = [[] for v in range(len(graph))]
    for v in range(len(graph)):
        if dists[v] == INF:
            continue
        max_ut = -INF
        max_p = None
        mn_dist = min(dists[v] - 1, min(dists[u] for u in graph[v] if dists[u] is not None))
        for u in graph[v]:
            if dists[u] == mn_dist and utility[u] > max_ut:
                max_ut = utility[u]
                max_p = u
        if max_p is not None:
            bfs_tree[max_p].append(v)

    # armies = [GG.armies[v] if vert2tile(v).tile == GG.self else -GG.armies[v] for v in range(len(GG.armies))]
    armies = get_oriented_armies()
    useless = [True] * len(bfs_tree)
    calc_useless(root, bfs_tree, armies, useless)
    return bfs_tree, dists, armies, useless


def gather_time_limit(root, time_limit, block_general=False):
    cell_limit = time_limit + 1

    graph = GG.side_graph
    bfs_tree, dists, armies, useless = gather_pre(root, block_general)

    dp = [dict() for i in range(len(graph))]
    calc_lazy(root, cell_limit, dp, bfs_tree, armies, dists, useless)
    moves = restore_moves(root, cell_limit, dp, bfs_tree)
    return moves, int(dp[root][cell_limit][0])


def gather_army_limit(root, army, cell_range, block_general=False):
    tic = time.time()
    graph = GG.side_graph
    bfs_tree, dists, armies, useless = gather_pre(root, block_general)

    dp = [dict() for i in range(len(graph))]
    gather_pre(root)
    for cl in cell_range:
        calc_lazy(root, cl, dp, bfs_tree, armies, dists, useless)
        if dp[root][cl][0] >= army:
            break
    moves = restore_moves(root, cl, dp, bfs_tree)
    print('------ gather army limit -------', time.time() - tic)
    return moves, int(dp[root][cl][0])

