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


def get_number_lines(moves):
    return len(moves) - (len(moves) > 0 and moves[0] is None)


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
    parsed_openings = json.load(f)

# make parsed_openings tuples and add 1 wait before opening if needed
correct_openings = []
for moves in parsed_openings:
    moves = tuple(tuple(move) for move in moves)
    if check_correct(moves):
        correct_openings.append(moves)
    elif check_correct((None,) + moves):
        correct_openings.append((None,) + moves)

# add up to 3-turn suffixes to all openings
for moves in correct_openings:
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
                correct_openings.append(new_moves)

# filter only useful openings, try adding opening prefix if opening was not added
filtered_openings = []
for moves in correct_openings:
    while True:
        while len(moves) > 0 and (moves[-1] is None or moves[-1][1] == 0):
            moves = moves[:-1]
        if len(moves) == 0:
            break
        land = get_land(moves)
        side = get_sides(moves)
        min_inside = get_min_inside(moves)
        if len(moves) <= 6 and (land >= 23 or
                                (land >= 17 and len(moves) == 2 and side == 1) or
                                (land >= 18 and min_inside >= 5 and side == 1) or
                                (land >= 21 and min_inside >= 3 and side == 1) or
                                (land >= 21 and min_inside >= 5 and side == 2) or
                                (land >= 22 and min_inside >= 3 and side == 2) or
                                (land >= 20 and min_inside >= 7 and side == 2)):
            filtered_openings.append(moves)
            break
        moves = moves[:-1]

# remove duplicate openings
filtered_openings = list(set(filtered_openings))

# remove opening if it is a prefix of any other opening
openings = []
for i in range(len(filtered_openings)):
    moves1 = filtered_openings[i]
    for j in range(len(filtered_openings)):
        if i == j:
            continue
        moves2 = filtered_openings[j]
        n = len(moves1)
        if n <= len(moves2) and moves1[:n - 1] == moves2[:n - 1] and moves1[n - 1][0] == moves2[n - 1][0] and \
                moves1[n - 1][1] <= moves2[n - 1][1]:  # 1 is prefix of 2
            break

    else:  # 1 is prefix of nothing
        openings.append(filtered_openings[i])

# order openings

sort_cmps = [
    lambda moves: -get_land(moves),  # maximize land
    lambda moves: get_number_lines(moves),  # minimize number of lines
    lambda moves: (sorted(-move[1] for move in moves if move is not None) + [0, 0])[1],  # maximize second maximum
    lambda moves: tuple(move if move is not None else (-1, -1) for move in moves)  # no unspecified behavior
]


def sort_openings(openings):
    openings.sort(key=lambda moves: tuple(cmp(moves) for cmp in sort_cmps))


def reorder_statistics(openings, statistics_file):
    global sort_cmps

    with open(statistics_file) as f:
        opening_records = list(map(int, f.read().strip().split()))
    statistics = dict()
    for record in opening_records:
        statistics[openings[record]] = statistics.get(openings[record], 0) + 1

    sort_cmps = [lambda moves: -statistics.get(moves, 0)] + sort_cmps
    sort_openings(openings)


sort_openings(openings)
reorder_statistics(openings, os.path.join(curdir, "opening_statistics.txt"))
reorder_statistics(openings, os.path.join(curdir, "opening_statistics2.txt"))

# print openings count
cnts = {}
for moves in openings:
    land = get_land(moves)
    side = get_sides(moves)
    if land not in cnts:
        cnts[land] = {1: 0, 2: 0, 3: 0, 4: 0}
    cnts[land][side] += 1

print("openings:", len(openings))
