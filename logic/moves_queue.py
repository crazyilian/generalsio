from collections import deque
from logic.utils import GG, vert2tile


class Multiset:
    def __init__(self):
        self.st = dict()

    def add(self, x):
        self.st[x] = self.st.get(x, 0) + 1

    def remove(self, x):
        cnt = self.st.get(x, 0)
        if self.st.get(x) == 1:
            self.st.pop(x)
        elif cnt > 1:
            self.st[x] = cnt - 1

    def __contains__(self, item):
        return item in self.st


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


def default_validate(v, u, is50):
    a = GG.armies[v] - 1 if not is50 else GG.armies[v] // 2
    return a > 0 and vert2tile(v).tile == GG.self


class MovesQueue:
    def __init__(self, bot):
        self.bot = bot
        self.moves = deque()
        self.last_move = None
        self.sources = Multiset()

    def extend_verts(self, moves, validate=None, is50=False, to_left=False):
        if validate is not None:
            validate3 = lambda v, u, fifty: validate(v, u)
        else:
            validate3 = default_validate
        self.extend([Move(v, u, is50, validate3) for v, u in moves], to_left)

    def extend(self, moves, to_left=False):
        if to_left:
            self.moves.extendleft(moves[::-1])
        else:
            self.moves.extend(moves)
        for mv in moves:
            self.sources.add(mv.v)

    def extend_path(self, path, is50=False, validate=None):
        moves = []
        for i in range(1, len(path)):
            moves.append((path[i - 1], path[i]))
        self.extend_verts(moves[:1], validate, is50=is50)
        self.extend_verts(moves[1:], validate, is50=False)

    def clear(self):
        self.moves.clear()

    def __len__(self):
        return len(self.moves)

    def exec(self):
        if len(self.moves) == 0:
            return False
        self.last_move: Move = self.moves.popleft()
        self.sources.remove(self.last_move.v)
        if not self.last_move.validate(*self.last_move.data()):
            print("Queue validation failed:", *self.last_move.data_tile())
            return False
        return self.bot.place_move(*self.last_move.data_tile())

    def exec_until_success(self):
        while len(self.moves) > 0:
            if self.exec():
                return True
        return False

    def exec_all(self):
        while len(self.moves) > 0:
            self.exec()

    def empty(self):
        return len(self.moves) == 0


def init():
    GG.queue = MovesQueue(GG.bot)
    GG.urgent_queue = MovesQueue(GG.bot)
