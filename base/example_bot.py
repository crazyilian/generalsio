from random import choice
from base import run_private


def make_move(bot, gamemap):
    shoud_attack_funcs = [
        lambda neigh: neigh.isEmpty() and not neigh.isCity,
        lambda neigh: not neigh.isSelf(),
        lambda neigh: any(not n1.isSelf() for n1 in neigh.neighbors()),
        lambda neigh: any(any(not n2.isSelf() for n2 in n1.neighbors()) for n1 in neigh.neighbors()),
        lambda neigh: True,
    ]

    for should_attack in shoud_attack_funcs:
        pairs = []
        for source in gamemap.tiles[gamemap.player_index]:  # Check Each Owned Tile
            if source.army >= 2:  # Find One With Armies
                for neigh in source.neighbors(cities=True):
                    if should_attack(neigh):
                        pairs.append((source, neigh))
        if len(pairs) > 0:
            bot.place_move(*choice(pairs))
            return


userid = ""  # Anonymous if random string. Public tester bot if empty. To log in check dev console at bot.generals.io.
username = "[Bot] dsgfhjnkl"  # Only used if the logged in account still does not have a username.
roomid = "keklol228"  # id from url to join and random string to create

run_private(make_move, userid, roomid, username)
