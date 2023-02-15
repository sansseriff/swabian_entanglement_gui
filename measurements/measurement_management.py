from multiprocessing import Event
import time
import numpy as np
import json
import random
from dataclasses import dataclass
from .pump_power_manager import PumpPowerManager
import logging
import orjson

"""
The action framework is used to build and specify measurements in a composable and modular fashion so that they
are carried out step by step in the programs main even loop. 


Actions can contain other actions, 
or actions can be customized to do specific things

Andrew Mueller 2022
"""

logger = logging.getLogger("measure")


class Action:
    def __init__(self):
        self.event_list = []
        self.init_time = -1
        self.results = []
        self.pass_state = False
        self.save_name = "output_file.json"
        self.save = False
        self.environment = {}  # used for accessing persistent data
        logger.debug(f"Initializing Action: {self.__class__.__name__}")

    def add_action(self, object):
        self.event_list.append(object)

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        if self.pass_state:
            return {"state": "passed"}
            """remember how I decided an object should be allowed 
            to deactivate itself, but it should not delete itself"""
        responses = []
        while True:
            response = self.event_list[0].evaluate(current_time, counts, **kwargs)
            responses.append(response)
            if response["state"] == "abort":
                self.pass_state = True
                print("aborting ", self.__class__.__name__)
                return {"state": "abort", "name": self.__class__.__name__}
            if response["state"] != "finished":
                break
            else:
                response.pop("state", None)
                self.results.append(response)
                self.event_list.pop(0)
                if len(self.event_list) == 0:
                    self.pass_state = True  # deactivates this function in this object
                    self.final_state = {
                        "state": "finished",
                        "name": self.__class__.__name__,
                        "results": self.flatten(self.results),
                    }
                    if self.save:
                        self.do_save()
                    return self.final_state
        return {"state": "waiting", "results": responses}

        # how do I bubble up the results from the scan? In each evaluate?

    def flatten(self, results):
        # to be overridden by child classes
        return results

    def search(self, a_dict, search_type):
        # this is useful for finding types that orjson cannot serialize
        for key, value in a_dict.items():
            if type(value) is search_type:
                print(f"found {str(search_type)} with key: {key}")
            if type(value) is dict:
                self.search(value, search_type)
            if type(value) is list:
                for item in value:
                    if type(item) is dict:
                        self.search(item, search_type)

    def do_save(self):
        self.search(self.final_state, np.float64)
        # with open(self.save_name, "w") as file:
        #     file.write(json.dumps(self.final_state))

        # self.save_name could be a Store
        logger.info(f"     {self.__class__.__name__}: Starting save")
        with open(self.current_value(self.save_name), "wb") as file:
            file.write(orjson.dumps(self.final_state))
        logger.info(f"     {self.__class__.__name__}: Ending save")

    def enable_save(self, save_name="output_file.json"):
        self.save_name = save_name
        self.save = True

    def current_value(self, value):
        # if (type(value) is int) or (type(value) is float):
        #     return value
        # if type(value) is Store:
        #     assert (type(value.get_val()) is int) or (type(value.get_val()) is float)
        #     return value.get_val()
        if type(value) is Store:
            return value.get_val()
        else:
            return value

    def __str__(self):
        return "Action Object"

    def pretty_print(self, data):
        print(json.dumps(data, sort_keys=True, indent=4))


@dataclass
class Store:
    __allowed = ("voltage", "counts", "power", "name")

    def __init__(self, **kwargs):
        assert len(kwargs.items()) == 1
        for k, v in kwargs.items():
            self.key = k
            assert k in self.__class__.__allowed
            setattr(self, k, v)

    def __str__(self):
        return str(self.__dict__)

    def export(self):
        return self.__dict__

    def set_val(self, value):
        assert type(self.__dict__[self.key]) is type(value)
        self.__dict__[self.key] = value

    def get_val(self):
        return self.__dict__[self.key]


