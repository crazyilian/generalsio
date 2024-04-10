from logic.utils import GG, Phase
from logic import utils
from logic import opening
from logic import moves_queue
from logic import army_gather
from logic import early_search_lines
from logic import search_lines


def hide_general():
    if GG.my_general_exposed or not GG.urgent_queue.empty():
        return
    x0, y0 = GG.my_general.x, GG.my_general.y
    max_enemy_army = 0
    max_dx, max_dy = None, None
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        x = x0 + dx * 2
        y = y0 + dy * 2
        if x < 0 or GG.W <= x or y < 0 or GG.H <= y or utils.is_blocked_vert((y0 + dy) * GG.W + x0 + dx):
            continue
        tile = GG.gamemap.grid[y][x]
        if tile.army > max_enemy_army and tile.tile == GG.enemy:
            max_enemy_army = tile.army
            max_dx = dx
            max_dy = dy
    if max_enemy_army == 0:
        return
    print(f'hide general: max_enemy_army={max_enemy_army}')
    dx, dy, a = max_dx, max_dy, max_enemy_army
    b = GG.gamemap.grid[y0 + dy][x0 + dx].army
    g = GG.my_general.army

    if g - 1 + b >= a:  # hide
        is50 = g // 2 + b - 1 > a
        G = y0 * GG.W + x0
        B = (y0 + dy) * GG.W + x0 + dx
        A = (y0 + 2 * dy) * GG.W + x0 + 2 * dx
        GG.urgent_queue.extend_path([G, B, A, B, G], is50=is50)
    else:  # try defense
        moves_gather = army_gather.gather_time_limit(utils.tile2vert(GG.my_general), 3)
        GG.urgent_queue.extend_verts(moves_gather)


def make_move(bot, gamemap):
    turn = gamemap.turn
    if turn == 1:
        return
    if turn == 2:
        utils.init(bot, gamemap)
        moves_queue.init()
        GG.phase = Phase.OPENING
    else:
        utils.update()
    print('turn:', turn)

    while GG.phase == Phase.OPENING:
        if turn == 50:
            GG.phase = Phase.EARLY_S_LINES
            GG.last_direction = -1
            GG.cnt_early_lines = 0
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

    hide_general()
    if not GG.urgent_queue.empty():
        if GG.urgent_queue.exec_until_success():
            return

    if GG.phase != Phase.ATTACK_GENERAL and GG.enemy_general is not None:
        GG.queue.clear()
        GG.phase = Phase.ATTACK_GENERAL
        GG.attack_cell_limit = 2

    while GG.phase == Phase.EARLY_S_LINES:
        if GG.queue.exec_until_success():
            return

        if (GG.cnt_early_lines >= 2 and len(GG.gamemap.tiles[GG.enemy]) >= 1) \
                or (GG.cnt_early_lines >= 1 and len(GG.gamemap.tiles[GG.enemy]) >= 5):
            GG.phase = Phase.S_LINES
            break
        GG.cnt_early_lines += 1

        path, moves_gather = early_search_lines.get_moves()
        if len(path) > 0:
            GG.queue.extend_verts(moves_gather)
            GG.queue.extend_path(path)

        if GG.queue.exec_until_success():
            return
        return

    while GG.phase == Phase.S_LINES:
        if GG.queue.exec_until_success():
            return

        tot_land = gamemap.scores[GG.self]['tiles']
        path, need_army = search_lines.get_moves()
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

        if cnt_tries == 7:
            return
        cnt_tries += 1

        # tot_army = gamemap.scores[GG.self]['total']
        tot_land = gamemap.scores[GG.self]['tiles']

        GG.attack_cell_limit *= 2
        if GG.attack_cell_limit > tot_land * 2:
            GG.attack_cell_limit = 8

        moves_gather = army_gather.gather_time_limit(utils.tile2vert(GG.enemy_general), GG.attack_cell_limit)
        print('moves gather:', moves_gather)
        GG.queue.extend_verts(moves_gather)
