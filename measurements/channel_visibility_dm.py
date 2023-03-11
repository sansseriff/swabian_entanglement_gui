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


class Interferometer:
    def __init__(self, path):
        with open("./interferometer_resistance.json") as file:
            data = json.load(file)
        self.voltages = np.array(data["voltage"])
        self.resistances = np.array(data["resistance"])
        self.currents = self.voltages / self.resistances
        self.powers = self.currents * self.voltages

    def voltage_from_power(self, power: float) -> float:
        voltage = float(np.interp(power, self.powers, self.voltages))
        return voltage

    def power_from_voltage(self, voltage: float) -> float:
        power = float(np.interp(voltage, self.voltages, self.powers))
        return power


class DerivedVoltages(Action):
    def __init__(
        self,
        minimum_1: Store,
        minimum_2: Store,
        derived_max: Store,
        derived_90: Store,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.minimum_1 = minimum_1
        self.minimum_2 = minimum_2
        self.derived_max = derived_max
        self.derived_90 = derived_90
        self.intf = Interferometer("./interferometer_resistance.json")

    def evaluate(self, current_time, counts, **kwargs):
        min_power_1 = self.intf.power_from_voltage(self.minimum_1.get_val())
        min_power_2 = self.intf.power_from_voltage(self.minimum_2.get_val())
        derived_max_power = float(np.average([min_power_1, min_power_2]))
        derived_90_power = float(np.average([min_power_1, derived_max_power]))

        derived_90_voltage = self.intf.voltage_from_power(derived_90_power)
        derived_max_voltage = self.intf.voltage_from_power(derived_max_power)
        print(f"##### derived max voltage: {derived_max_voltage}")
        print(f"##### derived 90 voltage: {derived_90_voltage}")

        self.derived_max.set_val(derived_max_voltage)
        self.derived_90.set_val(derived_90_voltage)

        # this is a bad practice! If this method does not have a return value with the key "finished",
        # then it breaks and it's hard to debug!!

        # I think this could be solved with a decorator that would put in the "finished" if I forgot to
        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "derived_max_voltage": derived_max_voltage,
            "dervied_90_voltage": derived_90_voltage,
        }
        return self.final_state


class ChannelVisibilityDM(Action):
    """
    Channel visibility measurement that collects all data to derive a
    density matrix at two powers
    """

    def __init__(
        self,
        voltage_source,
    ):
        super().__init__()

        with open(
            "./measurements/channel_visibility_dm.yaml", "r", encoding="utf8"
        ) as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["channel_visibility"]
        print("######  DID YOU REMEMBER TO SET THE CORRECT FILE NAME IN THE YAML?")
        print("######  IS POLARIZATION MAXIMIZED?")

        min_voltage_1 = Store(voltage=params["minimum_voltage_1"])
        min_voltage_2 = Store(voltage=params["minimum_voltage_2"])
        max_voltage = Store(voltage=params["maximum_voltage"])
        derived_max = Store(voltage=0)  # to be updated later
        derived_90 = Store(voltage=0)

        # set to medium power
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ####### MINIMUM 1 (phase=0 degree)
        ####### ##########################
        # set interferometer voltage to something near the minimum
        self.add_action(SetVoltage(params["minimum_voltage_1"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true minimum
        self.add_action(
            self.make_integration(
                voltage_source,
                params["scan_extremum_min"],
                min_voltage_1,
                label="min scan 1",
            )
        )
        # now, min_voltage_1 store should contain decent minimum voltage

        # get fringe min data for low-power visibility
        self.add_action(SetPower(params["low_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(
                voltage_source,
                params["extremum_min"],
                min_voltage_1,
                label="min integrate low power",
            )
        )

        # get fringe min data for high-power visibility
        self.add_action(SetPower(params["high_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            self.make_integration(
                voltage_source,
                params["extremum_min"],
                min_voltage_1,
                label="min integrate high power",
            )
        )

        # back to scanning power
        self.add_action(SetPower(params["scan_power"], voltage_source, 1))

        ####### ########################## begin new part
        ####### ##########################
        ####### MINIMUM 2 (phase=360 degree)
        # set interferometer voltage to something near the minimum
        self.add_action(SetVoltage(params["minimum_voltage_2"], voltage_source, 2))
        self.add_action(Wait(params["intf_stabilize_time"]))

        # scan for true minimum
        self.add_action(
            self.make_integration(
                voltage_source,
                params["scan_extremum_min"],
                min_voltage_2,
                label="min scan 2",
            )
        )
        # now, min_voltage_2 store should contain decent minimum voltage

        self.add_action(
            DerivedVoltages(min_voltage_1, min_voltage_2, derived_max, derived_90)
        )

        # go to the min-defined max
        self.add_action(SetVoltage(derived_max, voltage_source, 2))
        self.add_action(SetPower(params["low_power"], voltage_source, 1))
        self.add_action(Wait(params["intf_stabilize_time"]))
        self.add_action(
            ValueIntegrateExtraData(
                10000,
                3,
                progress_bar=True,
                label="min-defined max integration low power",
            )
        )
        self.add_action(SetPower(params["high_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            ValueIntegrateExtraData(
                10000,
                3,
                progress_bar=True,
                label="min-defined max integration high power",
            )
        )

        # go to the min-defined 90 degree
        self.add_action(SetVoltage(derived_90, voltage_source, 2))
        self.add_action(SetPower(params["low_power"], voltage_source, 1))
        self.add_action(Wait(params["intf_stabilize_time"]))
        self.add_action(
            ValueIntegrateExtraData(
                5000, 3, progress_bar=True, label="90 degree integration low power"
            )
        )
        self.add_action(SetPower(params["high_power"], voltage_source, 1))
        self.add_action(Wait(params["power_stabilize_time"]))
        self.add_action(
            ValueIntegrateExtraData(
                5000, 3, progress_bar=True, label="90 degree integration high power"
            )
        )

        ####### ########################## end new part
        ####### ##########################

        # back to scan power
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

    def make_integration(self, voltage_source, params, voltage, label="default_label"):
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
        return integration

    # P = IV = (V/R)V = (V^2)/R(V)
    # P*R(V) = V^2
    # np.sqrt(P*R(V)) = V

    # P = IV = (V^2)/R(V)

    # V = IR


# tomorrow you should check to see that the sent voltage and the measured voltage are really close.
# Then don't even worry about measuring the current in the extremum method. Just assume phase is
# linear with power, and you can convert power to voltage and the inverse of that with your
# resistance curve.

# And figure out what is wrong with git push