class SetVoltage(Action):
    def __init__(self, voltage, vsource, channel):
        super().__init__()
        self.vsource = vsource
        self.voltage = voltage
        self.channel = channel

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        current_voltage = self.current_value(self.voltage)  # if self.voltage is a Store
        self.vsource.setVoltage(self.channel, round(current_voltage, 3))
        print("####### setting voltage to", round(current_voltage, 3))
        logger.info(
            f"     {self.__class__.__name__}: setting voltage to: {round(current_voltage, 3)}"
        )
        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "voltage": current_voltage,
        }
        return self.final_state

    def __str__(self):
        return "SetVoltage Action Object"


class SetPower:
    def __init__(self, power, vsource, channel):
        super().__init__()
        self.power = power
        self.power_manager = PumpPowerManager(vsource, channel)

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        logger.info(
            f"     {self.__class__.__name__}: setting power to: {round(self.power, 3)}"
        )
        result = self.power_manager.change_pump_power(self.power)

        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "result": result,
        }
        return self.final_state

    def __str__(self):
        return "SetVoltage Action Object"


class GetVoltageCurrent(Action):
    def __init__(self, vsource, channel):
        super().__init__()
        self.vsource = vsource
        self.channel = channel

    def evaluate(self, current_time, counts, **kwargs):
        current = self.vsource.getCurrent(self.channel)
        voltage = self.vsource.getVoltage(self.channel)
        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "current": current,
            "voltage": voltage,
        }
        return self.final_state

    def __str__(self):
        return "GetVoltage Action Object"


class Wait(Action):
    def __init__(self, wait_time):
        super().__init__()
        self.wait_time = wait_time

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        if self.init_time == -1:
            self.init_time = time.time()
        if (current_time - self.init_time) > self.wait_time:
            logger.info(
                f"     {self.__class__.__name__}: Finishing. Time Waited: {round(current_time - self.init_time,2)}"
            )
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "time_waited": current_time - self.init_time,
            }
            return self.final_state

        return {"state": "waiting"}

    def __str__(self):
        return "Wait Action Object"

    def reset(self):
        self.init_time = -1


class Integrate(Action):
    def __init__(self, int_time):
        super().__init__()
        self.int_time = int_time
        self.counts = 0
        self.coincidences = 0
        self.hist_1 = None
        self.hist_2 = None

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        if self.init_time == -1:
            self.init_time = current_time
            self.hist_1 = np.zeros_like(kwargs.get("hist_1"))
            self.hist_2 = np.zeros_like(kwargs.get("hist_2"))
            return {"state": "integrating"}
        else:
            # only add counts for evaluations after the init evaluation
            self.counts = self.counts + counts  # add counts
            print("self.coincidences: ", self.coincidences)
            print("kwargs.get('coincidences'): ", kwargs.get("coincidences"))
            self.coincidences += kwargs.get("coincidences")
            self.hist_1 += kwargs.get("hist_1")
            self.hist_2 += kwargs.get("hist_2")

        if (current_time - self.init_time) > self.int_time:
            self.delta_time = current_time - self.init_time
            logger.info(
                f"     {self.__class__.__name__}: Finishing. Time Integrating: {round(self.delta_time,3)}"
            )
            singles_rate_1 = float(np.sum(self.hist_1) / self.delta_time)
            singles_rate_2 = float(np.sum(self.hist_2) / self.delta_time)
            coincidence_rate = self.coincidences / self.delta_time
            print("singles_rate_1: ", round(singles_rate_1, 3))
            print("singles_rate_2: ", round(singles_rate_2, 3))
            print("coincidence_rate: ", round(coincidence_rate, 3))

            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "counts": self.counts,
                "delta_time": self.delta_time,
                "coincidences": self.coincidences,
                "singles_rate_1": singles_rate_1,
                "singles_rate_2": singles_rate_2,
                "coincidence_rate": coincidence_rate,
            }
            return self.final_state
        return {"state": "integrating"}

    def reset(self):
        self.init_time = -1
        self.counts = 0
        self.coincidences = 0

    def __str__(self):
        return "Integrate Object"


