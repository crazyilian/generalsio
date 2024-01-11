from logic.utils import GG
from logic import utils
from logic import opening


def make_move(bot, gamemap):
    if gamemap.turn == 1:
        pass
    elif gamemap.turn == 2:
        utils.init(bot, gamemap)
        opening.init()
        opening.calculate_opening()
        return
    elif gamemap.turn in GG.opening_turns:
        opening.start_opening()
        print("OPENING TURN", gamemap.turn)
        GG.opening_turns[gamemap.turn]()
    elif gamemap.turn == 55:
        bot.surrender()
