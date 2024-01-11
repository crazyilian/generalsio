from base import run_private
from make_move import make_move

userid = ""  # Anonymous if random string. Public tester bot if empty. To log in check dev console at bot.generals.io.
username = "[Bot] dsgfhjnkl"  # Only used if the logged in account still does not have a username.
roomid = "keklol228"  # id from url to join and random string to create

run_private(make_move, userid, roomid, username, 10)
