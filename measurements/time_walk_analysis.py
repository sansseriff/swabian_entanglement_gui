from .measurement_management import *
import yaml
import matplotlib.pyplot as plt
from tqdm import tqdm



class TimeWalkRunner(Action):
    def __init__(self):
        super().__init__()
        self.add_action(TimeWalkAnalysis(20, 300000, 500, 243))


class TimeWalkAnalysis(Action):
    def __init__(self, int_time, t_prime_max, t_prime_step, hist_bin_number, progress_bar=True):
        super().__init__()
        self.progress_bar = progress_bar
        self.int_time = int_time
        self.t_prime_bins = np.arange(1, t_prime_max, t_prime_step)
        self.hist_bin_number = hist_bin_number
        self.hist_bins = np.linspace(0, 244.5558, hist_bin_number)
        self.hist_2d = None
        self.period = None
        self.delta_time = 0
        self.pbar_ratio = 0

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.n}")

        diff_1 = kwargs.get("diff_1")
        diff_2 = kwargs.get("diff_2")

        hist_1 = kwargs.get("hist_tags_1")
        hist_2 = kwargs.get("hist_tags_2")

        input_1 = np.array([diff_1, hist_1])
        input_2 = np.array([diff_2, hist_2])

        if self.init_time == -1:
            self.init_time = current_time

            if self.progress_bar:
                self.progress_bar = tqdm(total = 100)

            self.period = kwargs.get("period")
            if self.period is None:
                self.period = 244.5558
                print("valid period not found. using stand-in value")
                self.hist_bins = np.linspace(0, self.period, self.hist_bin_number)

            # print("shape input: ", np.shape(input_1))
            # print("shape input: ", np.shape(input_1))

            # print(np.shape(diff_1))
            # print(np.shape(hist_1))

            # print(np.shape(diff_2))
            # print(np.shape(hist_2))

            # print("shape of bins: ", np.shape([self.t_prime_bins, self.hist_bins]))
            self.hist_2d_1, edges = np.histogramdd(
                input_1.T, bins=[self.t_prime_bins, self.hist_bins]
            )
            self.hist_2d_2, edges = np.histogramdd(
                input_2.T, bins=[self.t_prime_bins, self.hist_bins]
            )

            if self.label != "default_label":
                print(f"################################## Beginning: {self.label}")
            return {"state": "integrating"}

        if self.progress_bar:
            r = round(((current_time - self.init_time)/self.int_time)*100)
            if self.pbar_ratio != r:
                self.pbar_ratio = r
                self.progress_bar.update(1)

        self.hist_2d_1 += np.histogramdd(
            input_1.T, bins=[self.t_prime_bins, self.hist_bins]
        )[0]
        self.hist_2d_2 += np.histogramdd(
            input_2.T, bins=[self.t_prime_bins, self.hist_bins]
        )[0]

        if (current_time - self.init_time) > self.current_value(self.int_time):
            if self.progress_bar:
                self.progress_bar.close()
            self.delta_time = current_time - self.init_time
            logger.info(
                f"     {self.n}: Finishing. Time Integrating: {round(self.delta_time,3)}"
            )

            # print("shape of result: ", np.shape(self.hist_2d_1))
            # print(
            #     "type: ",
            # )
            self.fig, self.ax = plt.subplots(1, 2, figsize=(5, 5))
            self.ax[0].imshow(self.hist_2d_1, cmap="hot", aspect="equal")

            self.ax[1].imshow(self.hist_2d_2, cmap="hot", aspect="equal")
            self.fig.savefig("test1.png")

            self.final_state = {
                "state": "finished",
                "name": self.n,
                "label": self.label,
                "delta_time": self.delta_time,
            }

            return self.final_state

        return {"state": "integrating"}
