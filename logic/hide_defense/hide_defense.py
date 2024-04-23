from logic.utils import GG, verts_closer_than, vert2tile, seen_by, tile2vert
from sortedcontainers import SortedSet
from logic.army_gather import gather_time_limit, gather_army_limit
from logic.plump import get_plump_moves


def dijkstra(starts, graph, is_blocked=lambda v: False, get_weight=lambda v, u: 1, dist_limit=float('inf')):
    dist = dict()
    pred = dict()
    Q = SortedSet()
    for s in starts:
        dist[s] = (0, 0)
        Q.add((0, 0, s))
    while len(Q) > 0:
        d1, dw, v = Q.pop(0)
        for u in graph[v]:
            if is_blocked(u):
                continue
            nd1 = d1 + 1
            ndw = dw + get_weight(v, u)
            old_dist = dist.get(u, (nd1 + 1, -1))
            if old_dist > (nd1, ndw) and nd1 <= dist_limit:
                Q.discard((*old_dist, u))
                dist[u] = (nd1, ndw)
                pred[u] = v
                Q.add((nd1, ndw, u))
    return dist, pred


def get_nearest_enemy(enemies, dist):
    nearest_enemy = None
    for v in enemies:
        assert v in dist
        if nearest_enemy is None or (dist[v][0] // 2, v) < (dist[nearest_enemy][0] // 2, nearest_enemy):
            nearest_enemy = v
    return nearest_enemy


def get_worst_enemy(starts, dist_limit, enemies):
    dist, pred = dijkstra(starts, GG.side_graph,
                          get_weight=lambda v, u: (GG.armies[v] + 1 if vert2tile(v).tile == GG.self
                                                   else int(vert2tile(v).tile < 0)),
                          dist_limit=dist_limit)
    worst_enemy = None
    worst_army_delta = -10 ** 9
    for v in enemies:
        assert v in dist
        army_delta = GG.armies[v] - dist[v][1]
        if worst_enemy is None or (army_delta, -dist[v][0]) > (worst_army_delta, -dist[worst_enemy][0]):
            worst_enemy = v
            worst_army_delta = army_delta
    return dist, pred, worst_enemy


def attack_nearest(enemies, dist, dist_limit, is_new_status):
    print('attack nearest')
    nearest_enemy = get_nearest_enemy(enemies, dist)
    if nearest_enemy is None:
        print('nearest_enemy=None')
        return
    print(f'nearest_enemy={vert2tile(nearest_enemy)}')
    moves, _ = gather_army_limit(nearest_enemy, 1, range(1, dist_limit + 1))
    if len(moves) == 0:
        return

    if is_new_status:
        # wait while updated=False (works because urgent_queue clears if updated=True)
        affected_verts = set()
        for v, u in moves:
            affected_verts.add(v)
            affected_verts.add(u)
        plump_moves = get_plump_moves(is_blocked=lambda v: v in affected_verts, limit=1)
        moves = plump_moves + moves

    GG.hide_defense_attack = True
    GG.urgent_queue.extend_verts(moves)
    print(f'moves={moves}')
    return


def update_status(enemies):
    GG.hide_defense_enemies, old = dict((v, GG.armies[v]) for v in enemies), GG.hide_defense_enemies
    updated = old != GG.hide_defense_enemies
    if updated or GG.urgent_queue.empty():
        GG.hide_defense_attack = False
        GG.urgent_queue.clear()
    return updated


def get_enemies(dist_limit):
    enemies = []
    seen_by_general = set(seen_by(tile2vert(GG.my_general)))
    for v in verts_closer_than(dist_limit):
        if (vert2tile(v).tile == GG.enemy and
                (GG.armies[v] - GG.dists_from_general[v] * 2 >= -3 or v in seen_by_general)):
            enemies.append(v)
    return enemies, seen_by_general


def check_general_in_danger(dist_limit):
    enemies, _ = get_enemies(dist_limit)
    if len(enemies) == 0:
        return False
    dist, pred, worst_enemy = get_worst_enemy([tile2vert(GG.my_general)], dist_limit, enemies)
    return GG.armies[worst_enemy] > dist[worst_enemy][1]


def run(soft_attack):
    dist_limit = 10 if GG.my_general_exposed or check_general_in_danger(10) else 4

    enemies, seen_by_general = get_enemies(dist_limit)
    updated = update_status(enemies)

    if len(enemies) == 0 or GG.hide_defense_attack:
        return

    if not GG.my_general_exposed:  # hide
        print('trying hiding')
        # Gener | Mount
        # Mount | .....  <-- in seen_by but very far
        starts = list(seen_by_general)
        dist, pred, worst_enemy = get_worst_enemy(starts, dist_limit, enemies)
        print(f'worst_enemy={vert2tile(worst_enemy)}')

        if GG.armies[worst_enemy] <= dist[worst_enemy][1]:
            # no way to become exposed, attack them
            print('no way to become exposed')
            if soft_attack:
                attack_nearest(enemies, dist, dist_limit, updated)
            return

        gather_dest = worst_enemy
        while gather_dest in pred:
            gather_dest = pred[gather_dest]
        print(f'gather_dest={vert2tile(gather_dest)}')
        moves, nw_army = gather_time_limit(gather_dest, dist[worst_enemy][0])
        nw_army += 1
        if GG.armies[worst_enemy] <= dist[worst_enemy][1] - GG.armies[gather_dest] + nw_army:
            # we can hide
            print('we can hide')
            print(f'moves={moves}')
            GG.urgent_queue.extend_verts(moves[:1])
            return

    # defense
    print('trying defensing')
    dist, pred, worst_enemy = get_worst_enemy([tile2vert(GG.my_general)], dist_limit, enemies)
    print(f'worst_enemy={vert2tile(worst_enemy)}')
    if GG.armies[worst_enemy] <= dist[worst_enemy][1]:
        # no way to be captured
        print('no way to be captured')
        if soft_attack:
            attack_nearest(enemies, dist, dist_limit, updated)
        return
    print('defense')
    if GG.my_general_exposed:
        moves, _ = gather_time_limit(tile2vert(GG.my_general), dist[worst_enemy][0] - 1)
    else:
        need = GG.my_general.army + GG.armies[worst_enemy] - dist[worst_enemy][1]
        moves, _ = gather_army_limit(tile2vert(GG.my_general), need, [1, 2, 3, 4, 6, 8, 10, 12, 15, 18, 21, 25, 30])
    print(f'moves={moves}')
    GG.urgent_queue.extend_verts(moves[:1])


def init():
    GG.hide_defense_enemies = dict()
    GG.hide_defense_attack = False
