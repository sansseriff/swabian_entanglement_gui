# PySide2 for the UI
from multiprocessing import Event
from pty import slave_open
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QInputDialog
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPalette, QColor

# matplotlib for the plots, including its Qt backend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# to generate new UI file: pyside2-uic CoincidenceExampleWindow_XXX.ui > CoincidenceExampleWindow_mx.py
# Please use the QtDesigner to edit the ui interface file
from entanglement_control_window import EntanglementControlWindow

# from CustomPLLHistogram import CustomPLLHistogram
from CustomPLLHistogram import CustomPLLHistogram
from snspd_measure.inst.teledyneT3PS import teledyneT3PS
import viz
import threading
from numba import njit

# numpy and math for statistical analysis
import numpy
import json
import yaml
import math
import warnings

warnings.filterwarnings("ignore")

# for scope trace
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# all required TimeTagger dependencies
from TimeTagger import (
    Coincidences,
    Coincidence,
    DelayedChannel,
    GatedChannel,
    EventGenerator,
    Histogram2D,
    Counter,
    Correlation,
    createTimeTagger,
    freeTimeTagger,
    Histogram,
    Countrate,
    FileWriter,
    FileReader,
    TT_CHANNEL_FALLING_EDGES,
    Resolution,
)
from time import sleep
import time
import datetime

# import time

from SocketClient import SocketClient
from awgClient import AWGClient
from measurements.visibility_scan_minimize import VisibilityScanMinimize
from measurements.user_input import TextDialog
from measurements.shg_scan import SHGScanAutoPower, DensityMatrixSHGScan
from measurements.pump_power_manager import PumpPowerManager
from measurements.fast_minimum import FastMinimum
from measurements.measurement_management import Store
from measurement_list import MeasurementList
from measurements.channel_visibility import ChannelVisibility
from measurements.channel_visibility_dm import ChannelVisibilityDM
from measurements.voltage_current_scan import VoltageCurrentScan
from measurements.long_term_minimize import ContinuousScanMin, ConstantMin
from measurements.fringe_scan import FringeScan
from measurements.continuous_integrate import ContinuousIntegrate
from measurements.histogram_save import SaveHistogram
from measurements.time_walk_analysis import TimeWalkAnalysis, TimeWalkRunner
from measurements.time_walk_comparison import TimeWalkComparison

import logging


