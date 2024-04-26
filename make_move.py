from logic.utils import GG, Phase
from logic import utils
from logic import opening
from logic import army_gather
from logic import early_search_lines
from logic import search_lines
from logic import plump
from logic import hide_defense
from logic import capture_city
from logic import moves_queue
import time


def is_almost_finished_attack():
    if GG.phase != Phase.ATTACK_GENERAL:
        return False
    return 0 < len(GG.queue) < 10 or (len(GG.queue) == 0 and GG.gamemap.turn < GG.attack_phase_start_turn + 10)


def make_move(bot, gamemap):
    turn = gamemap.turn
    if turn == 1:
        return
    if turn == 2:
        utils.init(bot, gamemap)
        hide_defense.init()
        capture_city.init()
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
            GG.queue.extend_verts(GG.planned_moves[turn], validate=lambda v, u, is50: True)
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
        GG.attack_phase_start_turn = turn

    if (turn == 50 or turn % 50 == 40) and not is_almost_finished_attack():
        moves = plump.get_plump_moves(is_blocked=lambda v: v in GG.queue.sources)
        moves = moves[:5] if turn == 50 else moves[:10]
        GG.queue.extend_verts(moves, policy50=moves_queue.Policy50.TRY, to_left=True, validate=plump.validate)

    if turn >= 300 + 150 * len(GG.my_cities) and len(GG.queue) == 0 and not is_almost_finished_attack():
        moves = capture_city.get_capture_moves()
        if len(moves) > 0:
            print('----- CAPTURING CITY ----')
            print(moves)
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
        break

    while GG.phase == Phase.S_LINES:
        if (len(GG.queue) >= 5 and GG.search_line_dest is not None
                and search_lines.get_score(GG.search_line_dest) < GG.stop_search_score):
            GG.queue.clear()
        if GG.queue.exec_until_success():
            return

        tot_land = gamemap.scores[GG.self]['tiles']
        path, need_army, GG.search_line_dest = search_lines.get_moves()
        GG.stop_search_score = min(-1, search_lines.get_score(GG.search_line_dest) - 1.5)
        print(f'need_army={need_army}, path={path}')
        moves_gather, _ = army_gather.gather_army_limit(path[0], need_army, range(5, tot_land + 1, 5))
        GG.queue.extend_verts(moves_gather)
        GG.queue.extend_path(path)

        if GG.queue.exec_until_success():
            return
        break

    while GG.phase == Phase.ATTACK_GENERAL:
        if GG.queue.exec_until_success():
            return
        moves_gather, collected_army = army_gather.gather_army_limit(
            utils.tile2vert(GG.enemy_general),
            1,
            [1, 2, 4, 8, 16, 24, 32, 48, 64, 128, 256],
            target_increase=0.5
        )
        print('moves gather:', moves_gather)
        GG.queue.extend_verts(moves_gather)

        if GG.queue.exec_until_success():
            return
        break

    print('NO MOVES, PLUMPING 1')
    moves = plump.get_plump_moves(is_blocked=lambda v: v in GG.queue.sources, limit=1)
    GG.queue.extend_verts(moves, policy50=moves_queue.Policy50.TRY, to_left=True, validate=plump.validate)
    GG.queue.exec_until_success()
