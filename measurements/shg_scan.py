from measurement_management import *


class InputandMinimizeSHG(Action):
    def __init__(self, start_value, req_shg_power):
        self.environment = {}
        self.add_action(Input(f"input {shg_power} power", environ=self.environment))
        self.add_action(FineGrainMinimze(start_value))
        # you should setup save_action so that the local self.environment gets saved.
        self.enable_save()


class SHG_Scan(Action):
    def __init__(self):

        shg_powers = np.linspace(
            params["start_power"], params["end_power"], params["steps"]
        )
        self.environment = {}
        # use environment instead of SequentialAction
        self.add_action(Minimize(start_value, environ=environment))
        for shg_power in shg_powers:
            self.add_action(InputandMinimizeSHG())
