
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

game = AviatorGame()