class ValueIntegrate(Action):
    def __init__(self, min_counts):
        super().__init__()
        self.min_counts = min_counts
        self.counts = 0

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        if self.init_time == -1:
            self.init_time = current_time
            # started
            logger.info(f"     {self.__class__.__name__}: Starting Integrate")
        else:
            self.counts = self.counts + counts  # add counts

        if self.counts > self.min_counts:
            # finish up
            logger.info(
                f"     {self.__class__.__name__}: Finishing. Time: {round(self.delta_time,3)} Counts: {self.counts}"
            )
            self.delta_time = current_time - self.init_time
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "counts": self.counts,
                "delta_time": self.delta_time,
            }
            return self.final_state
        return {"state": "integrating"}

    def reset(self):
        self.init_time = -1
        self.counts = 0

    def __str__(self):
        return "ValueIntegrate Action Object"


class ValueIntegrateExtraData(Action):
    def __init__(self, min_counts, minimum_evaluations=3):
        super().__init__()
        self.min_counts = min_counts
        self.counts = 0
        self.coincidences_hist_1 = []
        self.coincidences_hist_2 = []
        self.full_coinc_1 = []
        self.full_coinc_2 = []
        self.hist_1 = None
        self.hist_2 = None
        self.evaluations = 0
        self.minimum_evaluations = minimum_evaluations
        self.coincidences = 0

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.__class__.__name__}")
        self.evaluations += 1

        if self.init_time == -1:
            self.init_time = current_time
            # started
            logger.info(f"     {self.__class__.__name__}: Starting Integrate")
            self.hist_1 = np.zeros_like(kwargs.get("hist_1"))
            self.hist_2 = np.zeros_like(kwargs.get("hist_2"))

        else:
            # only add counts for iterations after the init iteration.
            # count data 'belongs' to the time bewteen the init iteration and the ending iteration
            self.counts += counts  # add counts
            self.coincidences_hist_1.extend(kwargs.get("coincidence_array_1"))
            self.coincidences_hist_2.extend(kwargs.get("coincidence_array_2"))
            self.full_coinc_1.extend(kwargs.get("full_coinc_1"))
            self.full_coinc_2.extend(kwargs.get("full_coinc_2"))
            self.hist_1 += kwargs.get("hist_1")
            self.hist_2 += kwargs.get("hist_2")
            self.coincidences += kwargs.get("coincidences")
            logger.debug(
                f"     {self.__class__.__name__}: Adding counts. Counts: {self.counts}"
            )

        if (self.counts > self.min_counts) and (
            self.evaluations > self.minimum_evaluations
        ):
            self.delta_time = current_time - self.init_time
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "counts": self.counts,
                "delta_time": self.delta_time,
                "coincidences_hist_1": self.coincidences_hist_1,
                "coincidences_hist_2": self.coincidences_hist_2,
                "full_coinc_1": self.full_coinc_1,
                "full_coinc_2": self.full_coinc_2,
                "singles_hist_1": self.hist_1.tolist(),
                "singles_hist_2": self.hist_2.tolist(),
                "total_coincidences": self.coincidences,
            }
            logger.info(
                f"     {self.__class__.__name__}: Finishing. Counts: {self.counts}, delta_time: {round(self.delta_time,2)}"
            )
            return self.final_state
        return {"state": "integrating"}

    def reset(self):
        logger.info(f"     {self.__class__.__name__}: Resetting Action")
        self.init_time = -1
        self.counts = 0
        self.coincidences_hist_1 = []
        self.coincidences_hist_2 = []
        self.full_coinc_1 = []
        self.full_coinc_2 = []
        self.evaluations = 0
        self.coincidences = 0

    def __str__(self):
        return "ValueIntegrate Action Object"


class VoltageAndIntegrate(Action):
    def __init__(
        self, voltage, vsource, voltage_channel, inter_wait_time, time_per_point
    ):
        super().__init__()
        self.vsource = vsource
        self.voltage_channel = voltage_channel
        self.inter_wait_time = inter_wait_time
        self.time_per_point = time_per_point

        self.add_action(SetVoltage(voltage, self.vsource, self.voltage_channel))
        self.add_action(Wait(self.inter_wait_time))
        self.add_action(GetVoltageCurrent(self.vsource, self.voltage_channel))
        self.add_action(Integrate(self.time_per_point))

    def evaluate(self, current_time, counts, **kwargs):
        return super().evaluate(current_time, counts, **kwargs)

    def flatten(self, results):
        res = {}
        check_list = ["voltage", "time_waited", "current", "counts", "delta_time"]
        for result in results:
            for item in check_list:
                if result.get(item) is not None:
                    res[item] = result.get(item)

        return res


