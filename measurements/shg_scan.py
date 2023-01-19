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


# self.input_handler = threading.Thread(target=self.entanglement_measurment)
# # self.input_handler = threading.Thread(target=self.handleScanInput)
# self.input_handler.start()


# message[0] = input("this is the shg power currently: ")


# class Worker(QRunnable):
#     """
#     Worker thread
#     """

#     @Slot()  # QtCore.Slot
#     def run(self):
#         """
#         Your code goes in this function
#         """
#         print("Thread start")
#         time.sleep(5)
#         print("Thread complete")


# @dataclass
# class VoltageStore:
#     def __init__(self, init_voltage):
#         self._voltage = init_voltage
#         self._voltages = []

#     # Define a "voltage" getter
#     @property
#     def voltage(self):
#         return self._voltage

#     # Define a "name" setter
#     @voltage.setter
#     def voltage(self, value):
#         self._voltage = value
#         print("voltage updated to: ", self._voltage)
#         self._voltages.append(value)

#     def export_data(self):
#         # self.voltage = self._voltage
#         # self.voltages = self._voltages
#         # del self._voltages
#         # del self._voltage
#         return self.__dict__


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


class WaitUpdateWait(Action):
    def __init__(self, main_window):
        super().__init__()
        self.add_action(Wait(1))
        self.add_action(
            UserInput(
                main_window,
                input_label="shg_true_power",
                request_message="Change SHG power to XXX and enter true power",
            )
        )
        self.add_action(Wait(1))


class InputMinimizeSHG(Action):
    def __init__(self, main_window, start_voltage, req_shg_power, voltage_source):
        super().__init__()
        self.environment = {}
        self.add_action(
            UserInput(
                main_window,
                input_label="shg_true_power",
                request_message=f"Change SHG power to {req_shg_power} and enter true power",
            )
        )
        # minimum = Extremum(
        #     "min",
        #     0.5,
        #     1,
        #     0.05,
        #     voltage_source,
        #     start_voltage,
        #     fine_grain_mode=True,
        #     low_res_steps=0,
        #     steps=5,
        # )
        # minimum.update_start_iteration(3)  # jump straight to highest res mode
        minimum = Extremum(
            "min",
            0.5,
            1,
            0.05,
            voltage_source,
            start_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",
        )
        minimum.add_action(ValueIntegrateExtraData(1000))
        minimum.init_custom_integration()
        minimum.update_start_iteration(3)
        self.add_action(minimum)
        # you should setup save_action so that the local self.environment gets saved.
        self.enable_save()


class InputMaximizeSHG(Action):
    def __init__(self, main_window, start_voltage, req_shg_power, voltage_source):
        super().__init__()
        self.environment = {}
        self.add_action(
            UserInput(
                main_window,
                input_label="shg_true_power",
                request_message=f"Change SHG power to {req_shg_power} and enter true power",
            )
        )
        # maximum = Extremum(
        #     "max",
        #     0.25,
        #     4,
        #     0.2,
        #     voltage_source,
        #     start_voltage,
        #     fine_grain_mode=True,
        #     low_res_steps=0,
        #     steps=5,
        # )
        # maximum.update_start_iteration(3)
        # self.add_action(maximum)

        maximum = Extremum(
            "max",
            0.25,
            4,
            0.2,
            voltage_source,
            start_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=5,
            int_type="custom",
        )
        maximum.add_action(ValueIntegrateExtraData(20000))
        maximum.init_custom_integration()
        maximum.update_start_iteration(3)
        self.add_action(maximum)
        # you should setup save_action so that the local self.environment gets saved.
        self.enable_save()


class SHG_Scan(Action):
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
        self.add_action(SetVoltage(start_min_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(30))
        for shg_power in shg_powers:
            self.add_action(
                InputMinimizeSHG(
                    main_window, start_min_voltage, shg_power, voltage_source
                )
            )

        # finished with scanning the mins, now wait and scan the maxes.
        self.add_action(SetVoltage(start_max_voltage.get_val(), voltage_source, 2))
        self.add_action(Wait(10))
        for shg_power in shg_powers:
            self.add_action(
                InputMaximizeSHG(
                    main_window, start_max_voltage, shg_power, voltage_source
                )
            )


if __name__ == "__main__":
    # thing = VoltageStore(3)
    # thing.voltage = 5
    # print(thing.voltage)
    # thing.voltage = 3.3
    # print(random_function(thing.voltage))
    # print(thing.export_data())

    thing = IntLike(5)
    # print(thing)
    thing = 3
    print(thing)
    thing = 2
    print(thing)
    print(type(thing))
