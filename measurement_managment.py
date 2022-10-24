from multiprocessing import Event
import time
import numpy as np
import json
import random

"""
Actions can contain other actions, 
or actions can be customized to do specific things


!! The issue with using this method is that each action needs a proper return value from .evaluate(). If you forget to put it there, you get errors that are hard to track down...
"""


class Action:
    def __init__(self):
        self.event_list = []
        self.init_time = -1
        self.results = []
        self.pass_state = False
        self.save_name = "output_file.json"
        self.save = False

    def add_action(self, object):
        self.event_list.append(object)

    def evaluate(self, current_time, counts, **kwargs):
        if self.pass_state:
            return {"state": "passed"}
            """remember how I decided an object should be allowed 
            to deactivate itself, but it should not delete itself"""
        response = self.event_list[0].evaluate(current_time, counts)
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
            # only if the previous is finished do you recursively call evaluate
            self.evaluate(current_time, counts)

        return {"state": "waiting", "results": response}

        # how do I bubble up the results from the scan? In each evaluate?

    def do_save(self):
        with open(self.save_name, "w") as file:
            file.write(json.dumps(self.final_state))

    def enable_save(self, save_name="output_file.json"):
        self.save_name = save_name
        self.save = True

    def __str__(self):
        return "Action Object"


class SetVoltage(Action):
    def __init__(self, voltage, vsource, channel):
        super().__init__()
        self.vsource = vsource
        self.voltage = voltage
        self.channel = channel

    def evaluate(self, current_time, counts, **kwargs):
        self.vsource.setVoltage(self.channel, round(self.voltage, 3))
        print("####### setting voltage to", round(self.voltage, 3))
        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "voltage": self.voltage,
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
        if self.init_time == -1:
            self.init_time = time.time()
            # print("####### starting wait")
        if (current_time - self.init_time) > self.wait_time:
            # print("####### finished wait")
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "time_waited": current_time - self.init_time,
            }
            return self.final_state

        return {"state": "waiting"}

    def __str__(self):
        return "Wait Action Object"


class Integrate(Action):
    def __init__(self, int_time):
        super().__init__()
        self.int_time = int_time
        self.counts = 0

    def evaluate(self, current_time, counts, **kwargs):
        if self.init_time == -1:
            self.init_time = time.time()
            # started
            # print("####### starting integrate")

        self.counts = self.counts + counts  # add counts

        if (current_time - self.init_time) > self.int_time:
            # finish up
            # print("####### ending integrate")
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
        return "Integrate Object"


class ValueIntegrate(Action):
    def __init__(self, min_counts):
        super().__init__()
        self.min_counts = min_counts
        self.counts = 0

    def evaluate(self, current_time, counts, **kwargs):
        if self.init_time == -1:
            self.init_time = time.time()
            # started
            print("####### starting integrate")

        self.counts = self.counts + counts  # add counts

        if self.counts > self.min_counts:
            # finish up
            print("####### ending integrate")
            self.delta_time = current_time - self.init_time
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                "counts": self.counts,
                "delta_time": self.delta_time,
            }
            return self.final_state
        return {"state": "integrating"}

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


# class ScanAndMinimize(Action):
#     def __init__(self, scan_params, vsource, change_rate, init_voltage):
#         super().__init__()
#         self.add_action(Scan(scan_params, vsource))
#         self.add_action(Minimize(change_rate, vsource, init_voltage))
class DependentAction(Action):
    def __init__(self):
        super().__init__()

    def evaluate(self, current_time, counts, **kwargs):
        if self.pass_state:
            return {"state": "passed"}
            """remember how I decided an object should be allowed 
            to deactivate itself, but it should not delete itself"""
        response = self.event_list[0].evaluate(current_time, counts)
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
            # take the data and put give it to the next object
            self.evaluate(current_time, counts, prev_data=response)

        # this intermediate return can be passed to a graph by ConcurrentAction
        return {"state": "waiting", "results": response}


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


class Minimize(Action):
    def __init__(self, change_rate, vsource, init_voltage):
        super().__init__()
        self.change_rate = change_rate
        self.add_action(Integrate(40))  # 2 seconds
        self.vsource = vsource
        self.init_voltage = init_voltage
        self.direction = Direction()
        self.voltage = init_voltage
        self.channel = 2
        self.prev_coinc_rate = -1
        self.init = False

    def evaluate(self, current_time, counts, **kwargs):
        if self.init is False:
            if kwargs.get("prev_data") is not None:
                print("previous data dump: ")
                print(kwargs["prev_data"])
            print("########################### VOLTAGE: ", round(self.voltage, 3))
            self.vsource.setVoltage(self.channel, round(self.voltage, 3))
            self.init = True

        response = self.event_list[0].evaluate(current_time, counts)
        # print("response: ", response["state"])
        if response["state"] == "finished":
            self.event_list[0].reset()
            coinc_rate = response["counts"] / response["delta_time"]
            print("########################### coinc rate: ", coinc_rate)

            if (coinc_rate == self.prev_coinc_rate) or (self.prev_coinc_rate == -1):
                self.direction.random()
            else:
                # if coinc_rate < self.prev_coinc_rate:
                # don't change direction

                # if coinc_rate is less than previous, there's nothing
                # to do. Keep going in that direction.
                if coinc_rate > self.prev_coinc_rate:
                    self.direction.reverse()
                else:
                    print("no direction change")

            delta = self.change_rate * self.direction()
            self.voltage = self.voltage + delta
            print("########################### VOLTAGE: ", round(self.voltage, 3))
            self.vsource.setVoltage(self.channel, round(self.voltage, 3))

            self.prev_coinc_rate = coinc_rate

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
            self.intermediate_result = object.evaluate(
                current_time, counts, intermediate=self.intermediate_result
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


# class PlottableObject():
#     def __init__():

# every time we get enough information for a new datapoint... Is every time we finihes one iteration of... the scan object.


class GraphUpdate(Action):
    def __init__(self, axis):
        self.axis = axis
        self.data = None
        self.pass_state = False
        self.x_data = []
        self.y_data = []

    def evaluate(self, current_time, counts, **kwargs):
        self.data = kwargs

        # if len(self.data) > 0:
        #     print("##### Sarting: from graph #####")
        #     print(self.data)
        #     print("##### Ending: from graph #####")

        return {"state": "graphing", "name": self.__class__.__name__}

        # if self.data.get("graph_data") is not None:
        #     self.axis[0].set_xdata(self.data["graph_data"]["x_data"])
        #     self.axis[0].set_ydata(self.data["graph_data"]["y_data"])


class Direction:
    def __init__(self):
        self.direction = 1

    def reverse(self):
        if self.direction == 1:
            self.direction = -1
            print("from 1 to -1")
        else:
            self.direction = 1
            print("from -1 to 1")
        return self.direction

    def random(self):
        self.direction = random.choice([1, -1])
        print("random: ", self.direction)
        return self.direction

    def __call__(self):
        return self.direction


if __name__ == "__main__":
    # concurrent = ConcurrentAction(Direction(), ValueIntegrate(30))
    # concurrent.whee()
    def myfunction(option_1, option_2, **kwargs):
        print("option_1: ", option_1)
        print("option_2: ", option_2)
        print(type(kwargs))
        print(len(kwargs))
        # for thing in kwargs:
        #     print("   thing: ", thing)
        # for item in kwargs.keys():
        #     print("key: ", item, "thing: ", kwargs[item])

    # print(concurrent)
    # print(concurrent.__class__())

    myfunction(3, 56)