class DistributeData(Action):
    def __init__(self, data_name):
        super().__init__()
        self.data_name = data_name
        self.initialized = False

    def evaluate(self, current_time, counts, **kwargs):
        if self.initialized is False:
            self.data = kwargs.get(self.data_name)
            if kwargs.get(self.data_name) is None:
                logger.warning(
                    f"     {self.__class__.__name__}: Error: injected data is None"
                )
            logger.info(f"     {self.__class__.__name__}: Data for distribution loaded")
            self.initialized = True

        if self.pass_state:
            return {"state": "passed"}
            """remember how I decided an object should be allowed 
            to deactivate itself, but it should not delete itself"""
        # need to drop down the prev_data from the recursive call!! That's confusing..
        # do that by repeating the **kwargs here:
        response = self.event_list[0].evaluate(
            current_time, counts, **{self.data_name: self.data}
        )
        if (
            response["state"] == "finished"
        ):  # might want to change these to response.get()
            response.pop("state", None)
            self.results.append(response)
            self.event_list.pop(0)
            if len(self.event_list) == 0:
                logger.info(f"     {self.__class__.__name__}: Finishing action")
                self.pass_state = True  # deactivates this function in this object
                self.final_state = {
                    "state": "finished",
                    "name": self.__class__.__name__,
                    "results": self.results,
                }
                if self.save:
                    self.do_save()
                return self.final_state

            # Distribute Action
            # provide the data injected during initialization
            self.evaluate(current_time, counts, **{self.data_name: self.data})

        # this intermediate return can be passed to a graph by ConcurrentAction
        return {"state": "waiting", "results": response}

    # this should take in and store some data that is provided on the first call to evaluate.
    # then it provides that data to sub-actions when they are initialized.


class DependentAction(Action):
    def __init__(self, data_name):
        super().__init__()
        self.data_name = data_name

    def evaluate(self, current_time, counts, **kwargs):
        if self.pass_state:
            return {"state": "passed"}
            """remember how I decided an object should be allowed 
            to deactivate itself, but it should not delete itself"""
        # need to drop down the prev_data from the recursive call!! That's confusing..
        # do that by repeating the **kwargs here:
        response = self.event_list[0].evaluate(current_time, counts, **kwargs)
        if (
            response["state"] == "finished"
        ):  # might want to change these to response.get()
            response.pop("state", None)
            self.results.append(response)
            self.event_list.pop(0)
            if len(self.event_list) == 0:
                print("finished event action: ", self.__class__.__name__)
                self.pass_state = True  # deactivates this function in this object
                self.final_state = {
                    "state": "finished",
                    "name": self.__class__.__name__,
                    "results": self.results,
                }
                if self.save:
                    self.do_save()
                return self.final_state

            # Dependent Action
            # take the data and put give it to the next object
            self.evaluate(current_time, counts, **{self.data_name: response})

        # this intermediate return can be passed to a graph by ConcurrentAction
        return {"state": "waiting", "results": response}

    # def flatten_response(self, response):
    #     # used for pretty print
    #     print(json.dumps(response, sort_keys=True, indent=4))


class Scan(Action):
    def __init__(self, scan_params, vsource):
        super().__init__()
        self.vsource = vsource
        self.scan_params = scan_params
        self.voltage_array = np.linspace(
            self.scan_params["start_voltage"],
            self.scan_params["end_voltage"],
            self.scan_params["steps"],
        )
        for voltage in self.voltage_array:
            self.add_action(
                VoltageAndIntegrate(
                    voltage,
                    self.vsource,
                    self.scan_params["voltage_channel"],
                    self.scan_params["inter_wait_time"],
                    self.scan_params["time_per_point"],
                )
            )

    # def flatten_evaluate(self, scan_params, vsource):
    #     result = self.evaluate(scan_params, vsource)
    #     if result.get("state") == "finished":
    #         for item in result:
    #             if

    def __str__(self):
        return "Scan Action Object"

    def print(self):
        print(self.__class__)

    def flatten(self, results):
        res = {}
        for i, result in enumerate(results):
            data = result.get("results")  # data is something like:
            """
            {
                "counts": 5279,
                "current": 0.0042,
                "delta_time": 1.047443151473999,
                "time_waited": 0.12920880317687988,
                "voltage": 0.1002
            }
            """
            if i == 0:
                for key in data.keys():
                    res[key] = []
                    res[key].append(data[key])
            else:
                for key in data.keys():
                    res[key].append(data[key])

        arr = np.array(res["counts"]) / np.array(res["delta_time"])
        res["viz"] = arr.tolist()
        return res


