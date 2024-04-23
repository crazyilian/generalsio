from logic.utils import GG, Phase, tile2vert
from logic import utils
from logic import opening
from logic import moves_queue
from logic import army_gather
from logic import early_search_lines
from logic import search_lines
from logic import plump
from logic import hide_defense
import time


def print_armies():
    for y in range(GG.H):
        for x in range(GG.W):
            tile = GG.gamemap.grid[y][x]
            if utils.is_blocked_vert(y * GG.W + x):
                print(' ##', end=' ')
            else:
                a = tile.army if tile.tile == GG.self else -tile.army
                print("{:>3}".format(a), end=' ')
        print()


def is_almost_finished_attack():
    return GG.phase == Phase.ATTACK_GENERAL and 0 < len(GG.queue) < 10


def make_move(bot, gamemap):
    turn = gamemap.turn
    if turn == 1:
        return
    if turn == 2:
        utils.init(bot, gamemap)
        moves_queue.init()
        hide_defense.init()
        GG.phase = Phase.OPENING
    else:
        utils.update()
    print('turn:', turn, time.time())

    while GG.phase == Phase.OPENING:
        if turn == 50:
            GG.phase = Phase.EARLY_S_LINES
            GG.last_direction = -1
            break
        if turn == 2:
            GG.opening_already_started = False
            opening.get_opening()
        if turn in GG.planned_moves:
            GG.opening_already_started = True
            print("Opening turn:", turn)
            GG.queue.extend_verts(GG.planned_moves[turn], validate=lambda v, u: True)
            GG.queue.exec_all()
        return

    hide_defense.run(not is_almost_finished_attack())
    if not GG.urgent_queue.empty():
        if GG.urgent_queue.exec_until_success():
            GG.queue.clear()
            return

    if GG.phase != Phase.ATTACK_GENERAL and GG.enemy_general is not None:
        GG.queue.clear()
        GG.phase = Phase.ATTACK_GENERAL
        GG.attack_cell_limit = 1

    if (turn == 50 or turn % 50 == 40) and not is_almost_finished_attack():
        moves = plump.get_plump_moves(is_blocked=lambda v: v in GG.queue.sources)
        moves = moves[:10]
        GG.queue.extend_verts(moves, to_left=True)

    while GG.phase == Phase.EARLY_S_LINES:
        if GG.queue.exec_until_success():
            return

        if len(GG.gamemap.tiles[GG.enemy]) >= 1:
            GG.phase = Phase.S_LINES
            GG.search_line_dest = None
            break

        path, moves_gather = early_search_lines.get_moves()
        if len(path) > 0:
            GG.queue.extend_verts(moves_gather)
            GG.queue.extend_path(path)

        if GG.queue.exec_until_success():
            return
        return

    while GG.phase == Phase.S_LINES:
        if len(GG.queue) >= 7 and GG.search_line_dest is not None and search_lines.get_score(GG.search_line_dest) < -1:
            GG.queue.clear()
        if GG.queue.exec_until_success():
            return

        tot_land = gamemap.scores[GG.self]['tiles']
        path, need_army, GG.search_line_dest = search_lines.get_moves()
        print(f'need_army={need_army}, path={path}')
        # print_armies()
        moves_gather, _ = army_gather.gather_army_limit(path[0], need_army, range(5, tot_land + 1, 5))
        GG.queue.extend_verts(moves_gather)
        GG.queue.extend_path(path)

        if GG.queue.exec_until_success():
            return
        return

    cnt_tries = 0
    while GG.phase == Phase.ATTACK_GENERAL:
        if GG.queue.exec_until_success():
            return

        if cnt_tries == 8:
            return
        cnt_tries += 1

        # tot_army = gamemap.scores[GG.self]['total']
        tot_land = gamemap.scores[GG.self]['tiles']

        GG.attack_cell_limit *= 2
        if GG.attack_cell_limit > tot_land * 2:
            GG.attack_cell_limit = 8

        enemy_army = GG.enemy_general.army
        GG.armies[tile2vert(GG.enemy_general)] = 0
        moves_gather, collected_army = army_gather.gather_time_limit(utils.tile2vert(GG.enemy_general), GG.attack_cell_limit)
        GG.armies[tile2vert(GG.enemy_general)] = enemy_army
        collected_army += 1
        expected_enemy_army = enemy_army + (turn + len(moves_gather)) // 2 - GG.enemy_general.last_seen // 2
        print(f'enemy_army={enemy_army}, len(moves_gather)={len(moves_gather)}, enemy_general.last_seen={GG.enemy_general.last_seen}')
        print(f'expected_enemy_army={expected_enemy_army}, collected_army={collected_army}')

        if collected_army - expected_enemy_army <= 0 and GG.attack_cell_limit * 2 < tot_land * 2:
            # if useless and can make cell_limit bigger
            continue

        print('moves gather:', moves_gather)
        GG.queue.extend_verts(moves_gather)
