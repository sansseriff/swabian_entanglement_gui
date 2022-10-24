import TimeTagger
import numpy as np
import numba
import math
from time import sleep


"""
Modified from the example code provided by swabian to generate histgrams from a phased locked clock.
Andrew Mueller February 2022

"""


class CustomPLLHistogram(TimeTagger.CustomMeasurement):
    """
    Example for a single start - multiple stop measurement.
        The class shows how to access the raw time-tag stream.
    """

    def __init__(
        self,
        tagger,
        data_channel_1,
        data_channel_2,
        clock_channel,
        mult=1,
        phase=0,
        deriv=0.01,
        prop=2e-9,
        n_bins=20000000,
    ):
        TimeTagger.CustomMeasurement.__init__(self, tagger)
        self.data_channel_1 = data_channel_1
        self.data_channel_2 = data_channel_2
        self.clock_channel = clock_channel
        self.mult = mult
        self.phase = phase
        self.deriv = deriv
        self.prop = prop
        self.clock0 = 0
        self.period = 1  # 12227788.110837
        self.phi_old = 0
        self.init = 1
        self.max_bins = n_bins

        self.clock_idx = 0
        self.hist_1_idx = 0
        self.hist_2_idx = 0
        self.coinc_idx = 0

        self.error = 0
        self.old_clock_start = 0
        self.old_clock = 0
        self.i = 0
        self.register_channel(channel=data_channel_1)
        self.register_channel(channel=data_channel_2)
        self.register_channel(channel=clock_channel)
        self.clear_impl()

        # At the end of a CustomMeasurement construction,
        # we must indicate that we have finished.
        self.finalize_init()

    def __del__(self):
        # The measurement must be stopped before deconstruction to avoid
        # concurrent process() calls.
        self.stop()

    def getData(self):
        # Acquire a lock this instance to guarantee that process() is not running in parallel
        # This ensures to return a consistent data.

        clocks = np.zeros(50)
        pclocks = np.zeros(50)
        hist_1_tags = np.zeros(50)
        hist_2_tags = np.zeros(50)  # why do I make these?
        while 1:
            self._lock()
            if self.clock_idx == 0:
                self._unlock()
                continue
            if (self.old_clock_start != self.clock_data[0]) | (
                self.old_clock_start == 0
            ):
                clocks = self.clock_data[: self.clock_idx].copy()
                pclocks = self.lclock_data[: self.clock_idx].copy()
                hist_1_tags = self.hist_1_tags_data[: self.hist_1_idx].copy()
                hist_2_tags = self.hist_2_tags_data[: self.hist_2_idx].copy()
                coinc = self.coinc[: self.coinc_idx].copy()
                self.old_clock_start = self.clock_data[0]

                # expiremental ####
                self.clock_idx = 0
                self.hist_1_idx = 0
                self.hist_2_idx = 0
                self.coinc_idx = 0
                ###################
                self._unlock()
                return clocks, pclocks, hist_1_tags, hist_2_tags, coinc
            else:
                print("nope")
            self._unlock()

    def clear_impl(self):
        # The lock is already acquired within the backend.
        self.last_start_timestamp = 0
        self.clock_data = np.zeros((self.max_bins,), dtype=np.float64)
        self.lclock_data = np.zeros((self.max_bins,), dtype=np.float64)
        self.hist_1_tags_data = np.zeros((self.max_bins,), dtype=np.float64)
        self.coinc = np.zeros((self.max_bins,), dtype=np.float64)
        self.hist_2_tags_data = np.zeros((self.max_bins,), dtype=np.float64)

    def on_start(self):
        # The lock is already acquired within the backend.
        pass

    def on_stop(self):
        # The lock is already acquired within the backend.
        pass

    # I should support the measurment of the unfiltered clock with respect to the phase locked clock.

    @staticmethod
    @numba.jit(nopython=True, nogil=True)
    def fast_process(
        tags,
        clock_data,
        lclock_data,
        hist_1_tags_data,
        hist_2_tags_data,
        coinc,
        data_channel_1,
        data_channel_2,
        clock_channel,
        init,
        clock0,
        period,
        phi_old,
        deriv,
        prop,
        phase,
        mult,
        clock_idx,
        hist_1_idx,
        hist_2_idx,
        coinc_idx,
        q,
    ):

        """
        A precompiled version of the histogram algorithm for better performance
        nopython=True: Only a subset of the python syntax is supported.
                       Avoid everything but primitives and numpy arrays.
                       All slow operation will yield an exception
        nogil=True:    This method will release the global interpreter lock. So
                       this method can run in parallel with other python code
        """
        error = 0
        test = 0
        siv_start = 80
        siv_end = 160
        buffer_tag_raw = 0
        buffer_tag_hist = 0
        freq = 1 / period
        zero_cycles = 0
        if init:
            print("type: ", tags.dtype)
            # print("extra info: ", tags[0].shape)
            clock_idx = 0
            clock_portion = np.zeros(1000, dtype=np.uint64)

            for clock_idx, tag in enumerate(tags[:1000]):
                if tag["channel"] == clock_channel:
                    clock_portion[clock_idx] = tag["time"]
                    clock_idx += 1

            # Initial Estimates
            clock_portion = clock_portion[clock_portion > 0]  # cut off extra zeros
            period = (clock_portion[-1] - clock_portion[0]) / (len(clock_portion) - 1)
            freq = 1 / period
            init = 0
            clock0 = -1
            print("[READY] Finished FastProcess Initialization")
            clock_idx = 0
            hist_1_idx = 0
            hist_2_idx = 0
            coinc_idx = 0
            arg1 = 0

        for i, tag in enumerate(tags):
            q = q + 1
            if tag["channel"] == clock_channel:
                current_clock = tag["time"]
                clock_data[clock_idx] = current_clock
                if clock0 == -1:
                    clock0 = current_clock - period
                arg1 = ((current_clock - (clock0 + period))* 2 * math.pi)
                clock0_int = math.floor(clock0)
                clock0_dec = clock0 - clock0_int

                period_int = math.floor(period)
                period_dec = period - period_int


                new_c_dec = clock0_dec + period_dec
                new_c_int = clock0_int + period_int
                arg1 = current_clock - new_c_int
                arg1 = (arg1 - new_c_dec) * 2 * math.pi
                arg2 = arg1 / period
                phi0 = math.sin(arg2)
                filterr = phi0 + (phi0 - phi_old) * deriv
                freq = freq - filterr * prop

                # this will handle missed clocks
                cycles = round((current_clock - clock0) / period)
                period = 1 / freq
                # if i == 32:
                #     print(phi_old)

                # if i == 56:
                #     print("###################")
                #     print("RANDOM")
                #     print("current and previous: ", current_clock - (clock0 + period))


                # if abs(phi0) <= 1e-9:
                #     zero_cycles += 1
                #     print("###################")
                #     print("phi0: ", phi0)
                #     print("phi_old: ", phi_old)
                #     print("arg1: ", arg1)
                #     print("arg2: ", arg2)
                #     print("current clock: ", current_clock)
                #     print("clock0: ", clock0)
                #     print("period: ", period)
                #     print("current and previous: ", current_clock - (clock0 + period))
                #     print("period: ", period)


                    # print("filterr: ", filterr)
                    # print("cycles: ", cycles)
                #     # print("period times frequency: ", period * freq)
                #     # print("#### phi0: ", phi0)
                #     # print("######## deriv: ", deriv)
                #     # print("######## prop: ", prop)
                #     # print("hist tags 1 data: ", hist_1_tags_data[0])
                #     # print("clock0: ", clock0)
                #     # print("q: ", q)
                # print(test)
                # if phi_old == 0.0:
                #     test = test + 1
                if cycles != 1:
                    test = test + 1
                # if i == 32:
                #     print(test)
                clock0 = clock0 + cycles * period  # add one (or more) periods
                lclock_data[clock_idx] = clock0
                phi_old = phi0
                clock_idx = clock_idx + 1

            if (tag["channel"] == data_channel_1) or (tag["channel"] == data_channel_2):
                if clock0 != -1:
                    hist_tag = tag["time"] - clock0
                    sub_period = period / mult
                    minor_cycles = (hist_tag + phase) // sub_period
                    hist_tag = hist_tag - (sub_period * minor_cycles)

                    if tag["channel"] == data_channel_1:
                        hist_1_tags_data[hist_1_idx] = hist_tag
                        hist_1_idx += 1

                        if (hist_tag > siv_start) and (hist_tag < siv_end):
                            # clock valid. Check the buffer
                            if abs(tag["time"] - buffer_tag_raw) <= 80:
                                # valid coincidence. add to coinc array
                                coinc[coinc_idx] = (buffer_tag_hist + hist_tag) / 2
                                buffer_tag_hist = -200
                                buffer_tag_raw = 0
                                coinc_idx += 1
                            else:
                                # no match, overwrite buffer with current tag
                                buffer_tag_hist = hist_tag
                                buffer_tag_raw = tag["time"]

                    if tag["channel"] == data_channel_2:
                        hist_2_tags_data[hist_2_idx] = hist_tag
                        hist_2_idx += 1

                        if (hist_tag > siv_start) and (hist_tag < siv_end):
                            # clock valid. Check the buffer
                            if abs(tag["time"] - buffer_tag_raw) <= 80:
                                # valid coincidence. add to coinc array
                                coinc[coinc_idx] = (buffer_tag_hist + hist_tag) / 2
                                buffer_tag_hist = -200
                                buffer_tag_raw = 0
                                coinc_idx += 1
                            else:
                                # no match, overwrite buffer with current tag
                                buffer_tag_hist = hist_tag
                                buffer_tag_raw = tag["time"]

                    # if its in the correct time window, save it in buffer.
                    # every time something gets added to the buffer you either
                    # 1. check what's in the buffer if it matches the raw time add to coinc array, set buffer to zero
                    # 2. check what's in the buffer if no match discard buffer and replace

                else:
                    continue

        # print("zero cycles: ", zero_cycles)
        return (
            clock0,
            period,
            phi_old,
            init,
            clock_idx,
            hist_1_idx,
            hist_2_idx,
            coinc_idx,
            error,
            q,
        )

    def process(self, incoming_tags, begin_time, end_time):
        """
        Main processing method for the incoming raw time-tags.

        The lock is already acquired within the backend.
        self.data is provided as reference, so it must not be accessed
        anywhere else without locking the mutex.

        Parameters
        ----------
        incoming_tags
            The incoming raw time tag stream provided as a read-only reference.
            The storage will be deallocated after this call, so you must not store a reference to
            this object. Make a copy instead.
            Please note that the time tag stream of all channels is passed to the process method,
            not only the onces from register_channel(...).
        begin_time
            Begin timestamp of the of the current data block.
        end_time
            End timestamp of the of the current data block.
        """
        # maybe the jit function could change the memory location of that returned ints? So you need to pass them?
        # but numpy arrays are just pointers, and the class already has those. No need to pass them back.
        (
            self.clock0,
            self.period,
            self.phi_old,
            self.init,
            self.clock_idx,
            self.hist_1_idx,
            self.hist_2_idx,
            self.coinc_idx,
            self.error,
            self.i,
        ) = CustomPLLHistogram.fast_process(
            incoming_tags,
            self.clock_data,
            self.lclock_data,
            self.hist_1_tags_data,
            self.hist_2_tags_data,
            self.coinc,
            self.data_channel_1,
            self.data_channel_2,
            self.clock_channel,
            self.init,
            self.clock0,
            self.period,
            self.phi_old,
            self.deriv,
            self.prop,
            self.phase,
            self.mult,
            # expiremental
            self.clock_idx,
            self.hist_1_idx,
            self.hist_2_idx,
            self.coinc_idx,
            self.i,
        )