class StepScan(Action):
    """
    Partial scan in two locations. This is biolerplate-y
    """

    def __init__(self, scan_params, vsource):
        super().__init__()
        self.vsource = vsource
        self.scan_params = scan_params
        self.voltage_array = np.linspace(
            self.scan_params["start_voltage"],
            self.scan_params["end_voltage"],
            self.scan_params["steps"],
        )
        self.voltage_array = np.concatenate((np.zeros(50) + 1.66, np.zeros(670) + 2.57))

        for voltage in self.voltage_array:
            self.add_action(
                SetVoltage(voltage, self.vsource, self.scan_params["voltage_channel"])
            )
            self.add_action(Wait(self.scan_params["inter_wait_time"]))
            self.add_action(
                GetVoltageCurrent(self.vsource, self.scan_params["voltage_channel"])
            )
            self.add_action(Integrate(self.scan_params["time_per_point"]))

    def __str__(self):
        return "Scan Action Object"


class UnspecifiedExtremum(Exception):
    pass


class Extremum(Action):
    def __init__(
        self,
        extremum_type,
        integration_time,
        wait_time,
        change_rate,
        vsource,
        init_voltage,
        data_name="prev_data",
        fine_grain_mode=False,
        low_res_steps=8,
        iteration_increase=False,
        steps=7,
        int_type="regular",
    ):
        super().__init__()
        self.extremum_type = extremum_type
        if (self.extremum_type != "min") and (self.extremum_type != "max"):
            raise UnspecifiedExtremum(
                f"{str(self.extremum_type)} is not 'max' or 'min'"
            )

        self.change_rate = change_rate
        self.original_rate = change_rate
        self.low_res_steps = low_res_steps
        self.int_type = int_type
        self.steps = steps
        self.iteration_increase = iteration_increase
        self.add_action(Wait(wait_time))

        if self.int_type == "regular":
            self.add_action(Integrate(integration_time))
            self.int_name = self.event_list[1].__class__.__name__
        self.org_integration_time = integration_time
        self.vsource = vsource
        # could be overridden by scan data supplied with evaluate
        self.voltage = init_voltage  # can be either a number or a Store
        self.fine_grain_status = "deactivated"
        self.direction = Direction()
        self.channel = 2
        self.prev_coinc_rate = -1
        self.init = False
        self.direction_list = []
        self.direction_array = []  # a list of lists of directions.
        # each fine-grain iteration gets its own list

        self.counts_list = []
        self.times_list = []
        self.voltage_list = []

        self.integration_results = []
        self.data_name = data_name
        self.cycle = 0
        self.fine_grain_iteration = 0
        if fine_grain_mode:
            self.fine_grain_mode = True
        else:
            self.fine_grain_mode = False
        self.data_color_list = ["#eb2121", "#db21b6", "#9a21db", "#5257d9"]
        self.data_color = "#fcc244"
        self.old_voltage = None
        self.update_rate()
        if self.int_type == "regular":
            self.update_time()

    def update_rate(self):
        self.change_rate = self.original_rate * (0.5**self.fine_grain_iteration)
        logger.info(
            f"     {self.__class__.__name__}: Updating rate. New rate: {self.change_rate}"
        )

    def update_time(self):
        self.event_list[1].int_time = self.org_integration_time * (
            4**self.fine_grain_iteration
        )
        logger.info(
            f"     {self.__class__.__name__}: Updating time. New time: {self.event_list[1].int_time}"
        )

    def get_voltage(self):
        if (type(self.voltage) is int) or (type(self.voltage) is float):
            return self.voltage
        if type(self.voltage) is Store:
            assert (type(self.voltage.get_val()) is int) or (
                type(self.voltage.get_val()) is float
            )
            return self.voltage.get_val()

    def set_voltage(self, value):
        if (type(self.voltage) is int) or (type(self.voltage) is float):
            self.voltage = value
        if type(self.voltage) is Store:
            self.voltage.set_val(value)

    def update_start_iteration(self, iteration):
        self.fine_grain_iteration = iteration
        if self.int_type == "regular":
            self.update_rate()
            self.update_time()
        if self.int_type == "custom":
            self.update_rate()

    def init_custom_integration(
        self,
    ):  # use this after add_action when using a custom integration method.
        self.int_name = self.event_list[1].__class__.__name__

    def evaluate(self, current_time, counts, **kwargs):
        if len(self.event_list) <= 1:
            raise Exception(
                "In custom integrate mode, add_action must be used to add an integration action"
            )

        if self.init is False:
            if kwargs.get(self.data_name) is not None:
                logger.info(
                    f"     {self.__class__.__name__}: Data loaded with name: {self.data_name}"
                )
                if self.extremum_type == "min":
                    idx_extreme = np.argmin(kwargs[self.data_name]["results"]["viz"])
                if self.extremum_type == "max":
                    idx_extreme = np.argmax(kwargs[self.data_name]["results"]["viz"])

                voltage_min = kwargs[self.data_name]["results"]["voltage"][idx_extreme]
                print("voltage min: ", voltage_min)

                # self.voltage = voltage_min  # apply minimum from graph
                self.set_voltage(voltage_min)
            logger.info(
                f"     {self.__class__.__name__}: Updating init voltage: {round(self.get_voltage(), 3)}"
            )
            self.vsource.setVoltage(self.channel, round(self.get_voltage(), 3))
            self.init = True

        response = self.event_list[self.cycle].evaluate(current_time, counts, **kwargs)

        if response.get("state") == "finished":
            if self.cycle == 1:  # alternate bewteen Wait and integrate
                self.cycle = 0
            else:
                self.cycle = 1

            if response.get("name") == self.int_name:
                # the integration is finished
                logger.info(
                    f"     {self.__class__.__name__}: Finished integrate, resetting integrate"
                )
                self.integration_results.append(response)
                self.event_list[0].reset()
                self.event_list[1].reset()  # reset the integrate
                self.counts_list.append(response["counts"])
                print("counts: ", response["counts"])
                print("times: ", response["delta_time"])
                self.times_list.append(response["delta_time"])
                # print("integrate response: ", response)
                coinc_rate = response["counts"] / response["delta_time"]
                print("## coinc rate: ", round(coinc_rate, 2))

                if (coinc_rate == self.prev_coinc_rate) or (self.prev_coinc_rate == -1):
                    self.direction_list.append(self.direction.random())
                else:
                    if coinc_rate > self.prev_coinc_rate:
                        # increased
                        if self.extremum_type == "min":
                            self.direction_list.append(self.direction.reverse())

                        else:
                            self.direction_list.append(self.direction())
                            print("no direction change")
                            logger.info(
                                f"     {self.__class__.__name__}: no direction change"
                            )

                    else:
                        # decreased
                        if self.extremum_type == "min":
                            self.direction_list.append(self.direction())
                            logger.info(
                                f"     {self.__class__.__name__}: no direction change"
                            )
                        else:
                            self.direction_list.append(self.direction.reverse())

                delta = self.change_rate * self.direction()
                self.old_voltage = self.get_voltage()
                self.set_voltage(self.get_voltage() + delta)
                logger.info(
                    f"     {self.__class__.__name__}: Updating voltage: {round(self.get_voltage(), 3)}"
                )
                print(f"#### Updating voltage: {round(self.get_voltage(), 3)}")
                print()
                self.vsource.setVoltage(self.channel, round(self.get_voltage(), 3))
                self.voltage_list.append(self.old_voltage)
                self.prev_coinc_rate = coinc_rate

                if (
                    self.fine_grain_mode
                    and len(self.direction_list) > self.low_res_steps
                ):
                    imbalance = self.direction_list[-8:]
                    if (
                        abs(sum(imbalance)) <= 3
                        and self.fine_grain_iteration <= 3
                        and self.iteration_increase
                    ):  # no beyond 3
                        self.fine_grain_iteration += 1
                        print(
                            "FINE GRAIN MODE, ITERATION: ",
                            self.fine_grain_iteration,
                        )

                        self.update_rate_time()

                        self.fine_grain_status = "activated"
                        last_direction = self.direction_list[-1]
                        self.direction_array.append(self.direction_list)
                        self.direction_list = [last_direction]
                        self.data_color = self.data_color_list[
                            self.fine_grain_iteration - 1
                        ]

                # stop minimization after 2nd fine grain iteration
                logger.info(
                    f"     {self.__class__.__name__}: Finishing step {len(self.direction_list)} of {self.steps}"
                )
                if (
                    len(self.direction_list) >= self.steps
                    and self.fine_grain_iteration == 3
                ):
                    logger.info(
                        f"     {self.__class__.__name__}: Finishing. counts_list: {self.counts_list}, times_list: {self.times_list}, voltage_list: {self.voltage_list}"
                    )
                    # imbalance = self.direction_list[-4:]
                    # self.direction_array.append(self.direction_list)
                    # print("imbalance list: ", imbalance)
                    # print("sum of imbalance list: ", sum(imbalance))
                    self.final_state = {
                        "state": "finished",
                        "name": self.__class__.__name__,
                        "results": {
                            "counts_list": self.counts_list,
                            "times_list": self.times_list,
                            "direction_array": self.direction_array,
                            "voltage_list": self.voltage_list,
                        },
                        "integration_results": self.integration_results,
                    }
                    if self.save:
                        self.do_save()
                    return self.final_state
                logger.info(
                    f"     {self.__class__.__name__}: Working. Processing integration finished. coinc_rate: {round(coinc_rate,2)}"
                )
                return {
                    "state": "working",
                    "name": self.__class__.__name__,
                    "results": {
                        "voltage": self.old_voltage,  # the voltage that was chosen previously and matches the counts from this round. Not the voltage that was chosen this round
                        "coinc_rate": coinc_rate,
                        "color": self.data_color,
                    },
                }

        logger.debug(f"     {self.__class__.__name__}: Working. ")
        return {"state": "working", "name": self.__class__.__name__}

    def __str__(self):
        return "Minimize Action Object"


