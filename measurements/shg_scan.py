from .measurement_management import *
from .user_input import UserInput, TextDialog
from PySide2.QtWidgets import QInputDialog, QAction
import threading
import yaml
from dataclasses import dataclass
import logging


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
    pass
