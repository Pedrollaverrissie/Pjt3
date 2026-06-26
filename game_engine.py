import threading
import time
import random


class AviatorGame:

    def __init__(self):

        self.multiplier = 1.00
        self.status = "waiting"
        self.round_id = 1

        self.current_crash = self.generate_crash()
        self.next_crash = self.generate_crash()

        self.countdown = 5

    def generate_crash(self):

        return round(random.uniform(1.10, 12.00), 2)

    def game_loop(self):

        while True:

            # WAITING
            self.status = "waiting"

            for i in range(5,0,-1):

                self.countdown = i

                time.sleep(1)

            # START ROUND
            self.status = "flying"

            self.multiplier = 1.00

            while self.multiplier < self.current_crash:

                self.multiplier += 0.02

                time.sleep(0.05)

            # CRASH
            self.status = "crashed"

            time.sleep(2)

            self.round_id += 1

            self.current_crash = self.next_crash

            self.next_crash = self.generate_crash()


game = AviatorGame()

thread = threading.Thread(target=game.game_loop)

thread.daemon = True

thread.start()