class ConcurrentAction(Action):
    # do multiple evalations of multiple objects in the same event loop
    # either object can end the action by returning a {"state": "finished"}

    # this is kind of like a master/slave architecture, because one internal action (measurment) kinda decides
    # what happens to the other action (make graph)
    def __init__(self, *objects):
        self.objects = objects  # this is a tuple of objects

        self.intermediate_result = None  # this gets overwritten with each evaluate
        # self.action_information = {"action": "concurrent_action", "state": "working"}
        self.pass_state = False

    def evaluate(self, current_time, counts, **kwargs):
        if self.pass_state:
            return {"state": "passed"}

        for object in self.objects:
            # actions alternate sharing intermediate results
            self.intermediate_result = object.evaluate(
                current_time, counts, graph_data=self.intermediate_result
            )
            if self.intermediate_result.get("state") == "finished":
                self.pass_state = True
                self.final_state = {
                    "state": "finished",
                    "name": self.__class__.__name__,
                    "results": self.intermediate_result,
                }
                return self.final_state
        return {"state": "working", "name": self.__class__.__name__}


class GraphUpdate(Action):
    def __init__(self, axis):
        self.axis = axis

        self.data = None
        self.pass_state = False
        self.x_data = []
        self.y_data = []
        self.axis.clear()
        self.x_scatter = []
        self.y_scatter = []

        self.plot = self.axis.plot(self.x_data, self.y_data)

        self.scatters = []
        self.init = False
        self.color = None

    def results_dive(self, dic, key):
        if dic is None:
            return dic

        if isinstance(dic, list):
            # print("this is the dic: ", dic)
            results = []
            for item in dic:
                results.append(self.results_dive(item, key))
            # assert len(results) == 1
            # print("this is the results ", results)
            # print(results)
            for result in results:
                if result is not None:
                    return result
        if isinstance(dic, dict):
            if dic.get("results") is not None:
                return self.results_dive(dic.get("results"), key)
            else:
                # print(dic.get(key))
                # print(dic)
                return dic.get(key)
        else:
            return None
            # print("This is the type: ", type(dic))
            # raise TypeError("Type other than list or dict found in results")

    def evaluate(self, current_time, counts, **kwargs):
        if self.init is False:
            self.axis.set_yscale("log")
            self.axis.grid()
            self.init = True

        self.data = kwargs
        # off_state = {"state": "not_graphing", "name": self.__class__.__name__}

        graph_data = self.data.get("graph_data")
        # print("results: ", graph_data)
        # print(graph_data)

        delta_time = self.results_dive(graph_data, "delta_time")
        counts = self.results_dive(graph_data, "counts")
        voltage = self.results_dive(graph_data, "voltage")

        color = self.results_dive(graph_data, "color")
        coinc_rate = self.results_dive(graph_data, "coinc_rate")
        # if coinc_rate is not None:
        #     print(coinc_rate)

        if (counts is not None) and (delta_time is not None) and (voltage is not None):
            self.x_data.append(voltage)
            self.y_data.append(counts / delta_time)
            self.plot[0].set_data(self.x_data, self.y_data)
            self.axis.relim()
            self.axis.autoscale_view(True, True, True)
            # self.canvas.draw()

        if (voltage is not None) and (coinc_rate is not None) and (color is not None):
            if self.color != color:
                # new color, new line
                self.scatter = self.make_scatter(color)
                self.x_scatter = []
                self.y_scatter = []
                self.color = color

            self.x_scatter.append(voltage)
            self.y_scatter.append(coinc_rate)
            self.scatter[0].set_data(self.x_scatter, self.y_scatter)
            self.axis.relim()
            self.axis.autoscale_view(True, True, True)

        return {"state": "graphing", "name": self.__class__.__name__}

        # if self.data.get("graph_data") is not None:
        #     self.axis[0].set_xdata(self.data["graph_data"]["x_data"])
        #     self.axis[0].set_ydata(self.data["graph_data"]["y_data"])

    def make_scatter(self, color):
        scatter = self.axis.plot(
            self.x_scatter,
            self.y_scatter,
            color=color,
            ls="None",
            marker="o",
            markersize=2.5,
            alpha=0.35,
        )
        self.scatters.append(scatter)
        return scatter


