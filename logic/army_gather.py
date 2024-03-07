import itertools

from logic.utils import bfs


def calc_lazy(v, k, dp, tree, armies, dist):
    if k == 0:
        return 0, None, None
    if k in dp[v]:
        return dp[v][k]
    ans = armies[v] - 1
    ansd = dist[v]
    anssm = (0,) * len(tree[v])
    for sm in itertools.product(range(0, k), repeat=len(tree[v]) - 1):
        last = k - sum(sm)
        if last < 0:
            continue
        sm = sm + (last,)
        res = armies[v] - 1
        resd = dist[v]
        for i in range(len(tree[v])):
            if sm[i] > 0:
                x, d, _ = calc_lazy(tree[v][i], sm[i], dp, tree, armies, dist)
                res += x
                resd = max(resd, d)
        if res > ans or (res == ans and resd < ansd):
            ans = res
            ansd = resd
            anssm = sm
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


def gather(root, graph, armies, choose_f, cell_limit, is_blocked=lambda v: False):
    dists = [d if d is not None else 10 ** 9 for d in bfs(root, graph, is_blocked)]
    bfs_tree = [[u for u in graph[v] if dists[u] == dists[v] + 1] for v in range(len(graph))]
    dp = [dict() for i in range(len(graph))]
    for k in range(1, cell_limit + 1):
        calc_lazy(root, k, dp, bfs_tree, armies, dists)
    k = choose_f([dp[root].get(i, (0,))[0] for i in range(0, cell_limit + 1)])
    moves = restore_moves(root, k, dp, bfs_tree)
    return moves
