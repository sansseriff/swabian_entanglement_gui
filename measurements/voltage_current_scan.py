from .measurement_management import *


"""
for finding the relationship between current and voltage for the interferometer. 
Should be a simple linear relationship?
"""


class VoltageCurrentScan(Action):
    def __init__(self, vsource):
        super().__init__()
        self.vsource = vsource
        steps = np.linspace(0, 4, 161)
        for step in steps:
            self.add_action(SetVoltage(step, self.vsource, 2))
            self.add_action(Wait(3))
            self.add_action(GetVoltageCurrent(self.vsource, 2, label="get_test_1"))
            self.add_action(Wait(3))
            self.add_action(GetVoltageCurrent(self.vsource, 2, label="get_test_2"))
            self.add_action(Wait(3))
            self.add_action(GetVoltageCurrent(self.vsource, 2, label="get_test_3"))
            self.add_action(Wait(3))
            self.add_action(GetVoltageCurrent(self.vsource, 2, label="get_test_4"))
            self.enable_save(save_name="voltage_current_scan.json")