class Direction:
    def __init__(self):
        self.direction = 1

    def reverse(self):
        if self.direction == 1:
            self.direction = -1
            print("from 1 to -1")
            logger.info(f"     {self.__class__.__name__}: from 1 to -1")
        else:
            self.direction = 1
            print("from -1 to 1")
            logger.info(f"     {self.__class__.__name__}: from -1 to 1")
        return self.direction

    def random(self):
        self.direction = random.choice([1, -1])
        print("random: ", self.direction)
        logger.info(f"     {self.__class__.__name__}: Random: {self.direction}")
        return self.direction

    def __call__(self):
        return self.direction


class Thing:
    def __init__(self, thing):
        self.thing = thing


if __name__ == "__main__":
    # concurrent = ConcurrentAction(Direction(), ValueIntegrate(30))
    # concurrent.whee()
    # def myfunction(option_1, option_2, **kwargs):
    #     print("option_1: ", option_1)
    #     print("option_2: ", option_2)
    #     print(type(kwargs))
    #     print(len(kwargs))
    #     print(kwargs)
    #     # for thing in kwargs:
    #     #     print("   thing: ", thing)
    #     # for item in kwargs.keys():
    #     #     print("key: ", item, "thing: ", kwargs[item])

    # mything = "how"
    # # print(concurrent)
    # # print(concurrent.__class__())

    # myfunction(3, 56, **{mything: "what"})

    # th = Thing(3)
    # th = 5

    # if type(th) is Thing:
    #     print("thingg")
    # elif type(th) is int:
    #     print("inttt")

    store = Store(voltage=3)
    print(store)
    print(store.voltage)
    store.voltage = 5
    print(store.export())