class CoincidenceExample(QMainWindow):
    """Small example of how to create a UI for the TimeTagger with the PySide2 framework"""

    def __init__(self, tagger):
        """Constructor of the coincidence example window
        The TimeTagger object must be given as arguments to support running many windows at once.
        """

        # Create the UI from the designer file and connect its action buttons
        super(CoincidenceExample, self).__init__()
        self.ui = EntanglementControlWindow()
        self.ui.setupUi(self)
        self.ui.loadparamsButton.clicked.connect(self.load_file_params)
        self.ui.clockrefButton.clicked.connect(self.clockRefMode)
        self.ui.clearButton.clicked.connect(self.getVisibility)
        self.ui.changePowerButton.clicked.connect(self.change_shg_power)
        self.ui.vsourceButton.clicked.connect(self.initVsource)
        self.ui.initScan.clicked.connect(self.initMeasurement)
        self.ui.set_intf_voltage.clicked.connect(self.set_intf_voltage)

        # Update the measurements whenever any input configuration changes
        self.ui.channelA.valueChanged.connect(self.updateMeasurements)
        self.ui.channelB.valueChanged.connect(self.updateMeasurements)
        self.ui.channelC.valueChanged.connect(self.updateMeasurements)
        self.ui.channelD.valueChanged.connect(self.updateMeasurements)
        self.ui.delayA.valueChanged.connect(self.updateMeasurements)
        self.ui.delayB.valueChanged.connect(self.updateMeasurements)
        self.ui.delayC.valueChanged.connect(self.updateMeasurements)
        self.ui.delayD.valueChanged.connect(self.updateMeasurements)
        self.ui.triggerA.valueChanged.connect(self.updateMeasurements)
        self.ui.triggerB.valueChanged.connect(self.updateMeasurements)
        self.ui.triggerC.valueChanged.connect(self.updateMeasurements)
        self.ui.triggerD.valueChanged.connect(self.updateMeasurements)
        self.ui.deadTimeA.valueChanged.connect(self.updateMeasurements)
        self.ui.deadTimeB.valueChanged.connect(self.updateMeasurements)
        self.ui.deadTimeC.valueChanged.connect(self.updateMeasurements)
        self.ui.deadTimeD.valueChanged.connect(self.updateMeasurements)
        self.ui.intf_voltage.valueChanged.connect(self.set_intf_voltage)

        self.ui.testsignalA.stateChanged.connect(self.updateMeasurements)
        self.ui.testsignalB.stateChanged.connect(self.updateMeasurements)
        self.ui.testsignalB.stateChanged.connect(self.updateMeasurements)
        self.ui.coincidenceWindow.valueChanged.connect(self.updateMeasurements)
        self.ui.IntType.currentTextChanged.connect(self.updateMeasurements)
        # self.ui.LogScaleCheck.stateChanged.connect(self.updateMeasurements)
        self.ui.IntTime.valueChanged.connect(self.updateMeasurements)

        self.ui.correlationBinwidth.valueChanged.connect(self.updateMeasurements)
        self.ui.correlationBins.valueChanged.connect(self.updateMeasurements)
        self.ent = False
        self.init_ent = False
        self.coinc_idx = 0
        self.input_mode = False
        self.offset_a = 0
        self.offset_b = 0
        self.p = 0
        self.vSource_initialized = False
        self.prev_time = 0

        # Create the matplotlib figure with its subplots for the counter and correlation
        Colors, palette = viz.phd_style(text=-2)
        # self.fig = Figure(figsize=(7, 7))

        # self.clockAxis = self.fig.add_subplot(221)
        # self.counterAxis = self.fig.add_subplot(222)
        # self.correlationAxis = self.fig.add_subplot(223)
        # self.coincAxis = self.fig.add_subplot(224)

        inner = [["innerA"], ["innerB"]]
        outer = [["upper left", "upper right"], ["lower left", inner]]
        gs_kw = dict(height_ratios=[1, 2])
        self.fig, axd = plt.subplot_mosaic(
            outer, gridspec_kw=gs_kw, layout="constrained"
        )
        self.clockAxis = axd["upper left"]
        self.counterAxis = axd["upper right"]
        self.correlationAxis = axd["lower left"]
        self.coincAxis = axd["innerA"]
        self.efficiencyAxis = axd["innerB"]

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.ui.plotLayout.addWidget(self.toolbar)
        self.ui.plotLayout.addWidget(self.canvas)

        # Create the TimeTagger measurements
        self.running = True
        self.measurements_dirty = False
        self.tagger = tagger
        self.IntType = "Rolling"
        self.last_channels = [-1, -5, 9, 9]
        self.active_channels = []
        self.last_coincidenceWindow = 0

        self.updateMeasurements()
        self.divider = 2
        self.scanRunning = False
        self.multiScan = False
        self.event_loop_action = None

        # I should really create this in an init_start_voltage method
        self.start_voltage_store = Store(voltage=2.58)

        self.user_message = [None, None]
        self.td = TextDialog()

        # Use a timer to redraw the plots every 100ms
        self.draw()
        self.timer = QTimer()
        self.timer.timeout.connect(self.draw)
        self.timer.start(50)
        self.clock_divider = 100  # divider 156.25MHz down to 78.125 KHz
        self.tagger.setEventDivider(9, self.clock_divider)

        self.pll_store = [None] # a silly way to make a mutable reference

        for arg in sys.argv:
            if arg == "-auto_init":
                # use this to get everything running right from the beginning.
                # do not use for debugging
                self.initVsource()
                self.load_file_params()
                self.clockRefMode()
                self.zoomInOnPeak()

    def loadMeasurements(self):
        self.measurement_list = MeasurementList(self.ui.measurement_combobox)
        self.measurement_list.add_measurement(
            VisibilityScanMinimize,
            (self.Vsource, self.clockAxis),
            "vis scan minimize",
        )
        self.measurement_list.add_measurement(
            SHGScanAutoPower, (self, self.Vsource), "shg scan"
        )

        self.measurement_list.add_measurement(
            DensityMatrixSHGScan, self.Vsource, "shg scan dm"
        )

        self.measurement_list.add_measurement(
            FastMinimum,
            (self, self.Vsource, self.start_voltage_store),
            "fast minimum",
        )
        self.measurement_list.add_measurement(
            ChannelVisibility, self.Vsource, "channel visibility"
        )
        self.measurement_list.add_measurement(
            ChannelVisibilityDM, self.Vsource, "channel visibility dm"
        )
        self.measurement_list.add_measurement(
            VoltageCurrentScan, self.Vsource, "voltage current scan"
        )
        self.measurement_list.add_measurement(
            ContinuousScanMin, self.Vsource, "continuous long min"
        )
        self.measurement_list.add_measurement(
            ConstantMin, self.Vsource, "constant long min"
        )
        self.measurement_list.add_measurement(FringeScan, self.Vsource, "fringe scan")
        self.measurement_list.add_measurement(
            ContinuousIntegrate, self, "forever integrate"
        )
        self.measurement_list.add_measurement(SaveHistogram, self, "save histogram")
        self.measurement_list.add_measurement(TimeWalkRunner, self.pll_store, "time walk analysis")
        self.measurement_list.add_measurement(TimeWalkComparison, self.Vsource, "time_walk_comparison")

    def initVsource(self):
        self.Vsource = teledyneT3PS("10.7.0.147", port=1026)
        self.Vsource.connect()
        self.Vsource.enableChannel(2)
        self.Vsource.enableChannel(1)
        self.Vsource.setCurrent(2, 0.20)
        self.Vsource.setCurrent(1, 0.02)
        V_init = self.Vsource.getVoltage(2)
        print("Vsource Initialized With Voltage: ", V_init)
        self.ui.intf_voltage.setProperty("value", V_init)
        self.vSource_initialized = True

        self.loadMeasurements()

    def reInit(self):
        # Create the TimeTagger measurements
        self.running = True
        self.measurements_dirty = False
        self.tagger = tagger
        self.IntType = "Rolling"
        self.last_channels = [-1, -5, 9, 9]
        self.last_coincidenceWindow = 0
        self.updateMeasurements()
        self.inputValid = False  # used for staring visibility scan

        # Use a timer to redraw the plots every 100ms
        self.draw()
        self.timer = QTimer()
        self.timer.timeout.connect(self.draw)
        self.timer.start(10)
        self.tagger.setEventDivider(9, self.clock_divider)

    def getCouterNormalizationFactor(self):
        bin_index = self.counter.getIndex()
        # normalize 'clicks / bin' to 'kclicks / second'
        return 1e12 / bin_index[1] / 1e3

    def show_dialog(self, message):
        self.td.get_text(self, message)

    def updateMeasurements(self):
        """Create/Update all TimeTagger measurement objects"""

        # If any configuration is changed while the measurements are stopped, recreate them on the start button
        if not self.running:
            self.measurements_dirty = True
            return

        # Set the input delay, trigger level, and test signal of both channels
        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]
        self.active_channels = []

        if channels[0] != 0:
            self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setDeadtime(
                channels[0] * -1, int(self.ui.deadTimeA.value() * 1000)
            )
            self.tagger.setInputImpedanceHigh(channels[0], False)
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())
            self.active_channels.append(channels[0])

        if channels[1] != 0:
            self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setDeadtime(
                channels[1] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.tagger.setInputImpedanceHigh(channels[1], False)
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())
            self.active_channels.append(channels[1])

        if channels[2] != 0:
            self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))
            self.tagger.setDeadtime(
                channels[2] * -1, int(self.ui.deadTimeC.value() * 1000)
            )
            self.tagger.setInputImpedanceHigh(channels[2], False)
            self.active_channels.append(channels[2])

        if channels[3] != 0:
            self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))
            self.tagger.setDeadtime(
                channels[3] * -1, int(self.ui.deadTimeD.value() * 1000)
            )
            self.tagger.setInputImpedanceHigh(channels[3], False)
            self.active_channels.append(channels[3])

        if self.ui.LogScaleCheck.isChecked():
            self.correlationAxis.set_yscale("log")
            # self.correlationAxis.set_ylim(.005,.04)
        else:
            self.correlationAxis.set_yscale("linear")

        # print(self.ui.IntType.currentText())

        self.seconds = 1
        self.histBlock = numpy.zeros(
            (int(self.ui.IntTime.value() * 10), self.ui.correlationBins.value())
        )

        self.buffer = numpy.zeros((1, self.ui.correlationBins.value()))
        self.buffer_old = numpy.zeros((1, self.ui.correlationBins.value()))

        self.BlockIndex = 0

        # Only recreate the counter if its parameter has changed,
        # else we'll clear the count trace too often
        coincidenceWindow = self.ui.coincidenceWindow.value()
        if (
            self.last_channels != self.active_channels
            or self.last_coincidenceWindow != coincidenceWindow
        ):
            self.last_channels = self.active_channels
            self.last_coincidenceWindow = coincidenceWindow

            # Create the virtual coincidence channel
            self.coincidences = Coincidences(
                self.tagger, [self.active_channels[1:]], coincidenceWindow
            )

            # Measure the count rate of both input channels and the coincidence channel
            # Use 200 * 50ms binning
            self.counter = Counter(
                self.tagger,
                self.active_channels + list(self.coincidences.getChannels()),
                binwidth=int(50e9),
                n_values=200,
            )

        # print("coincidences on ch", self.coincidences.getChannels())

        # Measure the correlation between A and B

        if self.ent:
            pass
        else:
            self.correlation = Histogram(
                self.tagger,
                # self.a_combined.getChannel(),
                # self.b_combined.getChannel(),
                self.active_channels[1],
                self.active_channels[0],
                self.ui.correlationBinwidth.value(),
                self.ui.correlationBins.value(),
            )
            self.correlation.start()

        self.tagger.sync()

        # Create the measurement plots
        self.counterAxis.clear()
        colors = [
            "#6d6acc",
            "#cc6a6a",
            "#6acc93",
            "#cc916a",
            "k",
            "#cc6a6a",
            "#6acc93",
            "#cc916a",
        ]
        data = self.counter.getData().T
        lines = self.plt_counter = self.counterAxis.plot(
            self.counter.getIndex() * 1e-12,
            data[:, :3] * self.getCouterNormalizationFactor(),
        )

        for i, line in enumerate(lines):
            line.set_color(colors[i])
        self.counterAxis.set_xlabel("time (s)")
        self.counterAxis.set_ylabel("count rate (kEvents/s)")
        self.counterAxis.set_title("Count rate")
        self.coincAxis.set_title("period coincidence rate")
        self.efficiencyAxis.set_title("coupling efficiency")
        # self.counterAxis.legend(["A", "B", "C", "D", "coincidences"])
        self.counterAxis.grid(True)

        self.correlationAxis.clear()
        self.clockAxis.clear()
        self.coincAxis.clear()
        self.efficiencyAxis.clear()

        if self.ent:
            (
                clocks,
                pclocks,
                hist1,
                hist2,
                coinc1,
                coinc2,
                full_coinc_1,
                full_coicc_2,
                coincidence,
                diff_1,
                diff_2,
                period
            ) = self.PLL.getData()

            try:
                max = numpy.max(hist1)
            except:
                max = 0
            self.bins = numpy.arange(1, max)
            histogram1, bins = numpy.histogram(hist1, bins=self.bins)
            histogram2, bins = numpy.histogram(hist2, bins=self.bins)
            histogram_coinc_1, bins = numpy.histogram(coinc1, bins=self.bins)
            histogram_coinc_2, bins = numpy.histogram(coinc2, bins=self.bins)

            self.histBlock_ent1 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram1))
            )
            self.histBlock_ent2 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram2))
            )
            self.histBlock_coinc_1 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram_coinc_1))
            )

            # this includes all three bins
            self.full_coincidence_block = numpy.zeros(int(self.ui.IntTime.value() * 10))
            self.hist_avg_rate_block = numpy.zeros(int(self.ui.IntTime.value() * 10))

            self.histBlock_coinc_2 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram_coinc_2))
            )

            clocks_div = clocks[:: self.divider]
            pclocks_div = pclocks[:: self.divider]
            x_clocks = numpy.linspace(0, 1, len(clocks_div))
            basis_div = numpy.linspace(pclocks[0], pclocks_div[-1], len(pclocks_div))

            self.plt_clock_dirty = self.clockAxis.plot(
                x_clocks, basis_div - clocks_div, color="k", alpha=0.2, lw=0.3
            )
            self.plt_clock_clean = self.clockAxis.plot(
                x_clocks, basis_div - pclocks_div, color="red", lw=0.3
            )

            self.plt_clock_corr_1 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram1, color="#6d6acc"
            )
            self.plt_clock_corr_2 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram2, color="#cc6a6a"
            )
            self.plt_clock_corr_coinc_1 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram_coinc_1 * 10, color="#232163", alpha=0.5
            )

            self.plt_clock_corr_coinc_2 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram_coinc_2 * 10, color="#591919", alpha=0.5
            )

            # self.box = self.correlationAxis.axvspan(
            #     xmin=80 * 1e-3, xmax=160 * 1e-3, alpha=0.1, color="red"
            # )
            self.box = self.correlationAxis.axvspan(
                xmin=80 * 1e-3, xmax=160 * 1e-3, alpha=0.1, color="blue"
            )
            self.coinc_x = []
            self.coinc_y = []
            self.efficiency_y = []
            self.coinc_line = self.coincAxis.plot(
                self.coinc_x, self.coinc_y, color="k", label="period coincidences"
            )
            self.coinc_eff_line = self.efficiencyAxis.plot(
                self.coinc_x, self.coinc_y, color="red", label="coupling efficiency"
            )
            # self.coincAxis.legend()
            if self.ui.LogScaleCheck.isChecked():
                self.correlationAxis.set_yscale("log")
            else:
                self.correlationAxis.set_yscale("linear")

        else:
            index = self.correlation.getIndex()
            data = self.correlation.getData()
            self.plt_correlation = self.correlationAxis.plot(index * 1e-3, data)

        self.correlationAxis.set_xlabel("time (ns)")
        self.correlationAxis.set_ylabel("Counts")
        self.correlationAxis.set_title("Clock Referenced Histograms")
        self.correlationAxis.grid(True, which="both")

        self.clockAxis.set_ylim(-100, 100)
        self.clockAxis.grid()
        self.clockAxis.set_title("PLL Locking Performance")

        self.coincAxis.grid(which="both")
        self.coincAxis.set_yscale("linear")
        self.efficiencyAxis.grid(which="both")
        self.efficiencyAxis.set_yscale("linear")
        # self.coincAxis.set_ylim(0, 600)
        # Generate nicer plots
        self.fig.tight_layout()

        self.measurements_dirty = False
        # Update the plot with real numbers
        self.draw()
        ####

    def apply_boxes(self):
        # initialize boxes
        self.offset = self.ui.offsetTime.value()
        bindwidth = self.ui.correlationBinwidth.value()
        bins = self.ui.correlationBins.value()

        width = 80  # ps
        rate = self.clock_rate.getData()[0]  # about 8 million
        period = 1e12 / (rate * 500)  # this should be in ps

        view_range = bindwidth * bins
        print("view_range: ", view_range)
        print("period: ", period)
        box_number = int(view_range // period)
        self.boxes = []
        self.spans = []
        for i in range(box_number):
            box_start = period * i
            box_end = period * i + width
            self.boxes.append([box_start, box_end])

        for box in self.boxes:
            self.spans.append(
                self.correlationAxis.axvspan(
                    xmin=(box[0] + self.offset) * 1e-3,
                    xmax=(box[1] + self.offset) * 1e-3,
                    alpha=0.2,
                )
            )
        # the boxes datastructure doesn't include any offet itself. That added when the boxes are drawn or moved

    def update_boxes(self):
        self.offset = self.ui.offsetTime.value()
        offset = self.offset
        print("offset:########### ", offset)
        for span, box in zip(self.spans, self.boxes):
            span.set_xy(self.set_span_loc(span, box, offset))

    def set_span_loc(self, span, box, offset):
        loc = span.get_xy()
        loc[0][0] = (box[0] + offset) * 1e-3
        loc[1][0] = (box[0] + offset) * 1e-3
        loc[4][0] = (box[0] + offset) * 1e-3
        loc[2][0] = (box[1] + offset) * 1e-3
        loc[3][0] = (box[1] + offset) * 1e-3
        return loc

    def startClicked(self):
        """Handler for the start action button"""
        self.running = True

        if self.measurements_dirty:
            # If any configuration is changed while the measurements are stopped,
            # recreate them on the start button
            self.updateMeasurements()
        else:
            # else manually start them
            self.counter.start()
            self.correlation.start()

    def stopClicked(self):
        """Handler for the stop action button"""
        self.running = False
        self.counter.stop()
        self.correlation.stop()

    def clearClicked(self):
        """Handler for the clear action button"""
        self.correlation.clear()

    def handle_user_input(self):
        self.user_message[0], self.user_message[1] = QInputDialog().getText(
            self, "Question", "Current SHG Power"
        )
        return self.user_message

    def saveTags(self):
        # depreciated
        self.tagger.reset()

        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]

        if channels[0] != 0:
            # self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setDeadtime(
                channels[0] * -1, int(self.ui.deadTimeA.value() * 1000)
            )
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())

        if channels[1] != 0:
            # self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setDeadtime(
                channels[1] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())

        if channels[2] != 0:
            # self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))
            self.tagger.setDeadtime(
                channels[2] * -1, int(self.ui.deadTimeC.value() * 1000)
            )

        if channels[3] != 0:
            # self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))
            self.tagger.setDeadtime(
                channels[3] * -1, int(self.ui.deadTimeD.value() * 1000)
            )
        self.tagger.setEventDivider(9, self.clock_divider)
        # self.a_combined = AverageChannel(self.tagger, -2, (-2, -3, -4))
        # self.b_combined = AverageChannel(self.tagger, -6, (-6, -7, -8))

        file = str(self.ui.saveFileName.text()) + ".ttbin"
        print("saving ", file, " in working directory")
        file_writer = FileWriter(
            self.tagger,
            file,
            [channels[0], self.a_combined.getChannel(), self.b_combined.getChannel()],
        )
        # file_writer = FileWriter(self.tagger, file, [channels[0],channels[1]])
        sleep(self.ui.saveTime.value())  # write for some time
        file_writer.stop()
        print("done!")
        self.reInit()
        self.updateMeasurements()

    def saveTagsSimple(self, nameAddition=""):
        self.tagger.reset()
        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]
        self.active_channels = []
        if channels[0] != 0:
            # self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setDeadtime(
                channels[0] * -1, int(self.ui.deadTimeA.value() * 1000)
            )
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())
            self.active_channels.append(channels[0])

        if channels[1] != 0:
            # self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setDeadtime(
                channels[1] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())
            self.active_channels.append(channels[1])

        if channels[2] != 0:
            # self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))
            self.tagger.setDeadtime(
                channels[2] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.active_channels.append(channels[2])

        if channels[3] != 0:
            # self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))
            self.tagger.setDeadtime(
                channels[3] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.active_channels.append(channels[3])

        # self.a_combined = AverageChannel(self.tagger, -3, (-3, -4))
        # self.b_combined = AverageChannel(self.tagger, -6, (-6, -7, -8))
        self.tagger.setEventDivider(18, self.clock_divider)
        file = str(self.ui.saveFileName.text()) + str(nameAddition) + ".ttbin"
        print("saving ", file, " in working directory")
        print("starting save")
        file_writer = FileWriter(self.tagger, file, self.active_channels)
        # file_writer = FileWriter(self.tagger, file, [channels[0],channels[1]])
        sleep(self.ui.saveTime.value())  # write for some time
        file_writer.stop()
        print("ending save")
        self.reInit()
        self.updateMeasurements()

    def dBScan(self):
        photonRate = SocketClient("10.7.0.101", 5050)
        startdB = float(input("Start Attenuation: "))
        stepdB = float(input("Attenuation Step Size: "))
        stepsdB = int(input("Attenuation Steps: "))

        dBlist = [startdB - stepdB * i for i in range(stepsdB)]

        for dB in dBlist:
            dBval = str(round(dB, 2))
            command = "-Q " + dBval
            # set the attenuation
            photonRate.send(command)
            sleep(1)

            self.saveTagsSimple(dBval)
            # uses the UI save time and saveName
            sleep(1)

    def triggerJitterScan(self):
        # if I want to do this with a phased locked clock, my best bet is to just save a bunch
        # of ~0.5 second files, and then do analysis on them later.

        self.tagger.reset()
        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]
        if channels[0] != 0:
            self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())

        if channels[1] != 0:
            self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())

        if channels[2] != 0:
            self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))

        if channels[3] != 0:
            self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))

        print(
            "this will save a tag file for each trigger level in a range for channel B"
        )
        start = float(input("start voltage: "))
        end = float(input("end voltage: "))
        res = int(input("input vertical resolution: "))
        save_time = float(input("save time per level: "))
        trigger_levels = [(i * (end - start) / res) + start for i in range(res)]
        trigger_levels.reverse()

        ## TODO

        for level in trigger_levels:
            self.tagger.setTriggerLevel(channels[1], level)
            print("Voltage: ", round(self.tagger.getTriggerLevel(channels[1]), 4))
            self.tagger.sync()

            file = str(self.ui.saveFileName.text()) + str(level) + "V.ttbin"
            print("saving ", file, " in working directory")
            file_writer = FileWriter(self.tagger, file, self.active_channels)
            # file_writer = FileWriter(self.tagger, file, [channels[0],channels[1]])
            sleep(save_time)  # write for some time
            file_writer.stop()
            sleep(0.5)

    def dBScanAWG(self):
        """
        this can change the attenuation, then send a command to another computer (currently my laptop) that communicates
        with the awg. This command starts a series of modulations on the awg.
        """

        choice = input(
            "this will start a series of file saves, each with a different attenuation. \n "
            "Do you also want to send a command to the awg-controlling computer for each attenuation? (y/n)"
        )

        if choice == "y":
            photonRate = SocketClient("10.7.0.101", 5050)
            awg = AWGClient()
            startdB = float(input("Start Attenuation (largest dB): "))
            stepdB = float(input("Attenuation Step Size: "))
            stepsdB = int(input("Attenuation Steps: "))

            dBlist = [startdB - stepdB * i for i in range(stepsdB)]

            for dB in dBlist:
                dBval = str(round(dB, 2))
                command = "-Q " + dBval
                # set the attenuation
                photonRate.send(command)
                sleep(0.5)
                awg.send(
                    "yes"
                )  # start the modulation. saving should start soon enough after.

                self.saveTagsSimple(dBval)
                # uses the UI save time and saveName
                sleep(60)
        else:
            photonRate = SocketClient("10.7.0.101", 5050)
            startdB = float(input("Start Attenuation (largest dB): "))
            stepdB = float(input("Attenuation Step Size: "))
            stepsdB = int(input("Attenuation Steps: "))
            dBlist = [startdB - stepdB * i for i in range(stepsdB)]
            for dB in dBlist:
                dBval = str(round(dB, 2))
                command = "-Q " + dBval
                # set the attenuation
                photonRate.send(command)
                sleep(1)
                self.saveTagsSimple(
                    dBval
                )  # this will block for some time determined by saveTags option in gui
                # uses the UI save time and saveName
                sleep(3)

    def saveTrace(self):
        self.tagger.reset()

        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]

        if channels[0] != 0:
            self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())

        if channels[1] != 0:
            self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())

        if channels[2] != 0:
            self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))

        if channels[3] != 0:
            self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))

        # self.a_combined = AverageChannel(self.tagger, -2, (-2, -3, -4, -5,-6))
        self.tagger.sync()

        start = float(input("start voltage: "))
        end = float(input("end voltage: "))
        res = int(input("input vertical resolution: "))
        ch = int(input("input channel number (A is 0, B is 1, C is 2, etc.)"))

        self.correlation = Histogram(
            self.tagger,
            self.active_channels[ch],
            # self.a_combined.getChannel(),
            self.active_channels[0],
            self.ui.correlationBinwidth.value(),
            self.ui.correlationBins.value(),
        )

        self.scopeBlock = numpy.zeros((res, self.ui.correlationBins.value()))
        trigger_levels = [
            (i * (end - start) / res) + start for i in range(len(self.scopeBlock))
        ]
        trigger_levels.reverse()

        self.correlation.stop()
        print("clear clicked in saveTrace")
        self.correlation.clear()
        sleep(1)
        for i in range(len(self.scopeBlock)):
            self.tagger.setTriggerLevel(channels[ch], trigger_levels[i])
            print("Voltage: ", round(self.tagger.getTriggerLevel(channels[ch]), 4))
            self.tagger.sync()
            sleep(0.1)
            # self.correlation.clear()
            self.correlation.start()
            sleep(0.1)
            self.correlation.stop()

            self.buffer = self.correlation.getData()
            self.scopeBlock[i] = self.buffer - self.buffer_old
            # buffer is used in next loop for subtraction
            self.buffer_old = self.buffer

        fig = plt.figure(figsize=(20, 5))
        ax = fig.add_subplot(111)
        ax.set_title("colorMap")
        plt.imshow(
            self.scopeBlock + 1,
            norm=LogNorm(),
            extent=[0, self.ui.correlationBins.value(), start, end],
        )
        # ax.set_aspect('equal')
        ax.set_aspect("auto")
        plt.show()
        sleep(0.5)  # write for some time
        print("done!")

        # self.reInit()
        self.updateMeasurements()
        R = input("Save numpy array? (y/n): ")
        if R == "y" or R == "Y":
            name = input("Input save Name: ")
            numpy.save(name, self.scopeBlock + 1)

    def Hist2D(self):
        self.tagger.reset()

        channels = [
            self.ui.channelA.value(),
            self.ui.channelB.value(),
            self.ui.channelC.value(),
            self.ui.channelD.value(),
        ]

        if channels[0] != 0:
            self.tagger.setInputDelay(channels[0], self.ui.delayA.value())
            self.tagger.setTriggerLevel(channels[0], self.ui.triggerA.value())
            self.tagger.setDeadtime(channels[0], int(self.ui.deadTimeA.value() * 1000))
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())

        if channels[1] != 0:
            self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())

        if channels[2] != 0:
            self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))

        if channels[3] != 0:
            self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))

        self.tagger.sync()

        self.hist2D = Histogram2D(
            self.tagger,
            self.active_channels[0],
            self.active_channels[1],
            self.active_channels[2],
            self.ui.correlationBinwidth.value(),
            self.ui.correlationBinwidth.value(),
            self.ui.correlationBins.value(),
            self.ui.correlationBins.value(),
        )

        self.hist2D.startFor(int(3e12))  # 1 second

        while self.hist2D.isRunning():
            sleep(0.1)

        img = self.hist2D.getData()

        fig = plt.figure(figsize=(5, 5))
        ax = fig.add_subplot(111)
        ax.set_title("2DHist")
        plt.imshow(img + 1, norm=LogNorm())
        # ax.set_aspect('equal')
        ax.set_aspect("equal")
        plt.show()

    def saveHistData(self):
        persistentData_ent1 = numpy.sum(self.histBlock_ent1, axis=0)
        persistentData_ent2 = numpy.sum(self.histBlock_ent2, axis=0)
        persistentData_coinc_1 = numpy.sum(self.histBlock_coinc_1, axis=0)
        persistentData_coinc_2 = numpy.sum(self.histBlock_coinc_2, axis=0)

        dic = {
            "channel_1": persistentData_ent1.tolist(),
            "channel_2": persistentData_ent2.tolist(),
            "coinc_1": persistentData_coinc_1.tolist(),
            "coinc_2": persistentData_coinc_2.tolist(),
        }

        with open("histogram_save.json", "w") as file:
            file.write(json.dumps(dic))

    def saveEntData(self):
        pass

    # def zoom(self, delay_1, delay_2, bind_width, iter):
    #     self.ui.delayA.setValue(delay_1)
    #     self.ui.delayB.setValue(delay_2)
    #     self.ui.delayC.setValue(0)
    #     self.ui.delayD.setValue(0)
    #     self.ui.correlationBinwidth.setValue(bind_width)
    #     self.ui.correlationBins.setValue(36000)  # that's 300 ns

    #     if iter > 1:
    #         # recursive
    #         return offset + self.zoom(
    #             smaller_delay_1, smaller_delay_2, smaller_bin_width, iter - 1
    #         )
    #     if iter == 1:
    #         return offset

    def zoomInOnPeak(self):
        # this does not seem to work at high count rate
        # or pump powers. Need to figure out why.
        self.ui.delayA.setValue(-90000)
        self.ui.delayB.setValue(90000)
        self.ui.delayC.setValue(0)
        self.ui.delayD.setValue(0)
        self.ui.correlationBinwidth.setValue(5)
        self.ui.correlationBins.setValue(36000)  # that's 300 ns
        self.correlation = Histogram(
            self.tagger,
            # self.a_combined.getChannel(),
            # self.b_combined.getChannel(),
            self.active_channels[1],
            self.active_channels[0],
            self.ui.correlationBinwidth.value(),
            self.ui.correlationBins.value(),
        )

        self.tagger.sync()

        _ = self.correlation.getData()
        sleep(0.2)
        res = self.correlation.getData()
        index = self.correlation.getIndex()

        print("picoseconds of max: ", index[res.argmax() - 2])
        time_from_zero = (
            180000 - index[res.argmax() - 2]
        )  # could be positive or negative
        hist_start_time = time_from_zero  #  + 250
        self.offset_a = -int(hist_start_time / 2)
        self.offset_b = int(hist_start_time / 2)
        self.ui.delayA.setValue(self.offset_a)
        self.ui.delayB.setValue(self.offset_b)

        # double_adjustment = int((1 / 2) * (max_ps - (1 / 2) * 200 * 1))
        # self.ui.delayA.setValue(double_adjustment)
        # self.ui.delayB.setValue(-double_adjustment)
        self.ui.correlationBins.setValue(500)
        self.ui.correlationBinwidth.setValue(1)
        time.sleep(0.02)
        self.updateMeasurements()

        persistentData_ent1 = numpy.sum(self.histBlock_ent1, axis=0)
        persistentData_ent2 = numpy.sum(self.histBlock_ent2, axis=0)

        persistentData_ent1_z = persistentData_ent1 - numpy.sum(
            persistentData_ent1
        ) / len(persistentData_ent1)
        persistentData_ent2_z = persistentData_ent2 - numpy.sum(
            persistentData_ent2
        ) / len(persistentData_ent2)

        similar = self.match_filter(persistentData_ent1_z, persistentData_ent2_z)
        # self.ui.delayC.setValue(numpy.argmax(similar))
        self.ui.delayA.setValue(self.offset_a + numpy.argmax(similar))

        guass = self.gaussian(80, 40, 15)
        extra_len = len(persistentData_ent1) - 160
        guass_ext = self.gaussian(int(extra_len), int(extra_len / 2), 15)

        # create psuedo-data that's perfectly centered
        base_array = numpy.concatenate((guass, guass * 2, guass_ext))
        base_array = numpy.roll(base_array, -20)  # fudge value
        ratio = numpy.max(persistentData_ent1) / numpy.max(base_array)
        clock_similar = self.diff_match_filter(persistentData_ent1, base_array * ratio)
        self.ui.delayC.setValue(-numpy.argmin(clock_similar))
        self.ui.delayD.setValue(-numpy.argmin(clock_similar))

    def gaussian(self, length, mu, sig):
        x = numpy.arange(length)
        return numpy.exp(-numpy.power(x - mu, 2.0) / (2 * numpy.power(sig, 2.0)))

    def match_filter(self, data1, data2):
        similarity = []
        for mult in range(len(data1)):
            similarity.append(numpy.sum(data1 * data2))
            data1 = numpy.roll(data1, 1)

        return numpy.array(similarity)

    def diff_match_filter(self, data1, data2):
        similarity = []
        for mult in range(len(data1)):
            similarity.append(numpy.sum(numpy.square(data1 - data2)))
            data1 = numpy.roll(data1, 1)

        return numpy.array(similarity)

    def change_shg_power(self):
        if not self.vSource_initialized:
            self.initVsource()
            # time.sleep(0.03)
        power_manager = PumpPowerManager(self.Vsource, 1)
        self.user_message = [None, None]
        self.show_dialog("Enter desired SHG power (Amps)")
        if self.user_message[1]:
            power = round(float(self.user_message[0]), 3)
            if power < 5.18:
                power_manager.change_pump_power(power)
            else:
                print("error power too high")

    def load_file_params(self):
        # self.ent = False
        with open("./UI_params.yaml", "r", encoding="utf8") as stream:
            try:
                ui_data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.ui.channelA.setValue(int(ui_data["Channels"]["ChA"]["channel"]))
        self.ui.triggerA.setValue(float(ui_data["Channels"]["ChA"]["trigger"]))
        self.ui.delayA.setValue(int(ui_data["Channels"]["ChA"]["delay"]))
        self.ui.deadTimeA.setValue(int(ui_data["Channels"]["ChA"]["dead_time"]))

        self.ui.channelB.setValue(int(ui_data["Channels"]["ChB"]["channel"]))
        self.ui.triggerB.setValue(float(ui_data["Channels"]["ChB"]["trigger"]))
        self.ui.delayB.setValue(int(ui_data["Channels"]["ChB"]["delay"]))
        self.ui.deadTimeB.setValue(int(ui_data["Channels"]["ChB"]["dead_time"]))

        self.ui.channelC.setValue(int(ui_data["Channels"]["ChC"]["channel"]))
        self.ui.triggerC.setValue(float(ui_data["Channels"]["ChC"]["trigger"]))
        self.ui.delayC.setValue(int(ui_data["Channels"]["ChC"]["delay"]))
        self.ui.deadTimeC.setValue(int(ui_data["Channels"]["ChC"]["dead_time"]))

        self.ui.channelD.setValue(int(ui_data["Channels"]["ChD"]["channel"]))
        self.ui.triggerD.setValue(float(ui_data["Channels"]["ChD"]["trigger"]))
        self.ui.delayD.setValue(int(ui_data["Channels"]["ChD"]["delay"]))
        self.ui.deadTimeD.setValue(int(ui_data["Channels"]["ChD"]["dead_time"]))

        self.ui.correlationBins.setValue(int(ui_data["Histogram"]["bins"]))
        self.ui.correlationBinwidth.setValue(int(ui_data["Histogram"]["bin_width"]))

        self.updateMeasurements()

    def startPLL(self, data_channel_1, data_channel_2, clock_channel):
        self.tagger.setEventDivider(self.active_channels[2], 100)

        # I should be pulling these settings from a local diccionary...
        self.PLL = CustomPLLHistogram(
            self.tagger,
            data_channel_1,
            data_channel_2,
            clock_channel,
            mult=50000,  # clock multiplier
            phase=0,
            deriv=200,
            prop=9e-13,
            n_bins=16000000,
            # ideally I would figure out how to make the program not crash when 16 million bins runs out. 
            # but that's a few seconds of integration at the highest count rates. Which hasn't been a problem. 
        )
        self.pll_store[0] = self.PLL


    def clockRefMode(self):
        # self.load_file_params()
        print("make sure correct params are loaded iwth <Load File Params>")
        print("makre sure a valid clock signal on channel ", self.active_channels[2])

        self.startPLL(
            self.active_channels[0], self.active_channels[1], self.active_channels[2]
        )

        self.ent = True
        self.init_int = True
        self.updateMeasurements()

    def getVisibility(self):
        self.zoomInOnPeak()
        with open("./UI_params.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        """
        GetVisibility:
            clock_offset: 40
            detector_one_offset: 30
            detector_two_offset: 20
            intf_min_start: 0.5
            intf_min_end: 0.6

            intf_max_start: 1.6
            intf_max_end: 1.7

            intf_steps: 10
            intf_integration: 3
        """

    def set_intf_voltage(self):
        self.req_voltage = self.ui.intf_voltage.value()
        print("requested voltage ##########: ", round(self.req_voltage, 3))
        self.Vsource.setVoltage(2, round(self.req_voltage, 3))

    def initMeasurement(self):
        cindex = self.ui.measurement_combobox.currentIndex()
        self.event_loop_action = self.measurement_list.load_measurement(cindex)

    def saveClicked(self):
        """Handler for the save action button"""

        # Ask for a filename
        filename, _ = QFileDialog().getSaveFileName(
            parent=self,
            caption="Save to File",
            directory="CoincidenceExampleData.txt",  # default name
            filter="All Files (*);;Text Files (*.txt)",
            options=QFileDialog.DontUseNativeDialog,
        )

        # And write all results to disk
        if filename:
            with open(filename, "w") as f:
                f.write("Input channel A: %d\n" % self.ui.channelA.value())
                f.write("Input channel B: %d\n" % self.ui.channelB.value())
                f.write("Input channel C: %d\n" % self.ui.channelC.value())
                f.write("Input channel D: %d\n" % self.ui.channelD.value())
                f.write("Input delay A: %d ps\n" % self.ui.delayA.value())
                f.write("Input delay B: %d ps\n" % self.ui.delayB.value())
                f.write("Input delay C: %d ps\n" % self.ui.delayC.value())
                f.write("Input delay D: %d ps\n" % self.ui.delayD.value())
                f.write("Trigger level A: %.3f V\n" % self.ui.triggerA.value())
                f.write("Trigger level B: %.3f V\n" % self.ui.triggerB.value())
                f.write("Trigger level C: %.3f V\n" % self.ui.triggerC.value())
                f.write("Trigger level D: %.3f V\n" % self.ui.triggerD.value())
                f.write("Test signal A: %d\n" % self.ui.testsignalA.isChecked())
                f.write("Test signal B: %d\n" % self.ui.testsignalB.isChecked())

                f.write(
                    "Coincidence window: %d ps\n" % self.ui.coincidenceWindow.value()
                )
                f.write(
                    "Correlation bin width: %d ps\n"
                    % self.ui.correlationBinwidth.value()
                )
                f.write("Correlation bins: %d\n\n" % self.ui.correlationBins.value())

                f.write("Counter data:\n%s\n\n" % self.counter.getData().__repr__())
                f.write(
                    "Correlation data:\n%s\n\n" % self.correlation.getData().__repr__()
                )

    def resizeEvent(self, event):
        """Handler for the resize events to update the plots"""
        self.fig.tight_layout()
        self.canvas.draw()

    def draw(self):
        """Handler for the timer event to update the plots"""
        if self.running:
            if self.BlockIndex >= int(self.ui.IntTime.value() * 10):
                self.BlockIndex = 0

            data = self.counter.getData()[:3] * self.getCouterNormalizationFactor()
            for data_line, plt_counter in zip(
                data, self.plt_counter
            ):  # loop though coincidences, Ch1, Ch2
                plt_counter.set_ydata(data_line)
            self.counterAxis.relim()
            self.counterAxis.autoscale_view(True, True, True)

            if self.ent:
                if self.ui.LogScaleCheck.isChecked():
                    self.correlationAxis.set_yscale("log")
                    # self.correlationAxis.set_ylim(.005,.04)
                else:
                    self.correlationAxis.set_yscale("linear")
                ##############
                (
                    clocks,
                    pclocks,
                    hist1,
                    hist2,
                    coinc1,
                    coinc2,
                    full_coinc_1,
                    full_coinc_2,
                    coincidence,
                    diff_1,
                    diff_2,
                    period,
                ) = self.PLL.getData()
                # print(diff_1[:7])
                # print(diff_2[:7])

                clocks_div = clocks[:: self.divider]
                pclocks_div = pclocks[:: self.divider]
                x_clocks = numpy.linspace(0, 1, len(clocks_div))
                step = int((pclocks_div[-1] - pclocks_div[0]) / (len(pclocks_div) - 1))
                basis_div = numpy.arange(
                    pclocks_div[0], pclocks_div[-1], step, dtype=numpy.int64
                )

                # do the big subtraction with int64s:
                try:
                    clock_dirty = basis_div - clocks_div
                    clock_clean = basis_div - pclocks_div
                except ValueError:
                    # sometimes the basis_div above is not big enough
                    basis_div = numpy.arange(
                        pclocks_div[0], pclocks_div[-1] + step, step, dtype=numpy.int64
                    )
                    clock_dirty = basis_div - clocks_div
                    clock_clean = basis_div - pclocks_div

                # make a array to remove that last bit of offset:
                final_offset = numpy.linspace(
                    clock_clean[0], clock_clean[-1], len(clock_clean)
                )

                # then another subtraction
                clock_dirty = clock_dirty - final_offset  # typecast to float
                clock_clean = clock_clean - final_offset  # typecast to float
                self.plt_clock_dirty[0].set_data(x_clocks, clock_dirty)
                self.plt_clock_clean[0].set_data(x_clocks, clock_clean)
                self.clockAxis.relim()

                histogram1, bins = numpy.histogram(hist1, bins=self.bins)
                histogram2, bins = numpy.histogram(hist2, bins=self.bins)
                histogram_coinc_1, bins = numpy.histogram(coinc1, bins=self.bins)
                histogram_coinc_2, bins = numpy.histogram(coinc2, bins=self.bins)
                self.histBlock_ent1[self.BlockIndex] = histogram1
                self.histBlock_ent2[self.BlockIndex] = histogram2
                self.histBlock_coinc_1[self.BlockIndex] = histogram_coinc_1
                self.histBlock_coinc_2[self.BlockIndex] = histogram_coinc_2

                current_time = time.time()


                delta_time = current_time - self.prev_time
                hist_avg_rate = (numpy.sum(histogram1) + numpy.sum(histogram2)) / 2
                self.full_coincidence_block[self.BlockIndex] = coincidence / delta_time
                self.hist_avg_rate_block[self.BlockIndex] = hist_avg_rate / delta_time
                self.prev_time = current_time

                

                if self.event_loop_action is not None:
                    self.event_loop_action.evaluate(
                        current_time,
                        len(coinc1),
                        main_window=self,
                        coincidence_array_1=coinc1.tolist(),
                        coincidence_array_2=coinc2.tolist(),
                        hist_1=histogram1,
                        hist_2=histogram2,
                        full_coinc_1=full_coinc_1.tolist(),
                        full_coinc_2=full_coinc_2.tolist(),
                        coincidences=coincidence,  # count of all period-level coincidences
                        diff_1 = diff_1,# for time walk analysis
                        diff_2 = diff_2,
                        period = period,
                        hist_tags_1 = hist1,
                        hist_tags_2 = hist2,
                    )

            else:
                index = self.correlation.getIndex()
                q = self.correlation.getData()
                self.histBlock[self.BlockIndex] = q
                self.p += 1
                self.plt_correlation[0].set_ydata(q)
                self.correlation.clear()

                # index = self.correlation.getIndex()
                # data = self.correlation.getData()
                # self.plt_correlation = self.correlationAxis.plot(index * 1e-3, data)

            if self.ui.IntType.currentText() == "Discrete":
                if self.BlockIndex == 0:
                    self.persistentData = numpy.sum(self.histBlock, axis=0)
                    if self.ent:
                        self.persistentData_ent1 = numpy.sum(
                            self.histBlock_ent1, axis=0
                        )
                else:
                    if self.IntType == "Rolling":
                        # first time changing from Rolling to Discrete
                        self.persistentData = numpy.sum(self.histBlock, axis=0)
                        # self.BlockIndex == 1
                        self.IntType = "Discrete"
                        if self.ent:
                            pass
                currentData = self.persistentData
                if self.ent:
                    currentData_ent1 = self.persistentData_ent1
            else:
                if self.ent:
                    # histogram singles
                    self.persistentData_ent1 = numpy.sum(self.histBlock_ent1, axis=0)
                    self.persistentData_ent2 = numpy.sum(self.histBlock_ent2, axis=0)

                    # histogram coinc hists
                    self.persistentData_coinc_1 = numpy.sum(
                        self.histBlock_coinc_1, axis=0
                    )
                    self.persistentData_coinc_2 = numpy.sum(
                        self.histBlock_coinc_2, axis=0
                    )

                    currentData_ent1 = self.persistentData_ent1
                    currentData_ent2 = self.persistentData_ent2
                    currentData_coinc_1 = self.persistentData_coinc_1
                    currentData_coinc_2 = self.persistentData_coinc_2
                    self.plt_clock_corr_1[0].set_ydata(currentData_ent1)
                    self.plt_clock_corr_2[0].set_ydata(currentData_ent2)
                    # multiplied by 10 just for better visibility in the UI
                    self.plt_clock_corr_coinc_1[0].set_ydata(currentData_coinc_1 * 10)
                    self.plt_clock_corr_coinc_2[0].set_ydata(currentData_coinc_2 * 10)

                    # if self.BlockIndex == 0:
                    #     coincidences = numpy.sum(self.persistentData_coinc_1)

                    self.coinc_idx += 1
                    self.coinc_x.append(self.coinc_idx)

                    self.coinc_y.append(numpy.average(self.full_coincidence_block))
                    self.efficiency_y.append(
                        numpy.average(
                            self.full_coincidence_block / self.hist_avg_rate_block
                        )
                    )
                    if len(self.coinc_x) > 50:
                        self.coinc_x.pop(0)
                        self.coinc_y.pop(0)
                        self.efficiency_y.pop(0)
                    self.coinc_line[0].set_xdata(self.coinc_x)
                    self.coinc_line[0].set_ydata(self.coinc_y)
                    self.coinc_eff_line[0].set_xdata(self.coinc_x)
                    self.coinc_eff_line[0].set_ydata(self.efficiency_y)
                    self.prev_time = current_time

                else:
                    currentData = numpy.sum(self.histBlock, axis=0)
                    self.plt_correlation[0].set_ydata(currentData)

            self.IntType = self.ui.IntType.currentText()
            self.correlationAxis.relim()
            self.coincAxis.relim()
            self.efficiencyAxis.relim()
            self.coincAxis.autoscale_view(True, True, True)
            self.efficiencyAxis.autoscale_view(True, True, True)
            self.correlationAxis.autoscale_view(True, True, True)

            self.canvas.draw()

            self.BlockIndex = self.BlockIndex + 1


# If this file is executed, initialize PySide2, create a TimeTagger object, and show the UI
if __name__ == "__main__":
    import sys

    # print(sys.argv)
    app = QApplication(sys.argv)

    logger = logging.getLogger("measure")

    # To override the default severity of logging
    logger.setLevel("INFO")

    # Use FileHandler() to log to a file
    file_handler = logging.FileHandler("measurment_managment.log")
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    # Don't forget to add the file handler
    logger.addHandler(file_handler)

    # For TimeTagger X (rack mount version) only HighResB is supported
    tagger = createTimeTagger(resolution=Resolution.HighResB)
    tagger.setLED(0x01FF0000)
    # tagger.setSoftwareClock
    # tagger = createTimeTagger()

    # If you want to include this window within a bigger UI,
    # just copy these two lines within any of your handlers.
    window = CoincidenceExample(tagger)
    window.show()

    app.exec_()

    freeTimeTagger(tagger)
