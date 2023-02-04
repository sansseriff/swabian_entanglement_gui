import numpy as np
import logging


class PumpPowerManager:
    def __init__(self, vsource, channel):
        self.vsource = vsource
        self.channel = channel

        # self.max = 1.576  # the pot voltage that correlates with maximum pump power
        # self.max_amps = 3.52  # original shg max power
        self.voltage_vals = [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
        ]
        self.amperage_vals = [
            0.06,
            0.29,
            0.53,
            0.76,
            0.99,
            1.23,
            1.46,
            1.70,
            1.94,
            2.18,
            2.41,
            2.65,
            2.89,
            3.13,
            3.36,
            3.60,
            3.84,
            4.06,
        ]

    def change_pump_power(self, power):
        # if percentage > 114:
        #     print("Error, power too high")
        #     return 1
        if power > 4.0:
            print("Error, too much power")
            return {
                "expected_amps": 0,
                "voltage_sent": 0,
            }

        voltage = float(np.interp(power, self.amperage_vals, self.voltage_vals))
        # you need the float to convert from np.float64

        print(f"Sending voltage {round(voltage,2)}")
        print(f"requested SHG amperage {power}")
        self.vsource.setVoltage(self.channel, round(voltage, 3))

        return {
            "expected_amps": power,
            "voltage_sent": voltage,
        }
