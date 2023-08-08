from .measurement_management import *
import yaml
# import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Union
import queue
# from numba import njit

import multiprocessing
import math
from skimage import transform as tf
from enum import Enum


class Rates(Action):
    def __init__(self, integration_time):
        super().__init__()
        self.prev_time = 0
        self.init_time = 0
        self.init = True
        # print("coinc rate: ", round(coincidence/delta_time), 
        # "singles_1_rate: ", round(len(hist1)/delta_time), 
        # "singles_2_rate: ", round(len(hist2)/delta_time))
        self.coinc_rate = []
        self.singles_1_rate = []
        self.singles_2_rate = []
        self.integration_time = integration_time

    def evaluate(self, current_time, counts, **kwargs):
        if self.init:
            self.prev_time = current_time
            self.init_time = current_time
            self.init = False
            return {"state": "integrating"}
        delta_time = current_time - self.prev_time

        self.singles_1_rate.append(len(kwargs["hist_tags_1"])/delta_time)
        self.singles_2_rate.append(len(kwargs["hist_tags_2"])/delta_time)
        self.coinc_rate.append(kwargs["coincidences"]/delta_time)

        if (current_time - self.init_time) > self.integration_time:
            print("finished. Coinc rate: ", round(float(np.average(self.coinc_rate))))
            return {"state": "finished",
                    "coincidence rate": self.coinc_rate,
                    "singles_1_rate": self.singles_1_rate,
                    "singels_2_rate": self.singles_2_rate}
        else:
            return {"state": "integrating"}
        


class RatesAndPowers(Action):
    def __init__(self, vsource, power, int_time):
        super().__init__()
        self.add_action(SetPower(power, vsource, 1))
        self.add_action(Wait(10))
        self.add_action(Rates(int_time))



class TimeWalkComparison(Action):
    """
    Used for collecting coincidence and singles rates with and without time walk correction, or 
    just using a dead time. Used to show how much higher coincidence rates you can reach with 
    time walk correction. 
    """
    def __init__(self, vsource):
        super().__init__()


        powers = np.arange(1.5, 5, .2).tolist()
        powers = [round(power,2) for power in powers]
        for power in powers:
            self.add_action(RatesAndPowers(vsource, power, 3))

        self.enable_save("comparison_dead_time")