import logging
from . import bot_base
from .client import generals
import time


# Set logging level
logging.basicConfig(level=logging.INFO)


def print_alive_threads():
    print("generals.py threads:")
    for t, f in generals.all_threads:
        if t.is_alive():
            print("Alive:", f)
    print("bot_base.py threads:")
    for t, f in bot_base.all_threads:
        if t.is_alive():
            print("Alive:", f)


def run_private(make_move, userid, roomid, username=None, forcestart_timeout=10):
    try:
        while True:
            bot_base.GeneralsBot(moveMethod=make_move, userid=userid, username=username,
                                 gameType='private', privateRoomID=roomid, forcestartTimout=forcestart_timeout)

            logging.info("\n\n\n")
    except KeyboardInterrupt:
        time.sleep(2)
        print_alive_threads()


def run_1v1(make_move, userid, username=None):
    try:
        while True:
            bot_base.GeneralsBot(moveMethod=make_move, userid=userid, username=username, gameType='1v1')

            logging.info("\n\n\n")
    except KeyboardInterrupt:
        time.sleep(2)
        print_alive_threads()