# Channel definitions
CHAN_START = 1
CHAN_STOP = 2

if __name__ == "__main__":

    print(
        """Custom Measurement example

Implementation of a custom single start, multiple stop measurement, histogramming
the time differences of the two input channels.

The custom implementation will be comparted to a the build-in Histogram class,
which is a multiple start, multiple stop measurement. But for the
selected time span of the histogram, multiple start does not make a difference.
"""
    )
    # fig, ax = plt.subplots()

    tagger = TimeTagger.createTimeTagger()
    data_channel = -5
    clock_channel = 9
    tagger.setEventDivider(9, 100)
    tagger.setTriggerLevel(-5, -0.014)
    tagger.setTriggerLevel(9, 0.05)
    PLL = CustomPLLHistogram(
        tagger,
        data_channel,
        clock_channel,
        10,
        phase=0,
        deriv=0.001,
        prop=2e-10,
        n_bins=800000,
    )
    # for i in range(40000):
    #     sleep(.05)
    #     clocks, pclocks, hist = PLL.getData()
    #     # print("1: ", clks1[:10])
    #     # print("HIST: ", hist[:20])
    #     print("length of clocks: ", len(clocks))
    #     diff = clocks - pclocks
    #     print("difference: ", diff[:10])
    for i in range(40000):
        sleep(0.05)
        clocks, pclocks, hist_1, hist_2 = PLL.getData()

    clocks, pclocks, hist1, hist_2 = PLL.getData()

    basis = np.linspace(clocks[0], clocks[-1], len(clocks))
