from .measurement_management import *
import yaml


# start_voltage: 1
# end_voltage: 4.015
# voltage_step: 0.015
# wait_time: 10
# integration_time: 90


class WaitIntegrate(Action):
    def __init__(self, vsource, voltage, params, **kwargs):
        super().__init__(**kwargs)

        self.add_action(SetVoltage(voltage, vsource, 2))
        self.add_action(Wait(params["wait_time"]))
        self.add_action(Integrate(params["integration_time"]))


class FringeScan(Action):
    def __init__(self, voltage_source):
        super().__init__()
        with open("./measurements/fringe_scan.yaml", "r", encoding="utf8") as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        voltages = np.arange(
            params["start_voltage"], params["end_voltage"], params["voltage_step"]
        ).tolist()

        voltages = [round(voltage, 3) for voltage in voltages]

        self.add_action(SetVoltage(params["start_voltage"], voltage_source, 2))
        self.add_action(Wait(90))

        for voltage in voltages:
            self.add_action(WaitIntegrate(voltage_source, voltage, params))

        self.enable_save(params["output_file_name"])
