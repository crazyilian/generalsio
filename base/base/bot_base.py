import logging
import threading
import time
from .client import generals


class GeneralsBot:
    def __init__(self, moveMethod, userid, gameType, username=None, privateRoomID=None, forcestartTimout=None):
        # Save Config
        self._moveMethod = moveMethod
        self._userid = userid
        self._gameType = gameType
        self._username = username
        self._privateRoomID = privateRoomID
        self._forcestartTimout = forcestartTimout

        # ----- Start Game -----
        self._running = True
        self._move_event = threading.Event()
        _create_thread(self._start_game_thread)
        _create_thread(self._start_moves_thread)

        try:
            while self._running:
                time.sleep(1)
            self._exit_game()
        except Exception as e:
            logging.critical(e, exc_info=True)
            self._exit_game()
        except KeyboardInterrupt as e:
            logging.critical("Keyboard Interrupt")
            self._exit_game()
            raise e

    ######################### Handle Updates From Server #########################

    def _start_game_thread(self):
        try:
            # Create Game
            self._game = generals.Generals(self._userid, self._gameType, self._username, self._privateRoomID, self._forcestartTimout)

            # Start Receiving Updates
            for gamemap in self._game.get_updates():
                if not self._running:
                    break
                self._set_update(gamemap)
                if not gamemap.complete:
                    self._move_event.set()  # Permit another move

        except Exception as e:
            logging.critical(e, exc_info=True)

        self._exit_game()

    def _set_update(self, gamemap):
        self._map = gamemap

        # Handle Game Complete
        if gamemap.complete and not self._has_completed:
            logging.info("!!!! Game Complete. Result = " + str(gamemap.result) + " !!!!")
            if '_moves_realized' in dir(self):
                logging.info("Moves: %d, Realized: %d" % (self._map.turn, self._moves_realized))
            self._exit_game()
        self._has_completed = gamemap.complete

    ######################### Game Exit / Timelimit #########################

    def _exit_game(self):
        logging.info("exiting")
        self._move_event.set()
        if self._running and "_game" in dir(self):
            self._game.close()
            self._running = False
        time.sleep(0.2)
        self._move_event.set()

    ######################### Move Generation #########################

    def _start_moves_thread(self):
        try:
            self._moves_realized = 0
            self._move_event.wait()
            while self._running:
                self._make_move()
                self._move_event.clear()
                self._moves_realized += 1
                self._move_event.wait(timeout=10)
        except Exception as e:
            logging.critical(e, exc_info=True)
            self._exit_game()


    def _make_move(self):
        self._moveMethod(self, self._map)

    ######################### Move Making #########################

    def place_move(self, source, dest, move_half=False):
        if self._map.isValidPosition(dest.x, dest.y):
            self._game.move(source.y, source.x, dest.y, dest.x, move_half)
            return True
        return False

    def clear_move_queue(self):
        self._game.clear_move_queue()

    def surrender(self):
        self._game.surrender()


######################### Global Helpers #########################


all_threads = []


def _create_thread(f, daemonThread=True):
    global all_threads
    t = threading.Thread(target=f)
    t.daemon = daemonThread
    t.start()
    all_threads.append((t, f))
    if len(all_threads) > 20:
        all_threads = [tf for tf in all_threads if tf[0].is_alive()]
