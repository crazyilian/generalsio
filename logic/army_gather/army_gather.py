import itertools

from logic.utils import dijkstra, bfs_limit, GG, vert2tile, tile2vert
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
    if len(tree[v]) >= 1:
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
        tile = vert2tile(v)
        if armies[v] >= 0 or tile.turn_captured == 0:
            continue
        age = turn - tile.last_seen
        generated = ((age + 1) ** 0.5 - 1) * (2 if tile.isGeneral or tile.isCity else 0.125)
        armies[v] = -1 + 3 * (armies[v] + 1) / (2 + 2 ** min(age / 2, 100)) - generated
    return armies


def calc_utility(is_blocked, graph):
    armies = get_oriented_armies()

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


def gather_pre(root, block_general, graph):
    dists = dijkstra(root, graph, lambda v: _is_blocked(v, block_general), lambda v: 1 + 3 * (
            vert2tile(v).tile != GG.self))
    dists = [d if d is not None else INF for d in dists]
    utility = calc_utility(lambda v: dists[v] == INF, graph)
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

    armies = get_oriented_armies()
    useless = [True] * len(bfs_tree)
    calc_useless(root, bfs_tree, armies, useless)
    return bfs_tree, dists, armies, useless


def gather_time_limit(root, time_limit, block_general=False, graph=None):
    if graph is None:
        graph = GG.side_graph_cities

    cell_limit = time_limit + 1

    bfs_tree, dists, armies, useless = gather_pre(root, block_general, graph)

    dp = [dict() for i in range(len(graph))]
    calc_lazy(root, cell_limit, dp, bfs_tree, armies, dists, useless)
    moves = restore_moves(root, cell_limit, dp, bfs_tree)
    return moves, int(dp[root][cell_limit][0])


def gather_army_limit(root, army, cell_range, block_general=False, graph=None, target_increase=0):
    if graph is None:
        graph = GG.side_graph_cities

    tic = time.time()
    bfs_tree, dists, armies, useless = gather_pre(root, block_general, graph)

    dp = [dict() for i in range(len(graph))]

    best_cl, best_collected, best_moves = None, None, None
    for cl in cell_range:
        calc_lazy(root, cl, dp, bfs_tree, armies, dists, useless)
        moves = restore_moves(root, cl, dp, bfs_tree)
        collected = dp[root][cl][0] - len(moves) * target_increase
        if best_cl is None or best_collected < collected:
            best_cl, best_collected, best_moves = cl, collected, moves
        if collected >= army:
            break
    print('------ gather army limit -------', time.time() - tic)
    return best_moves, best_collected
