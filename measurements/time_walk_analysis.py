from .measurement_management import *
import yaml
import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Union
import queue
from numba import njit

import multiprocessing
import math
from skimage import transform as tf
from enum import Enum

class Mode(Enum):
    INTEGRATE = 0
    COMPUTE = 1

@dataclass
class InputData:
    diff_1: np.ndarray
    diff_2: np.ndarray
    hist_1: np.ndarray
    hist_2: np.ndarray
    t_prime_step: int
    period: float
    t_prime_bins: np.ndarray
    hist_bins: np.ndarray
    hist_bin_number: int



@dataclass
class InputMessage:
    data: Union[InputData, None]
    action: str



class TimeWalkRunner(Action):
    def __init__(self):
        super().__init__()

        with open(
            "./measurements/time_walk_analysis.yaml", "r", encoding="utf8"
        ) as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.add_action(
            TimeWalkAnalysis(
                params["analysis_time"],
                params["t_prime_max"],
                params["t_prime_step"],
                params["hist_bin_number"],
            )
        )
        self.enable_save(params["save_name"])


class TimeWalkManager:
    def __init__(self):
        self.hist_2d_1 = None
        self.hist_2d_2 = None

    def process(self, message: InputMessage):
        if message.action == Mode.INTEGRATE:
            self.integrate_histograms(message.data)
            return

        if message.action == Mode.COMPUTE:
            return_data = self.process_histograms()
            return return_data

    def integrate_histograms(self, d: InputData):

        input_1 = np.array([d.diff_1, d.hist_1])
        input_2 = np.array([d.diff_2, d.hist_2])

        if self.hist_2d_1 is None:
            self.hist_2d_1, edges = np.histogramdd(
                    input_1.T, bins=[d.t_prime_bins, d.hist_bins]
                )
            self.hist_2d_2, edges = np.histogramdd(
                input_2.T, bins=[d.t_prime_bins, d.hist_bins]
            )


            self.period = d.period
            self.t_prime_step = d.t_prime_step
            self.hist_bin_number = d.hist_bin_number

        else:
            self.hist_2d_1 += np.histogramdd(
            input_1.T, bins=[d.t_prime_bins, d.hist_bins])[0]
            
            self.hist_2d_2 += np.histogramdd(
            input_2.T, bins=[d.t_prime_bins, d.hist_bins])[0]


    def process_histograms(self):

        # skew_and_kernel(data_d.results[0].hist_2d_1, 244.5558, 243, 500)

        match_1, offset_array_1 = skew_and_kernel(self.hist_2d_1, self.period, self.hist_bin_number, self.t_prime_step)
        match_2, offset_array_2 = skew_and_kernel(self.hist_2d_2, self.period, self.hist_bin_number, self.t_prime_step)

        fig, ax = plt.subplots(1,2,figsize=(7,5))

        # Display the data as an image
        ax[0][0].imshow(match_1, cmap='viridis')
        ax[0][1].plot(offset_array_1)


        ax[1][0].imshow(match_2, cmap='viridis')
        ax[1][1].plot(offset_array_2)

        # Save the figure as an image file
        fig.savefig('time_walk_results.png')

        return offset_array_1, offset_array_2





@njit
def sum_absolute_differences(input_array, kernel):
    offset_off = 0
    old_offset = -1

    offsets = np.zeros(np.shape(input_array)[0])
    new  = np.zeros(np.shape(input_array))
    for i, row in enumerate(input_array):
        for of in range(0,np.shape(input_array)[1]):
            new[i,of] = np.nansum(np.abs(np.roll(kernel, of) - (row/np.max(row))))

        
        offset = np.argmin(new[i])
        
        if old_offset == -1:
            old_offset = offset

        # these handle period jumps
        if (offset - old_offset) > 240:
            offset_off = offset_off - 243

        if (offset - old_offset) < -240:
            offset_off = offset_off + 243
        
        offsets[i] = offset + offset_off
            

        old_offset = offset

    return new, offsets

