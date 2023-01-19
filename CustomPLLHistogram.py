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
        self.cycle = 0

        self.clock_idx = 0
        self.hist_1_idx = 0
        self.hist_2_idx = 0
        self.coinc_1_idx = 0
        self.coinc_2_idx = 0

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
                coinc_1 = self.coinc_1[: self.coinc_1_idx].copy()
                coinc_2 = self.coinc_2[: self.coinc_2_idx].copy()
                self.old_clock_start = self.clock_data[0]

                # expiremental ####
                self.clock_idx = 0
                self.hist_1_idx = 0
                self.hist_2_idx = 0
                self.coinc_1_idx = 0
                self.coinc_2_idx = 0
                ###################
                self._unlock()
                return clocks, pclocks, hist_1_tags, hist_2_tags, coinc_1, coinc_2
            else:
                print("nope")
            self._unlock()

    def clear_impl(self):
        # The lock is already acquired within the backend.
        self.last_start_timestamp = 0
        self.clock_data = np.zeros((self.max_bins,), dtype=np.int64)
        self.lclock_data = np.zeros((self.max_bins,), dtype=np.int64)
        self.lclock_data_dec = np.zeros(
            (self.max_bins,), dtype=np.float64
        )  # decimal component of clock0
        self.hist_1_tags_data = np.zeros((self.max_bins,), dtype=np.float64)
        self.coinc_1 = np.zeros((self.max_bins,), dtype=np.float64)
        self.coinc_2 = np.zeros((self.max_bins,), dtype=np.float64)
        self.hist_2_tags_data = np.zeros((self.max_bins,), dtype=np.float64)

    def on_start(self):
        # The lock is already acquired within the backend.
        pass

    def on_stop(self):
        # The lock is already acquired within the backend.
        pass

    # I should support the measurment of the unfiltered clock with respect to the phase locked clock.

    @staticmethod
    @numba.jit(nopython=True, nogil=True, cache=True)
    def fast_process(
        tags,
        clock_data,
        lclock_data,
        lclock_data_dec,
        hist_1_tags_data,
        hist_2_tags_data,
        coinc_1,
        coinc_2,
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
        coinc_1_idx,
        coinc_2_idx,
        q,
        cycle,
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
        ch1_siv_start = 90  # - 20  # blue
        ch1_siv_end = 158  # + 20  # blue

        ch2_siv_start = 80  # - 20  # red
        ch2_siv_end = 148  # + 20  # red
        buffer_tag_raw = 0
        buffer_tag_hist = 0
        buffer_cycle = 0
        freq = 1 / period
        # test_factor = 1000000000000000000
        test_factor = 0

        this = np.ones(5) * 4.9345
        if init:
            print(
                "Init PLL with clock channel ",
                clock_channel,
                " , data1 channel: ",
                data_channel_1,
                " , and data2 channel ",
                data_channel_2,
            )
            clock_idx = 0
            clock_portion = np.zeros(1000, dtype=np.uint64)

            for clock_idx, tag in enumerate(tags[:1000]):
                if tag["channel"] == clock_channel:
                    clock_portion[clock_idx] = tag["time"] + test_factor
                    clock_idx += 1

            # Initial Estimates
            clock_portion = clock_portion[clock_portion > 0]  # cut off extra zeros
            period = (clock_portion[-1] - clock_portion[0]) / (len(clock_portion) - 1)
            freq = 1 / period
            init = 0
            clock0 = -1
            clock0_dec = -0.1
            print("[READY] Finished FastProcess Initialization")
            clock_idx = 0
            hist_1_idx = 0
            hist_2_idx = 0
            coinc_1_idx = 0
            coinc_2_idx = 0

        for i, tag in enumerate(tags):
            q = q + 1
            # if i == 32:
            #     print("period: ", period)
            if tag["channel"] == clock_channel:
                current_clock = tag["time"] + test_factor
                clock_data[clock_idx] = current_clock
                if clock0 == -1:
                    # clock0 = current_clock - period
                    clock0 = np.int64(current_clock - period)
                    clock0_dec = 0.0

                # arg_int = np.int64(current_clock - clock0) #should both be int64s
                arg_int = current_clock - clock0  # both int64
                arg = arg_int - clock0_dec
                arg = (arg - period) * 2 * math.pi  # now its a float
                arg = arg / period
                phi0 = math.sin(arg)
                filterr = phi0 + (phi0 - phi_old) * deriv
                freq = freq - filterr * prop

                # this will handle missed clocks
                cycles = round((current_clock - clock0) / period)
                cycle += cycles
                period = 1 / freq
                adj = cycles * period
                adj_int = np.int64(adj)
                adj_dec = adj - adj_int

                clock0 = clock0 + adj_int
                clock0_dec = clock0_dec + adj_dec
                if clock0_dec >= 1:
                    int_add = np.int64(clock0_dec)
                    clock0 = clock0 + int_add
                    clock0_dec = clock0_dec - int_add

                # clock0 = clock0 + adj

                lclock_data[clock_idx] = clock0
                lclock_data_dec[clock_idx] = clock0_dec
                phi_old = phi0
                clock_idx = clock_idx + 1

            if (tag["channel"] == data_channel_1) or (tag["channel"] == data_channel_2):
                if clock0 != -1:
                    hist_tag = ((tag["time"] + test_factor) - clock0) - clock0_dec
                    # hist_tag = (tag["time"]+test_factor) - current_clock # no PLL
                    sub_period = period / mult
                    minor_cycles = (hist_tag + phase) // sub_period
                    minor_cycle = cycle * mult + minor_cycles
                    # minor_cycle is the number or 'index' of this experiment period
                    hist_tag = hist_tag - (sub_period * minor_cycles)

                    if tag["channel"] == data_channel_1:
                        hist_1_tags_data[hist_1_idx] = hist_tag
                        hist_1_idx += 1

                        if (hist_tag > ch1_siv_start) and (hist_tag < ch1_siv_end):
                            # this cuts the blue
                            if minor_cycle == buffer_cycle:
                                # if the counts are from the same period
                                # valid coincidence. add to coinc array
                                # pass
                                coinc_1[coinc_1_idx] = hist_tag
                                coinc_2[coinc_2_idx] = buffer_tag_hist
                                # maybe I need a way of ensuring that the buffer tag is from the other channel?
                                # I'd prefer to do things in this order:
                                # 1. Are they in the same period?
                                # 2. Are they in the same bin?
                                # I remember I wanted to assign each tag a cycle number

                                # (buffer_tag_hist + hist_tag) / 2

                                buffer_tag_hist = -200
                                buffer_tag_raw = 0
                                coinc_1_idx += 1
                                coinc_2_idx += 1
                            else:
                                # no match, overwrite buffer with current tag
                                buffer_tag_hist = hist_tag
                                buffer_tag_raw = tag["time"] + test_factor
                                buffer_cycle = minor_cycle

                    if tag["channel"] == data_channel_2:
                        hist_2_tags_data[hist_2_idx] = hist_tag
                        hist_2_idx += 1

                        if (hist_tag > ch2_siv_start) and (hist_tag < ch2_siv_end):
                            # this cuts the red. Red is the 2nd member of the coincidence
                            # if abs(tag["time"] + test_factor - buffer_tag_raw) <= 240:
                            if minor_cycle == buffer_cycle:
                                # if the counts are from the same period
                                coinc_2[coinc_1_idx] = hist_tag
                                coinc_1[coinc_2_idx] = buffer_tag_hist

                                buffer_tag_hist = -200
                                buffer_tag_raw = 0
                                coinc_1_idx += 1
                                coinc_2_idx += 1
                            else:
                                # no match, overwrite buffer with current tag
                                buffer_tag_hist = hist_tag
                                buffer_tag_raw = tag["time"] + test_factor
                                buffer_cycle = minor_cycle

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
            coinc_1_idx,
            coinc_2_idx,
            error,
            q,
            cycle,
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
            self.coinc_1_idx,
            self.coinc_2_idx,
            self.error,
            self.i,
            self.cycle,
        ) = CustomPLLHistogram.fast_process(
            incoming_tags,
            self.clock_data,
            self.lclock_data,
            self.lclock_data_dec,
            self.hist_1_tags_data,
            self.hist_2_tags_data,
            self.coinc_1,
            self.coinc_2,
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
            self.coinc_1_idx,
            self.coinc_2_idx,
            self.i,
            self.cycle,
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
