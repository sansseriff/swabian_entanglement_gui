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

from .channel_visibility_dm import DerivedVoltages


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


class ScanStep(Action):
    def __init__(
        self,
        voltage_source,
        power,
        params_extreme,
        voltage_store,
        extremum_mode=True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.add_action(SetPower(power, voltage_source, 1))
        self.add_action(Wait(30))
        self.add_action(
            make_integration(
                voltage_source, params_extreme, voltage_store, extremum_mode
            )
        )


class PowerRamp(Action):
    def __init__(
        self,
        voltage_source,
        powers,
        params_extreme,
        voltage_store,
        extremum_mode=True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        for power in powers:
            self.add_action(
                ScanStep(
                    voltage_source, power, params_extreme, voltage_store, extremum_mode
                )
            )


class DensityMatrixSHGScan(Action):
    def __init__(self, voltage_source, **kwargs):
        super().__init__(**kwargs)

        with open("./measurements/shg_scan_dm.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["channel_visibility"]

        powers = [
            round(item, 3)
            for item in np.arange(
                params["low_power"], params["high_power"], params["power_step"]
            ).tolist()
        ]

        min_voltage_1 = Store(voltage=params["minimum_voltage_1"])
        min_voltage_2 = Store(voltage=params["minimum_voltage_2"])
        max_voltage = Store(voltage=params["maximum_voltage"])
        derived_max = Store(voltage=0)  # to be updated later
        derived_90 = Store(voltage=0)

        ########### STEP 1
        # at a medium power, scan the phase of the interferometer to find the minimum
        # with high accuracy.
        ###########
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))
        self.add_action(SetVoltage(params["minimum_voltage_1"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true minimum 1 at medium power
        self.add_action(
            make_integration(
                voltage_source,
                params["scan_extremum_min"],
                min_voltage_1,
                label="min scan 1",
                extremum_mode=True,
            )
        )
        # now, min_voltage_1 store should contain decent minimum voltage

        ########### STEP 2
        # With the minimum point found and stored in the min_voltage_1 store, do
        # integrations at a list of powers, continuing to use the gradient
        # ascent/descent extremum method.
        ###########
        self.add_action(
            PowerRamp(
                voltage_source,
                powers,
                params["extremum_min"],
                min_voltage_1,
                extremum_mode=True,
            )
        )

        ########### STEP 3
        # Find another phase minimum at a different interferometer power/voltage.
        # Using an estimate in params["minimum_voltage_2"].
        ###########
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))
        self.add_action(SetVoltage(params["minimum_voltage_2"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true minimum 2 at medium power
        self.add_action(
            make_integration(
                voltage_source,
                params["scan_extremum_min"],
                min_voltage_2,
                label="min scan 2",
                extremum_mode=True,
            )
        )

        ########### STEP 3
        # We expect a phase maximum (180 degree) to lie directly between the minimums, and a
        # phase 'medium' (90 degree) to lie bewteen a minimum and a maximum. Estimate the
        # voltages of these points using DerivedVoltages. After this runs during the
        # measurment, the Stores 'derived_max' and 'derived_90' are updated with correct
        # voltages.
        ###########

        # now, min_voltage_2 store should contain decent minimum voltage
        self.add_action(
            DerivedVoltages(min_voltage_1, min_voltage_2, derived_max, derived_90)
        )

        ########### STEP 4
        # Do another set of integrations across shg powers, at the derived phase max
        # point just derived above.
        ###########

        # go to the min-defined max
        self.add_action(SetVoltage(derived_max, voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # ramp through powers at the min defined max
        self.add_action(
            PowerRamp(
                voltage_source,
                powers,
                params["extremum_max"],
                derived_max,
                extremum_mode=False,
            )
        )

        # back to scan power
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ########### STEP 5
        # Do another set of integrations across shg powers, at the derived phase 90
        # degree point.
        ###########

        # go to the min-defined 90 degree point
        self.add_action(SetVoltage(derived_90, voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # ramp through powers at the min defined 90 degree point
        self.add_action(
            PowerRamp(
                voltage_source,
                powers,
                params["extremum_max"],
                derived_90,
                extremum_mode=False,
            )
        )

        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ########### STEP 6
        # Do another set of integrations across shg powers, at the regular
        # max point (lower voltage).
        ###########

        # go to the regular max point
        self.add_action(SetVoltage(max_voltage, voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # ramp through powers
        self.add_action(
            PowerRamp(
                voltage_source,
                powers,
                params["extremum_max"],
                max_voltage,
                extremum_mode=True,
            )
        )

        self.add_action(SetPower(1.2, voltage_source, 1))
        self.add_action(Wait(4))
        self.enable_save(params["output_file_name"])


# copied from channel_visibility_dm.py
def make_integration(
    voltage_source, params, voltage, label="default_label", extremum_mode=True
):
    if extremum_mode:
        integration = Extremum(
            params["type"],
            params["int_time"],
            params["wait_time"],
            params["change_rate"],
            voltage_source,
            voltage,  # a store
            fine_grain_mode=params["fine_grain_mode"],
            low_res_steps=params["low_res_steps"],
            steps=params["steps"],
            int_type=params["int_type"],
            label=label,
        )
        integration.add_action(
            ValueIntegrateExtraData(
                params["minimum_counts"],
                minimum_evaluations=params["minimum_integrate_evaluations"],
                progress_bar=True,
            )
        )
        integration.init_custom_integration()
        integration.update_start_iteration(3)
    else:
        # no min or max gradient descent. Just stay at one voltage
        # and so a series of integrations.

        integration = SimpleSet(
            ValueIntegrateExtraData,
            [params["minimum_counts"], params["minimum_integrate_evaluations"]],
            params["steps"],
            label=label,
        )
    return integration


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
