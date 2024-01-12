import os
import json


class Moves:
    def __init__(self, game, player, general):
        self.player = player
        self.game = game
        self.opened_land = {general}
        self.last_move = None
        self.moves = []
        self.isbad = False


replays_directory = 'replays_prod/'  # https://dev.generals.io/replays
curdir = os.path.dirname(__file__)
files = os.listdir(replays_directory)
openings = []

for file_ind in range(len(files)):
    if file_ind % 1000 == 0:
        print(file_ind, '/', len(files))
    with open(os.path.join(replays_directory, files[file_ind])) as f:
        data = json.load(f)
    generals = data['generals']
    ops = [Moves(files[file_ind], i, generals[i]) for i in range(len(data['usernames']))]

    # teams[x] is list of players in team number x
    teams = None
    if data['teams'] is not None:
        teams = dict()
        for i in range(len(ops)):
            team = data['teams'][i]
            if team not in teams:
                teams[team] = []
            teams[team].append(i)

    for move in data['moves']:
        if move['turn'] >= 50:
            break
        player = move['index']
        op = ops[player]
        if move['is50']:  # if moving half army
            op.isbad = True
        if op.last_move is not None and op.last_move['turn'] + 1 != move['turn']:  # if wait during opening
            op.isbad = True
        if move['start'] == generals[player]:  # if start new "expanding line"
            op.moves.append([0, 0])
        elif move['start'] != op.last_move['end'] or move['end'] == generals[player]:  # if don't continue line
            op.isbad = True
        if teams is not None:
            for other_player in teams[data['teams'][player]]:
                if other_player == player:
                    continue
                if move['end'] in ops[other_player].opened_land:  # if step on allied territory (get additional army)
                    ops[other_player].isbad = True
                    ops[player].isbad = True
        if move['end'] not in op.opened_land:  # get new land
            op.moves[-1][1] += 1
            op.opened_land.add(move['end'])
        else:  # step on self territory
            op.moves[-1][0] += 1
            if len(op.moves) == 1:
                op.isbad = True
        op.last_move = move
    # filter correct openings and make it tuples
    for op in ops:
        if not op.isbad and len(op.moves) > 0:
            openings.append(tuple((m[0], m[1]) for m in op.moves))

custom_openings = [
    ((0, 13), (0, 6), (0, 3), (0, 2)),  # 4-sided
    ((0, 10), (3, 5), (2, 4), (0, 3), (0, 1), (0, 1)),  # 4-sided 11-6-5-4-2-2 https://youtu.be/CibhyUsZSnk?t=186
    ((0, 10), (3, 5), (0, 5), (0, 2), (1, 1), (0, 1)),  # 4-sided 11-6-6-3-2-2 https://youtu.be/CibhyUsZSnk?t=238
    ((0, 12), (2, 6), (0, 4), (0, 2)),  # 3-sided 13-start
    ((0, 12), (1, 6), (0, 3), (0, 2), (1, 1),),  # 3-sided 13-7-4-3-2 https://youtu.be/CibhyUsZSnk?t=104
    ((0, 11), (3, 5), (1, 4), (0, 3), (0, 1),),  # 3-sided 12-6-5-4-2 https://youtu.be/CibhyUsZSnk?t=129
    ((0, 11), (2, 5), (2, 4), (0, 3), (0, 1)),  # 3-sided 12-6-5-4-2 https://youtu.be/CibhyUsZSnk?t=159
    ((0, 9), (3, 5), (2, 4), (0, 3), (1, 1), (0, 2),),  # 3-sided 10-6-5-4-2-3 https://youtu.be/CibhyUsZSnk?t=211
    ((0, 12), (0, 6), (1, 3), (1, 2), (0, 1),),  # 3-sided
    ((0, 10), (3, 5), (2, 4), (1, 3), (0, 2)),  # 2-sided
    ((0, 13), (0, 6), (1, 3), (0, 1),),  # 3-sided (24 cells) https://generals.io/replays/B9cmvufNb (λx.λy.<3)
    ((0, 12), (0, 6), (0, 3), (1, 1), (1, 1)),  # 3-sided (24 cells) https://generals.io/replays/HYdY5OfEW (λx.λy.<3)
    ((0, 11), (3, 5), (2, 4), (0, 3)),  # 2-sided (24 cells)
    ((0, 10), (4, 5), (2, 4), (2, 3)),  # 1-sided (23 cells)
    ((0, 12), (5, 4), (0, 2), (1, 1)),
    # 1-sided 2-moves optimal
    ((0, 12), (6, 6)),
    ((0, 12), (6, 6)),
    ((0, 12), (7, 6)),
    ((0, 12), (8, 6)),
    ((0, 13), (2, 7)),
    ((0, 13), (3, 7)),
    ((0, 13), (4, 6)),
    ((0, 13), (5, 6)),
    ((0, 13), (6, 5)),
    ((0, 13), (7, 4)),
    ((0, 13), (8, 3)),
    ((0, 14), (0, 7)),
    ((0, 14), (1, 7)),
    ((0, 14), (2, 6)),
    ((0, 14), (3, 5)),
    ((0, 14), (4, 4)),
    ((0, 14), (5, 3)),
    ((0, 14), (6, 2)),
    ((0, 14), (7, 1)),
    ((0, 15), (0, 5)),
    ((0, 15), (1, 4)),
    ((0, 15), (2, 3)),
    ((0, 15), (3, 2)),
    ((0, 15), (4, 1)),
    ((0, 16), (0, 2)),
    ((0, 16), (1, 1))
]

openings = custom_openings + openings
print('total openings:', len(openings))
openings = list(set(openings))
print('different openings:', len(openings))

with open(os.path.join(curdir, 'parsed_openings.json'), 'w') as f:
    json.dump(openings, f)
