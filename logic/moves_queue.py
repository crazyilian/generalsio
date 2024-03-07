from collections import deque
from logic.utils import GG, vert2tile


class Move:
    def __init__(self, v, u, is50, validate):
        self.v = v
        self.u = u
        self.is50 = is50
        self.validate = validate

    def data(self):
        return self.v, self.u, self.is50

    def data_tile(self):
        return vert2tile(self.v), vert2tile(self.u), self.is50


class MovesQueue:
    def __init__(self, bot):
        self.bot = bot
        self.moves = deque()
        self.last_move = None

    def extend_verts(self, moves, validate=lambda v, u: True):
        validate3 = lambda v, u, is50: not is50 and validate(v, u)
        self.extend([Move(v, u, False, validate3) for v, u in moves])

    def extend(self, moves):
        self.moves.extend(moves)

    def clear(self):
        self.moves.clear()

    def __len__(self):
        return len(self.moves)

    def exec(self):
        if len(self.moves) == 0:
            return False
        self.last_move: Move = self.moves.popleft()
        if not self.last_move.validate(*self.last_move.data()):
            print("Queue validation failed:", *self.last_move.data_tile())
            return False
        return self.bot.place_move(*self.last_move.data_tile())

    def exec_all(self):
        while len(self.moves) > 0:
            self.exec()


def init():
    GG.queue = MovesQueue(GG.bot)