def skew_and_kernel(hist_array, hist_period, hist_bins, delta_t_prime):

    angle = math.atan((hist_period/hist_bins)/delta_t_prime)
    # print(angle)
    afine_tf = tf.AffineTransform(
    np.array([[1, 0, 0], [-angle, 1, 0], [0, 0, 1]]))
    # Apply transform to image data
    modified = tf.warp(hist_array, inverse_map=afine_tf)

    kernel = np.average(modified[-20:],axis=0)
    kernel = kernel/np.max(kernel)

    correlated_array, offsets = sum_absolute_differences(modified, kernel)

    return correlated_array, offsets


def time_walk_event_loop(input_queue, output_queue):
    manager = TimeWalkManager()

    while True:
        data = input_queue.get()
        if data is None:
            print("received none. Exiting.")
            break
        manager.process(data)






class TimeWalkAnalysis(Action):
    def __init__(
        self, int_time, t_prime_max, t_prime_step, hist_bin_number, progress_bar=True
    ):
        super().__init__()
        self.progress_bar = progress_bar
        self.int_time = int_time
        self.t_prime_max = t_prime_max
        self.t_prime_step = t_prime_step
        self.t_prime_bins = np.arange(1, t_prime_max, t_prime_step)
        self.hist_bin_number = hist_bin_number
        self.hist_bins = np.linspace(0, 244.5558, hist_bin_number)
        self.hist_2d = None
        self.period = None
        self.delta_time = 0
        self.pbar_ratio = 0

        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=time_walk_event_loop, args=(self.input_queue, self.output_queue))
        self.process.start()

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.n}")

        diff_1 = kwargs.get("diff_1")
        diff_2 = kwargs.get("diff_2")

        hist_1 = kwargs.get("hist_tags_1")
        hist_2 = kwargs.get("hist_tags_2")

        if self.init_time == -1:
            self.init_time = current_time

            if self.progress_bar:
                self.progress_bar = tqdm(total=100)

            self.period = kwargs.get("period")
            if self.period is None:
                self.period = 244.5558
                print("valid period not found. using stand-in value")
                self.hist_bins = np.linspace(0, self.period, self.hist_bin_number)

            if self.label != "default_label":
                print(f"################################## Beginning: {self.label}")
        
        d = InputData(diff_1=diff_1,
                           diff_2=diff_2,
                           hist_1=hist_1,
                           hist_2=hist_2,
                           t_prime_step=self.t_prime_step,
                           period=self.period,
                           t_prime_bins=self.t_prime_bins,
                           hist_bins=self.hist_bins,
                           hist_bin_number=self.hist_bin_number)
        msg = InputMessage(d, Mode.INTEGRATE)

        self.input_queue.put(msg)
        print(f"Input queue length: {self.input_queue.qsize()}")


        if self.progress_bar:
            r = round(((current_time - self.init_time) / self.int_time) * 100)
            if self.pbar_ratio != r:
                self.pbar_ratio = r
                self.progress_bar.update(1)


        if (current_time - self.init_time) > self.current_value(self.int_time):
            # end of integration period. Being computation
            logger.info(
                f"     {self.n}: Finishing Integration. Time Integrating: {round(self.delta_time,3)}"
            )

            if self.progress_bar:
                self.progress_bar.close()
            self.delta_time = current_time - self.init_time

            # start the time walk final computation using the collected 2D histogram
            self.input_queue.put(InputMessage(None, Mode.COMPUTE))

            

            try:
                output_data = self.output_queue.get(False) # non blocking
                print("these are the t prime curves")
                print(output_data)


                self.input_queue.put(None)
                self.process.join()
                self.final_state = {
                    "state": "finished",
                    "name": self.n,
                    "label": self.label,
                    "delta_time": self.delta_time,
                    "period": self.period,
                    "t_prime_max": self.t_prime_max,
                    "t_prime_step": self.t_prime_step,
                }

                return self.final_state

            except queue.Empty:
                # No data available, do something else
                return {"state": "computing"}
        

        return {"state": "integrating"}
