# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CoincidenceExampleWindow_4chan.ui',
# licensing of 'CoincidenceExampleWindow_4chan.ui' applies.
#
# Created: Mon Jan 25 14:08:44 2021
#      by: pyside2-uic  running on PySide2 5.9.0~a1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class EntanglementControlWindow(object):
    def setupUi(self, CoincidenceExample):
        CoincidenceExample.setObjectName("Entanglement Analyzer V3.1")
        CoincidenceExample.resize(859, 811)
        self.centralwidget = QtWidgets.QWidget(CoincidenceExample)
        self.centralwidget.setEnabled(True)
        self.centralwidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.plotLayout = QtWidgets.QVBoxLayout()
        self.plotLayout.setObjectName("plotLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label_saveName = QtWidgets.QLabel(self.centralwidget)
        self.label_saveName.setObjectName("label_saveName")
        self.gridLayout.addWidget(self.label_saveName, 9, 1, 1, 1)

        self.label_C = QtWidgets.QLabel(self.centralwidget)
        self.label_C.setObjectName("label_C")
        self.gridLayout.addWidget(self.label_C, 3, 0, 1, 1)

        self.delayB = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.delayB.sizePolicy().hasHeightForWidth())
        self.delayB.setSizePolicy(sizePolicy)
        self.delayB.setMinimum(-99999)
        self.delayB.setMaximum(99999)
        self.delayB.setObjectName("delayB")
        self.gridLayout.addWidget(self.delayB, 2, 2, 1, 1)

        self.delayA = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.delayA.sizePolicy().hasHeightForWidth())
        self.delayA.setSizePolicy(sizePolicy)
        self.delayA.setMinimum(-99999)
        self.delayA.setMaximum(99999)
        self.delayA.setObjectName("delayA")
        self.gridLayout.addWidget(self.delayA, 1, 2, 1, 1)

        self.delayC = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.delayC.sizePolicy().hasHeightForWidth())
        self.delayC.setSizePolicy(sizePolicy)
        self.delayC.setMinimum(-99999)
        self.delayC.setMaximum(99999)
        self.delayC.setObjectName("delayC")
        self.gridLayout.addWidget(self.delayC, 3, 2, 1, 1)

        self.delayD = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.delayD.sizePolicy().hasHeightForWidth())
        self.delayD.setSizePolicy(sizePolicy)
        self.delayD.setMinimum(-99999)
        self.delayD.setMaximum(99999)
        self.delayD.setObjectName("delayD")
        self.gridLayout.addWidget(self.delayD, 4, 2, 1, 1)

        self.label_inputChannel = QtWidgets.QLabel(self.centralwidget)
        self.label_inputChannel.setObjectName("label")
        self.gridLayout.addWidget(self.label_inputChannel, 0, 1, 1, 1)
        self.label_B = QtWidgets.QLabel(self.centralwidget)
        self.label_B.setObjectName("label_B")
        self.gridLayout.addWidget(self.label_B, 2, 0, 1, 1)
        self.label_14 = QtWidgets.QLabel(self.centralwidget)
        self.label_14.setText("")
        self.label_14.setObjectName("label_14")
        self.gridLayout.addWidget(self.label_14, 8, 5, 1, 1)

        self.channelB = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.channelB.sizePolicy().hasHeightForWidth())
        self.channelB.setSizePolicy(sizePolicy)
        self.channelB.setMinimum(-99)
        self.channelB.setProperty("value", -5)
        self.channelB.setObjectName("channelB")
        self.gridLayout.addWidget(self.channelB, 2, 1, 1, 1)

        self.channelA = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.channelA.sizePolicy().hasHeightForWidth())
        self.channelA.setSizePolicy(sizePolicy)
        self.channelA.setMinimum(-99)
        self.channelA.setProperty("value", -1)
        self.channelA.setObjectName("channelA")
        self.gridLayout.addWidget(self.channelA, 1, 1, 1, 1)

        self.channelC = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.channelC.sizePolicy().hasHeightForWidth())
        self.channelC.setSizePolicy(sizePolicy)
        self.channelC.setMinimum(-99)
        self.channelC.setProperty("value", 9)
        self.channelC.setObjectName("channelC")
        self.gridLayout.addWidget(self.channelC, 3, 1, 1, 1)

        self.channelD = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.channelD.sizePolicy().hasHeightForWidth())
        self.channelD.setSizePolicy(sizePolicy)
        self.channelD.setMinimum(-99)
        self.channelD.setProperty("value", 9)
        self.channelD.setObjectName("channelD")
        self.gridLayout.addWidget(self.channelD, 4, 1, 1, 1)

        self.label_A = QtWidgets.QLabel(self.centralwidget)
        self.label_A.setObjectName("label_A")
        self.gridLayout.addWidget(self.label_A, 1, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setText("")
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 8, 5, 1, 1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QtWidgets.QSpacerItem(
            0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_3.addItem(spacerItem)
        self.testsignalB = QtWidgets.QCheckBox(self.centralwidget)
        self.testsignalB.setText("")
        self.testsignalB.setObjectName("testsignalB")
        self.horizontalLayout_3.addWidget(self.testsignalB)
        spacerItem1 = QtWidgets.QSpacerItem(
            0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_3.addItem(spacerItem1)
        self.gridLayout.addLayout(self.horizontalLayout_3, 1, 5, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 2, 1, 1)
        self.triggerA = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.triggerA.setDecimals(3)
        self.triggerA.setMinimum(-2.5)
        self.triggerA.setMaximum(2.5)
        self.triggerA.setSingleStep(0.1)
        self.triggerA.setProperty("value", 0.1)
        self.triggerA.setObjectName("triggerA")
        self.gridLayout.addWidget(self.triggerA, 1, 3, 1, 1)
        self.label_13 = QtWidgets.QLabel(self.centralwidget)
        self.label_13.setObjectName("label_13")
        self.gridLayout.addWidget(self.label_13, 0, 5, 1, 1)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem2 = QtWidgets.QSpacerItem(
            0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem2)
        self.testsignalA = QtWidgets.QCheckBox(self.centralwidget)
        self.testsignalA.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.testsignalA.setAutoFillBackground(False)
        self.testsignalA.setStyleSheet("")
        self.testsignalA.setText("")
        self.testsignalA.setChecked(False)
        self.testsignalA.setAutoRepeat(False)
        self.testsignalA.setObjectName("testsignalA")
        self.horizontalLayout_4.addWidget(self.testsignalA)
        spacerItem3 = QtWidgets.QSpacerItem(
            0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem3)
        self.gridLayout.addLayout(self.horizontalLayout_4, 2, 5, 1, 1)
        self.triggerB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.triggerB.setDecimals(3)
        self.triggerB.setMinimum(-2.5)
        self.triggerB.setMaximum(2.5)
        self.triggerB.setSingleStep(0.001)
        self.triggerB.setProperty("value", -0.1)
        self.triggerB.setObjectName("triggerB")
        self.gridLayout.addWidget(self.triggerB, 2, 3, 1, 1)
        self.label_12 = QtWidgets.QLabel(self.centralwidget)
        self.label_12.setObjectName("label_12")
        self.gridLayout.addWidget(self.label_12, 0, 3, 1, 1)
        self.label_16 = QtWidgets.QLabel(self.centralwidget)
        self.label_16.setObjectName("label_16")
        self.gridLayout.addWidget(self.label_16, 8, 1, 1, 1)
        self.label_15 = QtWidgets.QLabel(self.centralwidget)
        self.label_15.setObjectName("label_15")
        self.gridLayout.addWidget(self.label_15, 0, 4, 1, 1)
        self.deadTimeB = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.deadTimeB.setDecimals(0)
        self.deadTimeB.setMaximum(1000.0)
        self.deadTimeB.setObjectName("deadTimeB")
        self.gridLayout.addWidget(self.deadTimeB, 2, 4, 1, 1)
        self.deadTimeA = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.deadTimeA.setDecimals(0)
        self.deadTimeA.setMaximum(1000.0)
        self.deadTimeA.setObjectName("deadTimeA")
        self.gridLayout.addWidget(self.deadTimeA, 1, 4, 1, 1)
        ###################
        # self.saveFileName = QtWidgets.QLineEdit(self.centralwidget)
        # self.saveFileName.setObjectName("saveFileName")
        # self.gridLayout.addWidget(self.saveFileName, 9, 2, 1, 2)

        self.measurement_combobox = QtWidgets.QComboBox()
        self.measurement_combobox.setObjectName("measurementChoice")
        self.measurement_combobox.addItems([])
        self.gridLayout.addWidget(self.measurement_combobox, 9, 2, 1, 2)

        self.intf_voltage = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.intf_voltage.setMinimum(-1000)
        self.intf_voltage.setMaximum(1000)
        self.intf_voltage.setSingleStep(0.003)
        self.intf_voltage.setDecimals(3)
        self.intf_voltage.setProperty("value", 0)
        self.intf_voltage.setObjectName("intf_voltage")
        self.gridLayout.addWidget(self.intf_voltage, 8, 2, 1, 1)
        self.set_intf_voltage = QtWidgets.QPushButton(self.centralwidget)
        self.set_intf_voltage.setObjectName("set_intf_voltage")
        self.gridLayout.addWidget(self.set_intf_voltage, 8, 3, 1, 1)
        self.initScan = QtWidgets.QPushButton(self.centralwidget)
        self.initScan.setObjectName("initScan")
        self.gridLayout.addWidget(self.initScan, 9, 4, 1, 1)
        self.label_D = QtWidgets.QLabel(self.centralwidget)
        self.label_D.setObjectName("label_D")
        self.gridLayout.addWidget(self.label_D, 4, 0, 1, 1)

        # self.channelC = QtWidgets.QDoubleSpinBox(self.centralwidget)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.channelC.sizePolicy().hasHeightForWidth())
        # self.channelC.setSizePolicy(sizePolicy)
        # self.channelC.setDecimals(0)
        # self.channelC.setMinimum(-99)
        # self.channelC.setMaximum(99)
        # self.channelC.setProperty("value", 5)
        # self.channelC.setObjectName("channelC")
        # self.gridLayout.addWidget(self.channelC, 3, 1, 1, 1)

        # self.delayC.setSizePolicy(sizePolicy)
        # self.delayC.setMinimum(-99999)
        # self.delayC.setMaximum(99999)
        # self.delayC.setObjectName("delayC")
        # self.gridLayout.addWidget(self.delayC, 3, 2, 1, 1)1

        self.triggerC = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.triggerC.setDecimals(3)
        self.triggerC.setMinimum(-2.5)
        self.triggerC.setMaximum(2.5)
        self.triggerC.setSingleStep(0.001)
        self.triggerC.setProperty("value", -0.1)
        self.triggerC.setObjectName("triggerC")
        self.gridLayout.addWidget(self.triggerC, 3, 3, 1, 1)
        self.deadTimeC = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.deadTimeC.setDecimals(0)
        self.deadTimeC.setObjectName("deadTimeC")
        self.gridLayout.addWidget(self.deadTimeC, 3, 4, 1, 1)

        # self.channelD = QtWidgets.QDoubleSpinBox(self.centralwidget)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.channelD.sizePolicy().hasHeightForWidth())
        # self.channelD.setSizePolicy(sizePolicy)
        # self.channelD.setDecimals(0)
        # self.channelD.setMinimum(-99)
        # self.channelD.setMaximum(99)
        # self.channelD.setProperty("value", 7)
        # self.channelD.setObjectName("channelD")
        # self.gridLayout.addWidget(self.channelD, 4, 1, 1, 1)

        # self.delayD.setSizePolicy(sizePolicy)
        # self.delayD.setMinimum(-99999)
        # self.delayD.setMaximum(99999)
        # self.delayD.setObjectName("delayD")
        # self.gridLayout.addWidget(self.delayD, 4, 2, 1, 1)

        self.triggerD = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.triggerD.setDecimals(3)
        self.triggerD.setMinimum(-2.5)
        self.triggerD.setMaximum(2.5)
        self.triggerD.setSingleStep(0.001)
        self.triggerD.setProperty("value", -0.1)
        self.triggerD.setObjectName("triggerD")
        self.gridLayout.addWidget(self.triggerD, 4, 3, 1, 1)
        self.deadTimeD = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.deadTimeD.setDecimals(0)
        self.deadTimeD.setObjectName("deadTimeD")
        self.gridLayout.addWidget(self.deadTimeD, 4, 4, 1, 1)
        self.horizontalLayout.addLayout(self.gridLayout)
        spacerItem4 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem4)
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.IntType = QtWidgets.QComboBox(self.centralwidget)
        self.IntType.setObjectName("IntType")
        self.IntType.addItem("")
        self.IntType.addItem("")
        self.gridLayout_3.addWidget(self.IntType, 4, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setObjectName("label_8")
        self.gridLayout_3.addWidget(self.label_8, 4, 0, 1, 1)
        self.correlationBins = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.correlationBins.sizePolicy().hasHeightForWidth()
        )
        self.correlationBins.setSizePolicy(sizePolicy)
        self.correlationBins.setMinimum(1)
        self.correlationBins.setMaximum(99999)
        self.correlationBins.setProperty("value", 1000)
        self.correlationBins.setObjectName("correlationBins")
        self.gridLayout_3.addWidget(self.correlationBins, 2, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setObjectName("label_7")
        self.gridLayout_3.addWidget(self.label_7, 2, 0, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setObjectName("label_6")
        self.gridLayout_3.addWidget(self.label_6, 1, 0, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setObjectName("label_5")
        self.gridLayout_3.addWidget(self.label_5, 0, 0, 1, 1)
        self.coincidenceWindow = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.coincidenceWindow.sizePolicy().hasHeightForWidth()
        )
        self.coincidenceWindow.setSizePolicy(sizePolicy)
        self.coincidenceWindow.setMinimum(1)
        self.coincidenceWindow.setMaximum(9999)
        self.coincidenceWindow.setProperty("value", 1000)
        self.coincidenceWindow.setObjectName("coincidenceWindow")
        self.gridLayout_3.addWidget(self.coincidenceWindow, 0, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setObjectName("label_3")
        self.gridLayout_3.addWidget(self.label_3, 3, 0, 1, 1)
        self.LogScaleCheck = QtWidgets.QCheckBox(self.centralwidget)
        self.LogScaleCheck.setObjectName("LogScaleCheck")
        self.gridLayout_3.addWidget(self.LogScaleCheck, 5, 1, 1, 1)
        self.IntTime = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.IntTime.setMinimum(0.2)
        self.IntTime.setProperty("value", 0.5)
        self.IntTime.setObjectName("IntTime")
        self.gridLayout_3.addWidget(self.IntTime, 3, 1, 1, 1)
        self.correlationBinwidth = QtWidgets.QSpinBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.correlationBinwidth.sizePolicy().hasHeightForWidth()
        )
        self.correlationBinwidth.setSizePolicy(sizePolicy)
        self.correlationBinwidth.setMinimum(1)
        self.correlationBinwidth.setMaximum(9999)
        self.correlationBinwidth.setProperty("value", 100)
        self.correlationBinwidth.setObjectName("correlationBinwidth")
        self.gridLayout_3.addWidget(self.correlationBinwidth, 1, 1, 1, 1)
        self.horizontalLayout.addLayout(self.gridLayout_3)
        self.plotLayout.addLayout(self.horizontalLayout)
        self.verticalLayout.addLayout(self.plotLayout)
        self.gridLayout_4 = QtWidgets.QGridLayout()
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.verticalLayout.addLayout(self.gridLayout_4)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.loadparamsButton = QtWidgets.QPushButton(self.centralwidget)
        self.loadparamsButton.setObjectName("loadparamsButton")
        self.horizontalLayout_2.addWidget(self.loadparamsButton)

        self.clockrefButton = QtWidgets.QPushButton(self.centralwidget)
        self.clockrefButton.setObjectName("clockrefButton")
        self.horizontalLayout_2.addWidget(self.clockrefButton)

        self.changePowerButton = QtWidgets.QPushButton(self.centralwidget)
        self.changePowerButton.setObjectName("changePowerButton")
        self.horizontalLayout_2.addWidget(self.changePowerButton)

        self.clearButton = QtWidgets.QPushButton(self.centralwidget)
        self.clearButton.setObjectName("clearButton")
        self.horizontalLayout_2.addWidget(self.clearButton)
        # self.fastMinimumButton = QtWidgets.QPushButton(self.centralwidget)
        # self.fastMinimumButton.setObjectName("fastMinimumButton")
        # self.horizontalLayout_2.addWidget(self.fastMinimumButton)

        self.vsourceButton = QtWidgets.QPushButton(self.centralwidget)
        self.vsourceButton.setObjectName("vsourceButton")
        self.horizontalLayout_2.addWidget(self.vsourceButton)

        self.verticalLayout.addLayout(self.horizontalLayout_2)
        CoincidenceExample.setCentralWidget(self.centralwidget)
        self.label_2.setBuddy(self.label_2)

        self.retranslateUi(CoincidenceExample)
        QtCore.QMetaObject.connectSlotsByName(CoincidenceExample)
        CoincidenceExample.setTabOrder(self.testsignalA, self.testsignalB)
        CoincidenceExample.setTabOrder(self.testsignalB, self.coincidenceWindow)
        CoincidenceExample.setTabOrder(self.coincidenceWindow, self.correlationBinwidth)
        CoincidenceExample.setTabOrder(self.correlationBinwidth, self.correlationBins)

    def retranslateUi(self, CoincidenceExample):
        CoincidenceExample.setWindowTitle(
            QtWidgets.QApplication.translate(
                "Entanglement Analyser V3.1", "Entanglement Analyser V3.1", None, -1
            )
        )
        self.label_saveName.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "measurment:", None, -1
            )
        )

        self.delayB.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.delayA.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.label_inputChannel.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Input channel", None, -1
            )
        )

        self.label_A.setText(
            QtWidgets.QApplication.translate("CoincidenceExample", "A:", None, -1)
        )
        self.label_B.setText(
            QtWidgets.QApplication.translate("CoincidenceExample", "B:", None, -1)
        )
        self.label_C.setText(
            QtWidgets.QApplication.translate("CoincidenceExample", "C", None, -1)
        )
        self.label_D.setText(
            QtWidgets.QApplication.translate("CoincidenceExample", "D", None, -1)
        )

        self.label_2.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Input delay", None, -1
            )
        )
        self.triggerA.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " V", None, -1)
        )
        self.label_13.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Test signal", None, -1
            )
        )
        self.triggerB.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " V", None, -1)
        )
        self.label_12.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Trigger level", None, -1
            )
        )
        self.label_16.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "intf_voltage:", None, -1
            )
        )
        self.label_15.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Dead Time", None, -1
            )
        )
        self.deadTimeB.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ns", None, -1)
        )
        self.deadTimeA.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ns", None, -1)
        )
        self.intf_voltage.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " V", None, -1)
        )
        self.set_intf_voltage.setText(
            QtWidgets.QApplication.translate("CoincidenceExample", "Set", None, -1)
        )
        self.initScan.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "init measurement", None, -1
            )
        )

        self.delayC.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.triggerC.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " V", None, -1)
        )
        self.deadTimeC.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ns", None, -1)
        )
        self.delayD.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.triggerD.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " V", None, -1)
        )
        self.deadTimeD.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ns", None, -1)
        )
        self.IntType.setItemText(
            0,
            QtWidgets.QApplication.translate("CoincidenceExample", "Rolling", None, -1),
        )
        self.IntType.setItemText(
            1,
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Discrete", None, -1
            ),
        )
        self.label_8.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Integration Type", None, -1
            )
        )
        self.label_7.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Histogram bins", None, -1
            )
        )
        self.label_6.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Histogram bin width", None, -1
            )
        )
        self.label_5.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Coincidence window", None, -1
            )
        )
        self.coincidenceWindow.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.label_3.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Integration Time", None, -1
            )
        )
        self.LogScaleCheck.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Log Scale", None, -1
            )
        )
        self.correlationBinwidth.setSuffix(
            QtWidgets.QApplication.translate("CoincidenceExample", " ps", None, -1)
        )
        self.loadparamsButton.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Load File Params", None, -1
            )
        )

        self.changePowerButton.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Change Pump Power", None, -1
            )
        )

        self.clockrefButton.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Clock Referenced Mode", None, -1
            )
        )
        self.clearButton.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Zoom In To Peak", None, -1
            )
        )
        # self.fastMinimumButton.setText(
        #     QtWidgets.QApplication.translate(
        #         "CoincidenceExample", "Fast Minimum", None, -1
        #     )
        # )

        self.vsourceButton.setText(
            QtWidgets.QApplication.translate(
                "CoincidenceExample", "Init Vsource", None, -1
            )
        )
