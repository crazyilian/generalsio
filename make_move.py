from logic.utils import GG, Phase
from logic import utils
from logic import opening
from logic import plump
from logic import moves_queue
from logic import army_gather


def get_choose_f(total_time_limit):
    def choose_f(t2a):
        best_cells = 0
        best_a = 0
        for cells in range(len(t2a)):
            a = t2a[cells]
            if cells - 1 + a <= total_time_limit and a > best_a:
                best_a = a
                best_cells = cells
        return best_cells

    return choose_f


def make_move(bot, gamemap):
    turn = gamemap.turn
    if turn == 1:
        GG.phase = Phase.R0_PREPARE
    if GG.phase == Phase.R0_PREPARE:
        if turn == 2:
            utils.init(bot, gamemap)
            moves_queue.init()
            opening.init()
            GG.phase = Phase.R1_OPENING
    if turn > 2:
        utils.update()
    if GG.phase == Phase.R1_OPENING:
        if turn == 50:
            plump.init()
            GG.phase = Phase.R2_PLUMP
        elif turn == 2:
            opening.get_opening()
        if turn in GG.opening_moves:
            opening.start_opening()
            print("Opening turn:", turn)
            GG.queue.extend_verts(GG.opening_moves[turn])
            GG.queue.exec_all()
    if GG.phase == Phase.R2_PLUMP:
        GG.first_r2_line = True
        if turn - 50 == 16:
            GG.phase = Phase.R2_LINE
            GG.queue.clear()
        elif not GG.queue.exec():
            GG.queue.clear()
            print("Recalc plump")
            plump.get_plump_moves()
            if len(GG.plump_moves) == 0:
                GG.phase = Phase.R2_LINE
            else:
                GG.queue.extend_verts(GG.plump_moves, plump.can_expand)
                if not GG.queue.exec():
                    print("!!!!!!!!! first plump move validation failed !!!!!!!!!")
    if GG.phase == Phase.R2_LINE:
        if GG.first_r2_line:
            GG.first_r2_line = False
            from random import choice
            v = utils.tile2vert(choice(tuple(gamemap.tiles[GG.self])))
            moves = army_gather.gather(v, GG.side_graph, GG.armies, get_choose_f(100 - turn),
                                       min(100 - turn, len(gamemap.tiles[GG.self])))
            GG.queue.extend_verts(moves)
            GG.queue.exec_all()
