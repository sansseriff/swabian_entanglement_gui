from .measurement_management import *


class ContinuousScanMin(Action):
    """
    Used to keep the phase stabilized at the minimum for a long time

    """

    def __init__(self, voltage_source, **kwargs):
        super().__init__(**kwargs)

        minimize = Extremum(
            "min",
            1,
            0.5,
            0.02,
            voltage_source,
            2.58,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=350,
            label="long_minimum_scan",
        )
        minimize.update_start_iteration(3)
        self.add_action(minimize)
        self.enable_save("continuous_scan_minimum.json")


class ConstantMin(Action):
    """
    Used to keep the phase stabilized at the minimum for a long time

    """

    def __init__(self, voltage_source, **kwargs):
        super().__init__(**kwargs)
        min_voltage = Store(voltage=2.58)
        minimize = Extremum(
            "min",
            1,
            0.5,
            0.02,
            voltage_source,
            2.58,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=10,
            label="long_minimum_scan",
        )
        minimize.update_start_iteration(3)
        self.add_action(minimize)

        for i in range(350):
            # self.add_action(Wait(0.5))
            self.add_action(Integrate(64))  # not sure yet
        self.enable_save("constant_minimum.json")
