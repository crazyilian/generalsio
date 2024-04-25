from collections import deque
from logic.utils import GG, vert2tile
from enum import Enum


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


class Policy50(Enum):
    NO = 0
    YES = 1
    TRY = 2


class Move:
    def __init__(self, v, u, policy50, validate_):
        self.v = v
        self.u = u
        self.policy50 = policy50
        self.validate_ = validate_

    def tiles(self):
        return vert2tile(self.v), vert2tile(self.u)

    def validate(self, is50):
        return self.validate_(self.v, self.u, is50)


def validate_default(v, u, is50):
    a = GG.armies[v] - 1 if not is50 else GG.armies[v] // 2
    return a > 0 and vert2tile(v).tile == GG.self


class MovesQueue:
    def __init__(self):
        self.moves = deque()
        self.last_move = None
        self.sources = Multiset()

    def extend_verts(self, moves, policy50=Policy50.NO, to_left=False, validate=validate_default):
        self.extend([Move(v, u, policy50, validate) for v, u in moves], to_left)

    def extend(self, moves, to_left=False):
        if to_left:
            self.moves.extendleft(moves[::-1])
        else:
            self.moves.extend(moves)
        for mv in moves:
            self.sources.add(mv.v)

    def extend_path(self, path):
        moves = []
        for i in range(1, len(path)):
            moves.append((path[i - 1], path[i]))
        self.extend_verts(moves)

    def clear(self):
        self.moves.clear()

    def __len__(self):
        return len(self.moves)

    def exec(self):
        if len(self.moves) == 0:
            return False
        self.last_move: Move = self.moves.popleft()
        self.sources.remove(self.last_move.v)

        if self.last_move.policy50 == Policy50.NO:
            go = 100 * self.last_move.validate(False)
        elif self.last_move.policy50 == Policy50.YES:
            go = 50 * self.last_move.validate(True)
        else:
            if self.last_move.validate(True):
                go = 50
            elif self.last_move.validate(False):
                go = 100
            else:
                go = 0
        if go == 0:
            print("Queue validation failed:", *self.last_move.tiles(), self.last_move.policy50)
            return False
        return GG.bot.place_move(*self.last_move.tiles(), go == 50)

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
