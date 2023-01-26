from .measurement_management import *
from PySide2.QtWidgets import QInputDialog, QAction
from PySide2.QtCore import (
    QObject,
    QThread,
    QRunnable,
    Slot,
    QThreadPool,
    Signal,
    QTimer,
)
import threading
import yaml
from dataclasses import dataclass
from .pump_power_manager import PumpPowerManager
import logging


class TextDialog(QObject):
    sig = Signal(str)

    def get_text(self, main_window, message):
        # this is called by the main_window.show_dialog() method
        main_window.user_message[0], main_window.user_message[1] = QInputDialog.getText(
            None, "User Input", message
        )
        return


class UserInput(Action):
    def __init__(
        self,
        main_window,
        input_label: str = "shg_true_power",
        request_message: str = "input data here",
    ):
        super().__init__()
        self.init = True
        self.main_window = main_window
        self.request_message = request_message
        self.input_label = input_label

    def evaluate(self, current_time, counts, **kwargs):
        if self.init:
            self.init = False
            # why singleShot: https://stackoverflow.com/questions/56524140/showing-qinputdialog-and-other-gui-objects-from-various-threads
            # why lambda function: https://stackoverflow.com/questions/7489262/singleshot-slot-with-arguments
            QTimer.singleShot(
                0, lambda: self.main_window.show_dialog(self.request_message)
            )

        if self.main_window.user_message[0] is None:
            return {"state": "waiting"}
        else:
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                self.input_label: self.main_window.user_message[0],
            }
            print("user message: ", self.main_window.user_message)
            # self.main_window.user_message is either ['number', True] or ['', False] (false when the cancel button is clicked)
            # print(self.final_state)
            self.main_window.user_message = [None, None]
            return self.final_state


class MinMaxSHG(Action):
    def __init__(
        self,
        main_window,
        start_min_voltage,
        start_max_voltage,
        req_shg_power,
        voltage_source,
    ):
        super().__init__()
        self.add_action(
            UserInput(
                main_window,
                input_label="shg_true_power",
                request_message=f"Change SHG power to {req_shg_power} and enter true power",
            )
        )
        self.add_action(SetVoltage(start_min_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(30))
        minimum = Extremum(
            "min",
            0.5,
            1,
            0.05,
            voltage_source,
            start_min_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",
        )
        minimum.add_action(ValueIntegrateExtraData(500))
        minimum.init_custom_integration()
        minimum.update_start_iteration(3)
        self.add_action(minimum)

        self.add_action(SetVoltage(start_max_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(30))
        maximum = Extremum(
            "max",
            0.25,
            4,
            0.2,
            voltage_source,
            start_max_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",  # add custom integrate action
        )
        maximum.add_action(ValueIntegrateExtraData(20000))
        maximum.init_custom_integration()
        maximum.update_start_iteration(3)
        self.add_action(maximum)
        # you should setup save_action so that the local self.environment gets saved.
        self.enable_save()


class MinMaxSHGAutoPower(Action):
    def __init__(
        self,
        main_window,
        start_min_voltage,
        start_max_voltage,
        shg_power,
        voltage_source,
    ):
        super().__init__()

        self.add_action(SetPower(shg_power, voltage_source, 1))
        self.add_action(Wait(1))
        self.add_action(SetVoltage(start_min_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(10))  # 30
        minimum = Extremum(
            "min",
            0.5,
            1,
            0.05,
            voltage_source,
            start_min_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",
        )
        minimum.add_action(ValueIntegrateExtraData(50))  # 500
        minimum.init_custom_integration()
        minimum.update_start_iteration(3)
        self.add_action(minimum)

        self.add_action(SetVoltage(start_max_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(10))  # 30
        maximum = Extremum(
            "max",
            0.25,
            4,
            0.2,
            voltage_source,
            start_max_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",  # add custom integrate action
        )
        maximum.add_action(ValueIntegrateExtraData(1000))  # 20000
        maximum.init_custom_integration()
        maximum.update_start_iteration(3)
        self.add_action(maximum)
        # you should setup save_action so that the local self.environment gets saved.
        # self.enable_save()


class SHG_Scan_Alt(Action):
    def __init__(self, main_window, voltage_source):
        super().__init__()
        with open("./measurements/shg_scan.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["shg_scan"]
        shg_powers = np.linspace(
            params["start_power"], params["end_power"], params["steps"]
        ).tolist()

        shg_powers = [round(power, 3) for power in shg_powers]

        # a store is like a mutable persistent value that can be used and updated across actions.
        start_min_voltage = Store(voltage=2.58)
        start_max_voltage = Store(voltage=1.58)
        # self.add_action(SetVoltage(start_min_voltage.get_val(), voltage_source, 2))
        # self.add_action(Wait(30))

        for shg_power in shg_powers:
            self.add_action(
                MinMaxSHG(
                    main_window,
                    start_min_voltage,
                    start_max_voltage,
                    shg_power,
                    voltage_source,
                )
            )


class SHGScanAutoPower(Action):
    def __init__(self, main_window, voltage_source):
        super().__init__()
        with open("./measurements/shg_scan.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["shg_scan"]
        shg_powers = np.linspace(
            params["start_power"], params["end_power"], params["steps"]
        ).tolist()

        shg_powers = [round(power, 3) for power in shg_powers]
        # a store is like a mutable persistent value that can be used and updated across actions.
        start_min_voltage = Store(voltage=2.58)
        start_max_voltage = Store(voltage=1.58)

        for shg_power in shg_powers:
            self.add_action(
                MinMaxSHGAutoPower(
                    main_window,
                    start_min_voltage,
                    start_max_voltage,
                    shg_power,
                    voltage_source,
                )
            )
        self.add_action(SetPower(1.0, voltage_source, 1))
        print("Finished")
        self.enable_save("shg_scan_results.json")


# if __name__ == "__main__":
