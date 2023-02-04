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
from .user_input import UserInput


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
        minimum.add_action(ValueIntegrateExtraData(500, minimum_evaluations=100))
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
        maximum.add_action(ValueIntegrateExtraData(20000, minimum_evaluations=100))
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
        params,
    ):
        super().__init__()

        self.add_action(SetPower(shg_power, voltage_source, 1))
        self.add_action(Wait(1))
        self.add_action(SetVoltage(start_min_voltage, voltage_source, 2))
        print(f"Wait time: {params['wait_time']}")
        self.add_action(Wait(params["wait_time"]))  # 30
        minimum = Extremum(
            "min",
            0.5,
            1,
            0.05,
            voltage_source,
            start_min_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=params["integration_steps"],
            int_type="custom",
        )
        minimum.add_action(
            ValueIntegrateExtraData(
                params["minimum_counts"],
                minimum_evaluations=params["minimum_integrate_evaluations"],
            )
        )  # 500
        print(f"Minimum counts: {params['minimum_counts']}")
        minimum.init_custom_integration()
        minimum.update_start_iteration(3)
        self.add_action(minimum)

        self.add_action(SetVoltage(start_max_voltage, voltage_source, 2))
        self.add_action(Wait(params["wait_time"]))  # 30
        maximum = Extremum(
            "max",
            0.25,
            4,
            0.2,
            voltage_source,
            start_max_voltage,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=params["integration_steps"],
            int_type="custom",  # add custom integrate action
        )
        maximum.add_action(
            ValueIntegrateExtraData(
                params["maximum_counts"],
                minimum_evaluations=params["minimum_integrate_evaluations"],
            )
        )  # 20000
        print(f"Maximum counts: {params['maximum_counts']}")
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
        # a store is a mutable persistent value that can be used and updated across actions.
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
                    params,
                )
            )
        self.add_action(SetPower(1.0, voltage_source, 1))
        self.enable_save(params["output_file_name"])


# if __name__ == "__main__":
