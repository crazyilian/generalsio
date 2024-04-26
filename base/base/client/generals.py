import certifi
import logging
import json
import ssl
import threading
import time
import requests
from websocket import create_connection, WebSocketConnectionClosedException

from .constants import *
from . import map


class Generals(object):
    # mode = "1v1" or "private"
    def __init__(self, userid, mode, username=None, roomid=None, forcestart_timeout=10):
        self._forcestart_timeout = max(0, forcestart_timeout) if mode == "private" else None
        self.userid = userid
        self.username = username
        self.gamemode = mode
        self.roomid = roomid
        self._seen_update = False
        self._move_id = 1
        self._start_data = {}
        self._stars = []
        self._numberPlayers = 0
        self._running = True

        self._connect_and_join(userid, username, mode, roomid)

    def close(self):
        if not self._running:
            return
        try:
            self.send_leave()
        except Exception as e:
            logging.critical(e, exc_info=True)
        self._running = False
        with self._lock:
            self._ws.close()

    ######################### Get updates from server #########################

    def get_updates(self):
        while self._running:
            try:
                msg = self._ws.recv()
                print('new message', time.time())
            except WebSocketConnectionClosedException:
                logging.info("Connection Closed")
                break

            # logging.info("Received message type: {}".format(msg))

            if not msg.strip():
                continue

            # ignore heartbeats and connection acks
            if msg in {"2", "3", "40"}:
                continue

            # remove numeric prefix
            while msg and msg[0].isdigit():
                msg = msg[1:]

            if msg == "probe":
                continue

            msg = json.loads(msg)
            if not isinstance(msg, list):
                continue
            if msg[0] == "error_user_id":
                logging.info("Exit: User already in games queue")
                return
            elif msg[0] == "queue_update":
                self._log_queue_update(msg[1])
            elif msg[0] == "pre_game_start":
                logging.info("pre_game_start")
            elif msg[0] == "game_start":
                self._start_data = msg[1]
            elif msg[0] == "game_update":
                yield self._make_update(msg[1])
            elif msg[0] in ["game_won", "game_lost"]:
                yield self._map.updateResult(msg[0])
            elif msg[0] == "chat_message":
                self._handle_chat(msg[2])
            elif msg[0] == "error_queue_full":
                self.changeToNewRoom()
            elif msg[0] == "error_set_username":
                logging.info("error_set_username: {}".format(msg[1:]))
            elif msg[0] == "game_over":
                logging.info("game_over: {}".format(msg[1:]))
            elif msg[0] == "notify":
                logging.info("notify: {}".format(msg[1:]))
            else:
                logging.info("Unknown message type: {}".format(msg))

    ######################### Make Moves #########################

    def move(self, y1, x1, y2, x2, move_half=False):
        if not self._seen_update:
            raise ValueError("Cannot move before first map seen")

        cols = self._map.cols
        a = y1 * cols + x1
        b = y2 * cols + x2
        self._send(["attack", a, b, move_half, self._move_id])
        self._move_id += 1

    def clear_move_queue(self):
        self._send(["clear_moves"])
        self._move_id = self._map.turn

    def surrender(self):
        self._send(["surrender"])

    ######################### Server -> Client #########################

    def _log_queue_update(self, msg):
        if 'queueTimeLeft' in msg:
            logging.info(
                "Queue (%ds) %s/%s" % (msg['queueTimeLeft'], str(len(msg['numForce'])), str(msg['numPlayers'])))
            return

        self.teams = {}
        if "teams" in msg:
            for i in range(len(msg['teams'])):
                if msg['teams'][i] not in self.teams:
                    self.teams[msg['teams'][i]] = []
                self.teams[msg['teams'][i]].append(msg['usernames'][i])

        if 'map_title' in msg:
            mapname = msg['map_title']
            if mapname and len(mapname) > 1:
                logging.info("Queue [%s] %d/%d %s" % (mapname, msg['numForce'], msg['numPlayers'], self.teams))
                return

        logging.info("Queue %s/%s %s" % (str(len(msg['numForce'])), str(msg['numPlayers']), self.teams))

        numberPlayers = msg['numPlayers']
        if self._numberPlayers != numberPlayers:
            self._numberPlayers = numberPlayers
            if self._forcestart_timeout is not None:
                _spawn(self.send_forcestart, self._forcestart_timeout)

    def _make_update(self, data):
        if not self._seen_update:
            self._seen_update = True
            self._map = map.Map(self._start_data, data)
            logging.info("Joined Game: %s - %s" % (self._map.replay_url, self._map.usernames))
            return self._map
        return self._map.update(data)

    def _handle_chat(self, chat_msg):
        if "username" in chat_msg:
            self.handle_command(chat_msg["text"])
            logging.info("From %s: %s" % (chat_msg["username"], chat_msg["text"]))
        else:
            logging.info("Message: %s" % chat_msg["text"])

    def handle_command(self, msg):
        if any(k in msg.lower().split() for k in START_KEYWORDS):
            self.send_forcestart()
        elif msg.startswith("speed"):
            self.set_game_speed(msg[5:].strip())

    ######################### Client -> Server #########################

    def _endpointWS(self):
        return "wss" + ENDPOINT_BOT + "&transport=websocket"

    def _endpointRequests(self):
        return "https" + ENDPOINT_BOT + "&transport=polling"

    def _getSID(self):
        request = requests.get(self._endpointRequests() + "&t=ObyKmaZ", verify=True)
        result = request.text
        while result and result[0].isdigit():
            result = result[1:]

        msg = json.loads(result)
        sid = msg["sid"]
        self._gio_sessionID = sid
        _spawn(self._verifySID)
        return sid

    def _verifySID(self):
        sid = self._gio_sessionID
        checkOne = requests.post(self._endpointRequests() + "&t=ObyKmbC&sid=" + sid, data="40", verify=True)
        # checkTwo = requests.get(self._endpointRequests() + "&t=ObyKmbC.0&sid=" + sid)
        # logging.debug("Check two: %s" % checkTwo.text)

    def _connect_and_join(self, userid, username, mode, roomid):
        endpoint = self._endpointWS() + "&sid=" + self._getSID()
        logging.debug("Creating connection with endpoint %s: %s" % (endpoint, certifi.where()))
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_verify_locations(certifi.where())
        self._ws = create_connection(endpoint, sslopt={"cert_reqs": ssl.CERT_NONE})
        self._lock = threading.RLock()
        self._ws.send("2probe")
        self._ws.send("5")
        _spawn(self._start_sending_heartbeat)

        if username is not None:
            logging.debug("Setting Username: %s" % username)
            # self._send(["set_username", userid, username, BOT_KEY])
            self._send(["set_username", userid, username])

        logging.info("Joining games")
        self._roomid = None
        if mode == "private":
            self._roomid = roomid
            if roomid is None:
                raise ValueError("roomid must be provided for private games")
            # self._send(["join_private", roomid, userid, BOT_KEY])
            self._send(["join_private", roomid, userid])
        elif mode == "1v1":
            # self._send(["join_1v1", userid, BOT_KEY])
            self._send(["join_1v1", userid])
        else:
            raise ValueError("Invalid mode")

    def _start_sending_heartbeat(self):
        while True:
            try:
                with self._lock:
                    self._ws.send("3")
            except WebSocketConnectionClosedException:
                logging.info("Connection Closed - heartbeat")
                break

            if _sleep_interrupt(19, lambda: not self._running):
                return

    def send_forcestart(self, delay=0):
        # self.set_game_speed("2")
        if _sleep_interrupt(delay, lambda: not self._running):
            return
        self._send(["set_force_start", self._roomid, True])
        logging.info("Sent force start")

    def set_game_speed(self, speed="1"):
        try:
            speed = float(speed)
        except Exception:
            pass
        # if speed in [1, 2, 3, 4]:
        self._send(["set_custom_options", self._roomid, {"game_speed": speed}])

    def send_leave(self):
        self._send(["surrender"])
        self._send(["cancel"])
        self._send(["leave_game"])

    def _send(self, msg, prefix="42"):
        logging.info(f"send: {msg}")
        try:
            with self._lock:
                self._ws.send(prefix + json.dumps(msg))
        except WebSocketConnectionClosedException:
            pass

    ######################### Change Rooms #########################

    def changeToNewRoom(self):
        self.close()
        self.roomid = self.roomid + "x"
        self._connect_and_join(self.userid, self.username, self.gamemode, self.roomid)


all_threads = []


def _spawn(f, *args, **kwargs):
    global all_threads
    t = threading.Thread(target=f, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    all_threads.append((t, f))
    if len(all_threads) > 20:
        all_threads = [tf for tf in all_threads if tf[0].is_alive()]


def _sleep_interrupt(secs, should_stop):
    while secs > 1e-6:
        if should_stop():
            return True
        delay = min(1, secs)
        secs -= delay
        time.sleep(delay)
    return should_stop()
