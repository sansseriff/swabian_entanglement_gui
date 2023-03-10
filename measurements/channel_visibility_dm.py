"""
channel_visibility_dm.py

Used for finding the visibility and coincidence rate at 2 power settings. 
The paper users this on each of the 8 channels pairings. 

This version uses a different maximum point (around 3.25 Volts), and 

"""

from .measurement_management import *
import yaml
from dataclasses import dataclass
from .pump_power_manager import PumpPowerManager
import logging
from .user_input import UserInput


class ChannelVisibility(Action):
    def __init__(
        self,
        voltage_source,
    ):
        super().__init__()

        with open(
            "./measurements/channel_visibility.yaml", "r", encoding="utf8"
        ) as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["channel_visibility"]
        print("######  DID YOU REMEMBER TO SET THE CORRECT FILE NAME IN THE YAML?")
        print("######  IS POLARIZATION MAXIMIZED?")
        min_voltage = Store(voltage=params["minimum_voltage"])
        max_voltage = Store(voltage=params["maximum_voltage"])

        # set to medium power
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ####### MINIMUM 1 (phase=0 degree)
        ####### ##########################
        # set interferometer voltage to something near the minimum
        self.add_action(SetVoltage(params["minimum_voltage"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true minimum
        self.add_action(
            self.make_integration(
                voltage_source, params["scan_extremum_min"], min_voltage
            )
        )
        # now, min_voltage store should contain decent minimum voltage

        # get fringe min data for low-power visibility
        self.add_action(SetPower(params["low_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(voltage_source, params["extremum_min"], min_voltage)
        )

        # get fringe min data for high-power visibility
        self.add_action(SetPower(params["high_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(voltage_source, params["extremum_min"], min_voltage)
        )

        # back to scanning power
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ####### MAXIMUM 1 (phase=180 degree)
        ####### ##########################
        # set interferometer voltage to something near the maximum
        self.add_action(SetVoltage(params["maximum_voltage"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true maximum
        self.add_action(
            self.make_integration(
                voltage_source, params["scan_extremum_max"], max_voltage
            )
        )
        # now, max_voltage store should contain decent maximum voltage

        # get max data for low-power visibility
        self.add_action(SetPower(params["low_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(voltage_source, params["extremum_max"], max_voltage)
        )

        # get max data for high-power visibility
        self.add_action(SetPower(params["high_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(voltage_source, params["extremum_max"], max_voltage)
        )

        # this all took about 1 hour 23 minutes with low power 1.2, high power 3.5
        # tomorrow I should set high power to 4.09

        # this is a huge hack to lower the data rate so that the file save doesn't segfault
        self.add_action(SetPower(1.3, voltage_source, 1))
        self.add_action(Wait(5))
        self.enable_save(save_name=params["output_file_name"])

    def make_integration(self, voltage_source, params, voltage):
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
        return integration


# def intf_power_from_voltage():


def intf_voltage_from_power(power: float) -> float:
    with open("./interferometer_resistance.json") as file:
        data = json.load(file)
        voltages = data["voltage"]
        resistances = data["resistance"]
        resistance = float(np.interp(power, voltages, resistances))
        # P = (V^2)/R
        return float(np.sqrt(power * resistance))

    # tomorrow you should check to see that the sent voltage and the measured voltage are really close.
    # Then don't even worry about measuring the current in the extremum method. Just assume phase is
    # linear with power, and you can convert power to voltage and the inverse of that with your
    # resistance curve.
