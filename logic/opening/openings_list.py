import json
import os

curdir = os.path.dirname(__file__)


def get_turns(moves):
    res = 0
    if moves[0] is None:
        res = 1
        moves = moves[1:]
    return res + moves[0][1] * 3 + sum([move[0] + move[1] for move in moves[1:]])


def get_sides(moves):
    return sum([move[0] == 0 for move in moves if move is not None])


def get_min_inside(moves):
    return min([move[0] for move in moves if move is not None and move[0] != 0] + [1000])


def get_land(moves):
    return sum([move[1] for move in moves if move is not None]) + 1


def check_correct(moves):
    if get_sides(moves) > 4:
        return False
    if moves[0] is None:
        moves = moves[1:]
        turn = 1 + moves[0][1] * 3
        army = (moves[0][1] + 1) // 2
    else:
        turn = moves[0][1] * 3
        army = moves[0][1] // 2
    for move in moves[1:]:
        if army < move[1]:
            return False
        army = (move[0] + move[1] + turn % 2) // 2
        turn += move[0] + move[1]
    return turn <= 50


with open(os.path.join(curdir, 'parsed_openings.json')) as f:
    all_moves = json.load(f)

for i in range(len(all_moves)):  # make it tuples
    all_moves[i] = tuple(tuple(move) for move in all_moves[i])
    if not check_correct(all_moves[i]) and check_correct((None,) + all_moves[i]):
        all_moves[i] = (None,) + all_moves[i]

for moves in all_moves:
    turns = get_turns(moves)
    side = get_sides(moves)
    suffixes = {
        49: [((0, 1),)],
        48: [((0, 2),), ((1, 1),), ((0, 1), (0, 1))],
        47: [((0, 3),), ((0, 2), (0, 1)), ((0, 1), (0, 1), (0, 1)), ((0, 1), (1, 1)), ((1, 2),), ((2, 1),)]
    }
    if turns in suffixes:
        for suffix in suffixes[turns]:
            new_moves = moves + suffix
            if check_correct(new_moves):
                all_moves.append(new_moves)

filtered_moves = []
for moves in all_moves:
    if not check_correct(moves):  # can be incorrect if army was merged in some cell
        continue
    land = get_land(moves)
    while True:
        while len(moves) > 0 and (moves[-1] is None or moves[-1][1] == 0):
            moves = moves[:-1]
        if len(moves) == 0:
            break
        side = get_sides(moves)
        min_inside = get_min_inside(moves)
        if len(moves) <= 6 and (land >= 23 or
                                (land >= 17 and len(moves) == 2 and side == 1) or
                                (land >= 18 and min_inside >= 5 and side == 1) or
                                (land >= 21 and min_inside >= 3 and side == 1) or
                                (land >= 21 and min_inside >= 5 and side == 2) or
                                (land >= 22 and min_inside >= 3 and side == 2) or
                                (land >= 20 and min_inside >= 7 and side == 2)):
            filtered_moves.append(moves)
            break
        else:
            land -= moves[-1][1]
            moves = moves[:-1]

filtered_moves = list(set(filtered_moves))

useful_moves = []
for i in range(len(filtered_moves)):
    moves1 = filtered_moves[i]
    for j in range(len(filtered_moves)):
        if i == j:
            continue
        moves2 = filtered_moves[j]
        n = len(moves1)
        if n <= len(moves2) and moves1[:n - 1] == moves2[:n - 1] and moves1[n - 1][0] == moves2[n - 1][0] and \
                moves1[n - 1][1] <= moves2[n - 1][1]:  # 1 is prefix of 2
            break

    else:  # 1 is prefix of nothing
        useful_moves.append(filtered_moves[i])

useful_moves.sort(key=lambda moves: (
    -get_land(moves),
    sum(move is not None for move in moves),
    (sorted(-move[1] for move in moves if move is not None) + [0, 0])[1],  # maximize second maximum
    tuple(move if move is not None else (-1, -1) for move in moves)
))


def print_cnts(openings):
    cnts = {}
    for moves in openings:
        land = get_land(moves)
        side = get_sides(moves)
        if land not in cnts:
            cnts[land] = {1: 0, 2: 0, 3: 0, 4: 0}
        cnts[land][side] += 1

    for land, sides in cnts.items():
        print(land, sides)


def reorder_statistics(openings, statistics_file):
    with open(statistics_file) as f:
        opening_records = list(map(int, f.read().strip().split()))
    statistics = dict()
    for record in opening_records:
        statistics[openings[record]] = statistics.get(openings[record], 0) + 1

    new_openings = openings.copy()
    new_openings.sort(key=lambda moves: (
        -statistics.get(moves, 0),
        -get_land(moves),
        sum(move is not None for move in moves),
        (sorted(-move[1] for move in moves if move is not None) + [0, 0])[1],  # maximize second maximum
        tuple(move if move is not None else (-1, -1) for move in moves)
    ))
    return new_openings


openings = reorder_statistics(useful_moves, os.path.join(curdir, "opening_statistics.txt"))

print_cnts(openings)

print("openings:", len(openings))
