# PySide2 for the UI
from multiprocessing import Event
from pty import slave_open
from PySide2.QtWidgets import QMainWindow, QApplication, QFileDialog
from PySide2.QtCore import QTimer
from PySide2.QtGui import QPalette, QColor

# matplotlib for the plots, including its Qt backend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# to generate new UI file: pyside2-uic CoincidenceExampleWindow_XXX.ui > CoincidenceExampleWindow_mx.py
# Please use the QtDesigner to edit the ui interface file
from CoincidenceExampleWindow_Ent_PLL import Ui_CoincidenceExample

from CustomPLLHistogram import CustomPLLHistogram
from snspd_measure.inst.teledyneT3PS import teledyneT3PS
import viz
import threading

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
from measurement_managment import (
    Action,
    ConcurrentAction,
    Minimize,
    SetVoltage,
    Wait,
    Integrate,
    Scan,
    StepScan,
    GraphUpdate,
    DependentAction,
)


class CoincidenceExample(QMainWindow):
    """Small example of how to create a UI for the TimeTagger with the PySide2 framework"""

    def __init__(self, tagger):
        """Constructor of the coincidence example window
        The TimeTagger object must be given as arguments to support running many windows at once."""

        # Create the UI from the designer file and connect its action buttons
        super(CoincidenceExample, self).__init__()
        self.ui = Ui_CoincidenceExample()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.load_file_params)
        self.ui.clockRefMode.clicked.connect(self.clockRefMode)
        self.ui.clearButton.clicked.connect(self.getVisibility)
        self.ui.saveButton.clicked.connect(self.saveHistData)
        # self.ui.measure_viz.clicked.connect(self.measure_viz)
        self.ui.initScan.clicked.connect(self.initVisibility)
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

        # Create the matplotlib figure with its subplots for the counter and correlation
        Colors, palette = viz.phd_style(text=-2)
        self.fig = Figure(figsize=(7, 7))

        self.clockAxis = self.fig.add_subplot(221)
        self.counterAxis = self.fig.add_subplot(222)
        self.correlationAxis = self.fig.add_subplot(223)
        self.coincAxis = self.fig.add_subplot(224)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.ui.plotLayout.addWidget(self.toolbar)
        self.ui.plotLayout.addWidget(self.canvas)

        # Create the TimeTagger measurements
        self.running = True
        self.measurements_dirty = False
        self.tagger = tagger
        self.IntType = "Rolling"
        self.last_channels = [9, -5, -14, 18]
        self.active_channels = []
        self.last_coincidenceWindow = 0
        self.updateMeasurements()
        self.divider = 5
        self.scanRunning = False
        self.multiScan = False
        self.event_loop_action = None

        # Use a timer to redraw the plots every 100ms
        self.draw()
        self.timer = QTimer()
        self.timer.timeout.connect(self.draw)
        self.timer.start(50)
        self.clock_divider = 2000  # divider 156.25MHz down to 78.125 KHz
        self.tagger.setEventDivider(18, self.clock_divider)

        self.VSource = teledyneT3PS("10.7.0.147", port=1026)
        self.VSource.set_max_voltage(5.0)
        # self.VSource = teledyneT3PS("10.7.0.147", port=1026, max_voltage=2)
        self.VSource.connect()
        V_init = self.VSource.getVoltage(2)
        print("VSource Initialized With Voltage: ", V_init)
        self.ui.intf_voltage.setProperty("value", V_init)
        self.clockRefMode()

    def reInit(self):
        # Create the TimeTagger measurements
        self.running = True
        self.measurements_dirty = False
        self.tagger = tagger
        self.IntType = "Rolling"
        self.last_channels = [9, -5, -14, 18]
        self.last_coincidenceWindow = 0
        self.updateMeasurements()
        self.inputValid = False  # used for staring visibility scan

        # Use a timer to redraw the plots every 100ms
        self.draw()
        self.timer = QTimer()
        self.timer.timeout.connect(self.draw)
        self.timer.start(10)
        self.tagger.setEventDivider(18, self.clock_divider)

    def getCouterNormalizationFactor(self):
        bin_index = self.counter.getIndex()
        # normalize 'clicks / bin' to 'kclicks / second'
        return 1e12 / bin_index[1] / 1e3

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
            self.tagger.setTestSignal(channels[0], self.ui.testsignalA.isChecked())
            self.active_channels.append(channels[0])

        if channels[1] != 0:
            self.tagger.setInputDelay(channels[1], self.ui.delayB.value())
            self.tagger.setTriggerLevel(channels[1], self.ui.triggerB.value())
            self.tagger.setDeadtime(channels[1], int(self.ui.deadTimeB.value() * 1000))
            self.tagger.setDeadtime(
                channels[1] * -1, int(self.ui.deadTimeB.value() * 1000)
            )
            self.tagger.setTestSignal(channels[1], self.ui.testsignalB.isChecked())
            self.active_channels.append(channels[1])

        if channels[2] != 0:
            self.tagger.setInputDelay(channels[2], self.ui.delayC.value())
            self.tagger.setTriggerLevel(channels[2], self.ui.triggerC.value())
            self.tagger.setDeadtime(channels[2], int(self.ui.deadTimeC.value() * 1000))
            self.tagger.setDeadtime(
                channels[2] * -1, int(self.ui.deadTimeC.value() * 1000)
            )
            self.active_channels.append(channels[2])

        if channels[3] != 0:
            self.tagger.setInputDelay(channels[3], self.ui.delayD.value())
            self.tagger.setTriggerLevel(channels[3], self.ui.triggerD.value())
            self.tagger.setDeadtime(channels[3], int(self.ui.deadTimeD.value() * 1000))
            self.tagger.setDeadtime(
                channels[3] * -1, int(self.ui.deadTimeD.value() * 1000)
            )
            self.active_channels.append(channels[3])

        if self.ui.LogScaleCheck.isChecked():
            self.correlationAxis.set_yscale("log")
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
        lines = self.plt_counter = self.counterAxis.plot(
            self.counter.getIndex() * 1e-12,
            self.counter.getData().T * self.getCouterNormalizationFactor(),
        )
        for i, line in enumerate(lines):
            line.set_color(colors[i])
        self.counterAxis.set_xlabel("time (s)")
        self.counterAxis.set_ylabel("count rate (kEvents/s)")
        self.counterAxis.set_title("Count rate")
        self.counterAxis.legend(["A", "B", "C", "D", "coincidences"])
        self.counterAxis.grid(True)

        self.correlationAxis.clear()
        self.clockAxis.clear()
        self.coincAxis.clear()

        if self.ent:
            clocks, pclocks, hist1, hist2, coinc = self.PLL.getData()

            max = numpy.max(hist1)
            print("max is: ", max)
            self.bins = numpy.arange(1, max)
            histogram1, bins = numpy.histogram(hist1, bins=self.bins)
            histogram2, bins = numpy.histogram(hist2, bins=self.bins)
            histogram_coinc, bins = numpy.histogram(coinc, bins=self.bins)

            self.histBlock_ent1 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram1))
            )
            self.histBlock_ent2 = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram2))
            )
            self.histBlock_coinc = numpy.zeros(
                (int(self.ui.IntTime.value() * 10), len(histogram_coinc))
            )

            clocks_div = clocks[:: self.divider]
            pclocks_div = pclocks[:: self.divider]
            x_clocks = numpy.linspace(0, 1, len(clocks_div))
            basis_div = numpy.linspace(pclocks[0], pclocks_div[-1], len(pclocks_div))

            self.plt_clock_dirty = self.clockAxis.plot(
                x_clocks, basis_div - clocks_div, color="k", alpha=0.2, lw=0.3
            )
            self.plt_clock_clean = self.clockAxis.plot(
                x_clocks, basis_div - pclocks_div, color="red"
            )

            self.plt_clock_corr_1 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram1, color="#6d6acc"
            )
            self.plt_clock_corr_2 = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram2, color="#cc6a6a"
            )
            self.plt_clock_corr_coinc = self.correlationAxis.plot(
                bins[:-1] * 1e-3, histogram_coinc * 10, color="k"
            )
            self.box = self.correlationAxis.axvspan(
                xmin=80 * 1e-3,
                xmax=160 * 1e-3,
                alpha=0.2,
            )
            self.coinc_x = []
            self.coinc_y = []
            self.coinc_line = self.coincAxis.plot(self.coinc_x, self.coinc_y, color="k")
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
        self.correlationAxis.grid(True)

        self.clockAxis.set_ylim(-100, 100)
        self.clockAxis.grid()
        self.clockAxis.set_title("PLL Locking Performance")

        self.coincAxis.grid(which="both")
        self.coincAxis.set_yscale("log")
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

        # boxes = self.apply_box_offset(boxes, offset)
        print(self.boxes)
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
        self.tagger.setEventDivider(18, self.clock_divider)
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
            # print(numpy.sum(self.buffer - self.buffer_old))
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

        print(self.active_channels[0])
        print(self.active_channels[1])
        print(self.active_channels[2])

        self.hist2D.startFor(int(3e12))  # 1 second

        while self.hist2D.isRunning():
            sleep(0.1)

        img = self.hist2D.getData()

        print(numpy.max(img))
        print(numpy.min(img))
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
        persistentData_coinc = numpy.sum(self.histBlock_coinc, axis=0)

        dic = {
            "channel_1": persistentData_ent1.tolist(),
            "channel_2": persistentData_ent2.tolist(),
            "coinc": persistentData_coinc.tolist(),
        }

        with open("histogram_save.json", "w") as file:
            file.write(json.dumps(dic))

    def saveEntData(self):
        pass

    def zoomInOnPeak(self):
        self.ui.delayA.setValue(-90000)
        self.ui.delayB.setValue(90000)
        self.ui.correlationBinwidth.setValue(10)
        self.ui.correlationBins.setValue(36000)  # that's 300 ns

        sleep(0.1)
        res = self.correlation.getData()
        index = self.correlation.getIndex()
        print("picoseconds of max: ", index[res.argmax()])
        time_from_zero = 180000 - index[res.argmax()]  # could be positive or negative
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

    def load_file_params(self):

        self.ent = False
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
        # self.data_channel = data_channel_1
        # self.clock_channel = clock_channel
        self.tagger.setEventDivider(self.active_channels[2], 100)

        # I should be pulling these settings from a local diccionary...
        self.PLL = CustomPLLHistogram(
            self.tagger,
            data_channel_1,
            data_channel_2,
            clock_channel,
            mult=50000,  # clock multiplier
            phase=0,
            deriv=800,
            prop=1e-13,
            n_bins=800000,
        )

    def clockRefMode(self):
        self.load_file_params()
        # self.zoomInOnPeak()

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

        # print(params["GetVisibility"]["clock_offset"])

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
        self.VSource.setVoltage(2, round(self.req_voltage, 3))

    def measure_viz(self):
        print("offset is: ", self.offset)
        print("center: ", int(self.offset + 40))

        self.final_coincidence = Coincidence(
            self.tagger,
            [
                self.gated_clock.getChannel(),
                self.snspd_2_delayed.getChannel(),
                self.snspd_1_delayed.getChannel(),
            ],
            40,
        )

        self.visibility_count_rate_1 = Countrate(
            self.tagger, [self.final_coincidence.getChannel()]
        )

        while 1:
            try:
                sleep(1)
                print("coinc final: ", self.visibility_count_rate_1.getData())
            except KeyboardInterrupt:
                break

    def handleScanInput(self):
        self.input_mode = True
        self.intTime = float(
            input("Input the approximate integration time per point: ")
        )
        self.holdTime = float(input("Input extra interferometer stabilize time: "))
        self.vStart = float(input("Start Voltage: "))
        self.vEnd = float(input("End Voltage: "))
        self.vStep = float(input("Voltage step: "))

        steps = ((self.vEnd - self.vStart) // self.vStep) + 1
        total_time = round((self.intTime + self.holdTime) * steps, 2)

        res = input(f"Scan will take {total_time} seconds. Continue? (Y/n)")
        print("res: ", res)
        if (res == "Y") or (res == ""):
            self.inputValid = True
            self.input_mode = False
            self.t_previous = time.time()
            self.voltageArray = numpy.arange(
                self.vStart, self.vEnd, self.vStep
            ).tolist()
            # print("voltage array: ", self.voltageArray)
            self.voltage_idx = 0
            self.master_counts = []
            self.master_times = []
            self.master_current = []

            self.counts_list = []
            self.times_list = []
            self.state = "waiting"  # for interferometer to settle
            setVoltage = round(self.voltageArray[self.voltage_idx], 3)
            print(f" ########### setting voltage to {setVoltage}")
            self.VSource.setVoltage(2, setVoltage)
            self.scanRunning = True
            return 0
        print("Exiting")
        self.inputValid = False
        self.input_mode = False

        return 0

    def entanglement_measurment(self):
        with open("./UI_params.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["visibility"]

        tracker = Action()
        self.event_loop_action = tracker
        """add a series of actions that will be done during the program's
        main event loop. (this is a way of avoiding a series of messy
        if statments that determine what to do at what time
        in the event loop) """
        # tracker.add_action(
        #     SetVoltage(
        #         params["int_1"]["start_voltage"],
        #         self.VSource,
        #         params["voltage_channel"],
        #     )
        # )
        # tracker.add_action(Wait(params["wait"]))
        # tracker.add_action(Scan(params["int_1"], self.VSource))
        # tracker.add_action(
        #     SetVoltage(
        #         params["int_2"]["start_voltage"],
        #         self.VSource,
        #         params["voltage_channel"],
        #     )
        # )
        # tracker.add_action(Wait(params["wait"]))

        # tracker.add_action(Scan(params["int_fast"], self.VSource))
        # tracker.add_action(Minimize(0.05, self.VSource, 0.5))

        # tracker.add_action(
        #     SetVoltage(
        #         1.66,
        #         self.VSource,
        #         params["voltage_channel"],
        #     )
        # )
        # tracker.add_action(Wait(10))
        # tracker.add_action(
        #     SetVoltage(
        #         params["min_voltage"],
        #         self.VSource,
        #         params["voltage_channel"],
        #     )
        # )
        # tracker.add_action(Wait(10))

        # +-Concurrent----------+
        # | +-Action-+ +------+ |
        # | |+------+| |      | |
        # | || Scan || |      | |
        # | ||      || |      | |
        # | |+------+| |graph | |
        # | |+------+| |      | |
        # | || Mini || |      | |
        # | ||      || |      | |
        # | |+------+| |      | |
        # | +--------+ +------+ |
        # +---------------------+

        scan_and_minimize = DependentAction()
        scan_and_minimize.add_action(Scan(params["int_fast"], self.VSource))
        scan_and_minimize.add_action(Minimize(0.005, self.VSource, 2.57))

        # how do you tell Minimize where to find the curve with the max and the min values? It doesn't exist yet...
        # if these are not finihed, I want the result to bubble up the the graph object.
        # if they are finished, I want them to export data to either the next object or the graph object.

        tracker.add_action(
            ConcurrentAction(scan_and_minimize, GraphUpdate(self.clockAxis))
        )
        tracker.enable_save(save_name=params["save_name"])

    def initVisibility(self):
        self.inputValid = False
        # I'm using a thread because I get a seg fault if I let the main
        # ui update stall for too long.
        # entanglement_measurment
        self.entanglement_measurment()
        # self.input_handler = threading.Thread(target=self.entanglement_measurment)
        # # self.input_handler = threading.Thread(target=self.handleScanInput)
        # self.input_handler.start()

    def collectCoincidences(self, count):
        ######### a way to do a coincidence measurment inside the program's main event loop.

        # if integration time exeedes limit, add and save the data, clear the buffer
        # else add to the integrator, iteration +1

        # t_previous is only changed when an integration period or a waiting period ends.
        if self.scanRunning:
            current_time = time.time()
            if self.state == "integrating":
                delta_t = current_time - self.t_previous
                if delta_t > self.intTime:
                    # finishes with this integration. Finish and move on.
                    # save the data.
                    self.master_counts.append(sum(self.counts_list))
                    self.master_times.append(delta_t)
                    self.master_current.append(self.VSource.getCurrent(2))
                    self.counts_list = []

                    if self.holdTime > 0:
                        self.state = "waiting"
                        print("state: ", self.state)
                        self.t_previous = current_time
                    else:
                        self.t_previous = current_time
                    # set the next voltage
                    self.voltage_idx += 1
                    if self.voltage_idx < len(self.voltageArray):
                        setVoltage = round(self.voltageArray[self.voltage_idx], 3)
                        print(f" ########### setting voltage to {setVoltage}")
                        self.VSource.setVoltage(2, setVoltage)
                    else:
                        # finish up the scan
                        self.scanRunning = False
                        print("master counts: ", self.master_counts)
                        print("master times: ", self.master_times)
                        dic = {
                            "master_counts": self.master_counts,
                            "master_current": self.master_current,
                            "master_times": self.master_times,
                            "voltage_array": self.voltageArray,
                        }
                        now = str(datetime.datetime.now()).replace(":", "_")
                        with open(
                            f"data_{self.vStart}_{self.vEnd}_{now}.json", "w"
                        ) as file:
                            file.write(json.dumps(dic))
                        return 0
                else:
                    # add to integration
                    # delta_t = current_time - self.t_previous
                    self.counts_list.append(count)
            if self.state == "waiting":

                if (current_time - self.t_previous) > self.holdTime:
                    self.state = "integrating"
                    print("state: ", self.state)
                    self.t_previous = current_time

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

            data = self.counter.getData() * self.getCouterNormalizationFactor()
            for data_line, plt_counter in zip(
                data, self.plt_counter
            ):  # loop though coincidences, Ch1, Ch2
                plt_counter.set_ydata(data_line)
            self.counterAxis.relim()
            self.counterAxis.autoscale_view(True, True, True)

            if self.ent:
                if self.ui.LogScaleCheck.isChecked():
                    self.correlationAxis.set_yscale("log")
                else:
                    self.correlationAxis.set_yscale("linear")
                ##############
                clocks, pclocks, hist1, hist2, coinc = self.PLL.getData()
                clocks_div = clocks[:: self.divider]
                pclocks_div = pclocks[:: self.divider]
                x_clocks = numpy.linspace(0, 1, len(clocks_div))
                basis_div = numpy.linspace(
                    pclocks_div[0], pclocks_div[-1], len(pclocks_div)
                )
                # print("Shape of coinc: ", numpy.shape(coinc))

                # self.plt_clock_dirty[0].set_xdata(x_clocks)
                self.plt_clock_dirty[0].set_data(x_clocks, basis_div - clocks_div)

                # self.plt_clock_clean[0].set_xdata(x_clocks)
                self.plt_clock_clean[0].set_data(x_clocks, basis_div - pclocks_div)
                self.clockAxis.relim()
                ##############

                histogram1, bins = numpy.histogram(hist1, bins=self.bins)
                histogram2, bins = numpy.histogram(hist2, bins=self.bins)
                histogram_coinc, bins = numpy.histogram(coinc, bins=self.bins)
                self.histBlock_ent1[self.BlockIndex] = histogram1
                self.histBlock_ent2[self.BlockIndex] = histogram2
                self.histBlock_coinc[self.BlockIndex] = histogram_coinc

                if self.event_loop_action is not None:
                    self.event_loop_action.evaluate(time.time(), len(coinc))

            else:
                index = self.correlation.getIndex()
                q = self.correlation.getData()
                self.histBlock[self.BlockIndex] = q

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

                    self.persistentData_ent1 = numpy.sum(self.histBlock_ent1, axis=0)
                    self.persistentData_ent2 = numpy.sum(self.histBlock_ent2, axis=0)
                    self.persistentData_coinc = numpy.sum(self.histBlock_coinc, axis=0)

                    currentData_ent1 = self.persistentData_ent1
                    currentData_ent2 = self.persistentData_ent2
                    currentData_coinc = self.persistentData_coinc
                    self.plt_clock_corr_1[0].set_ydata(currentData_ent1)
                    self.plt_clock_corr_2[0].set_ydata(currentData_ent2)
                    # multiplied by 10 just for better visibility in the UI
                    self.plt_clock_corr_coinc[0].set_ydata(currentData_coinc * 10)
                    if self.BlockIndex == 0:
                        # if not self.input_mode:
                        #     print(
                        #         "Coincidences: ",
                        #         numpy.sum(self.persistentData_coinc),
                        #     )
                        coincidences = numpy.sum(self.persistentData_coinc)
                        self.coinc_idx += 1
                        self.coinc_x.append(self.coinc_idx)
                        self.coinc_y.append(coincidences)
                        if len(self.coinc_x) > 50:
                            self.coinc_x.pop(0)
                            self.coinc_y.pop(0)
                        self.coinc_line[0].set_xdata(self.coinc_x)
                        self.coinc_line[0].set_ydata(self.coinc_y)

                else:
                    currentData = numpy.sum(self.histBlock, axis=0)
                    self.plt_correlation[0].set_ydata(currentData)

            self.IntType = self.ui.IntType.currentText()
            self.correlationAxis.relim()
            self.coincAxis.relim()
            self.coincAxis.autoscale_view(True, True, True)
            self.correlationAxis.autoscale_view(True, True, True)
            self.canvas.draw()
            self.correlation.clear()

            self.BlockIndex = self.BlockIndex + 1


# If this file is executed, initialize PySide2, create a TimeTagger object, and show the UI
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # used to check if JPL swabian supports high res. It does not.
    tagger = createTimeTagger(resolution=Resolution.HighResC)
    # tagger.setSoftwareClock
    # tagger = createTimeTagger()

    # If you want to include this window within a bigger UI,
    # just copy these two lines within any of your handlers.
    window = CoincidenceExample(tagger)
    window.show()

    app.exec_()

    freeTimeTagger(tagger)
