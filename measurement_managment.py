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
                self.pass_state = True  # deactivates this function in this object
                self.final_state = {
                    "state": "finished",
                    "name": self.__class__.__name__,
                    "results": self.flatten(self.results),
                }
                if self.save:
                    self.do_save()
                return self.final_state
            # only if the previous is finished do you recursively call evaluate
            res = self.evaluate(current_time, counts)
            print("EXTRA EVALUATE: ", res)
            return res
        return {"state": "waiting", "results": response}

        # how do I bubble up the results from the scan? In each evaluate?

    def flatten(self, results):
        # to be overridden by child classes
        return results

    def do_save(self):
        with open(self.save_name, "w") as file:
            file.write(json.dumps(self.final_state))

    def enable_save(self, save_name="output_file.json"):
        self.save_name = save_name
        self.save = True

    def __str__(self):
        return "Action Object"

    def pretty_print(self, data):
        print(json.dumps(data, sort_keys=True, indent=4))


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
            return {"state": "integrating"}
        self.counts = self.counts + counts  # add counts

        if (current_time - self.init_time) > self.int_time:
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
                print("Error: injected data is None")
            print("Data for distribution loaded")
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
    ):
        super().__init__()
        self.extremum_type = extremum_type
        # print("is it min?: ", extremum_type == "min")
        # print("is it max?: ", extremum_type == "max")
        if (self.extremum_type != "min") and (self.extremum_type != "max"):
            raise UnspecifiedExtremum(
                f"{str(self.extremum_type)} is not 'max' or 'min'"
            )

        self.change_rate = change_rate
        self.add_action(Wait(wait_time))
        self.add_action(Integrate(integration_time))
        self.vsource = vsource
        # could be overriden by scan data supplied with evaluate
        self.voltage = init_voltage
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

    def evaluate(self, current_time, counts, **kwargs):
        if self.init is False:
            if kwargs.get(self.data_name) is not None:
                print("data loaded with name: ", self.data_name)
                if self.extremum_type == "min":
                    idx_extreme = np.argmin(kwargs[self.data_name]["results"]["viz"])
                if self.extremum_type == "max":
                    idx_extreme = np.argmax(kwargs[self.data_name]["results"]["viz"])

                voltage_min = kwargs[self.data_name]["results"]["voltage"][idx_extreme]
                print("voltage min: ", voltage_min)
                self.voltage = voltage_min  # apply minimum from graph

            print("###### VOLTAGE: ", round(self.voltage, 3))
            self.vsource.setVoltage(self.channel, round(self.voltage, 3))
            self.init = True

        response = self.event_list[self.cycle].evaluate(current_time, counts)

        if response.get("state") == "finished":
            # DON'T CYCLE UNLESS ITS A FINISHED RESPONSE!
            # I need to think of a more foolproof way of doing this

            # What is a good way of ensuring that an action is never skipped in successive evaluations?
            if self.cycle == 1:  # alternate bewteen Wait and integrate
                self.cycle = 0
            else:
                self.cycle = 1

            if response.get("name") == "Integrate":
                self.event_list[1].reset()  # reset the integrate
                self.counts_list.append(response["counts"])
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

                    else:
                        # decreased
                        if self.extremum_type == "min":
                            self.direction_list.append(self.direction())
                            print("no direction change")
                        else:
                            self.direction_list.append(self.direction.reverse())

                delta = self.change_rate * self.direction()
                self.old_voltage = self.voltage
                self.voltage = self.voltage + delta
                print("## VOLTAGE: ", round(self.voltage, 3))
                self.vsource.setVoltage(self.channel, round(self.voltage, 3))
                self.prev_coinc_rate = coinc_rate

                # print(
                #     "list: ",
                #     self.direction_list,
                #     "sum: ",
                #     abs(sum(self.direction_list)),
                # )

                if self.fine_grain_mode and len(self.direction_list) > 8:
                    imbalance = self.direction_list[-8:]
                    if (
                        abs(sum(imbalance)) <= 3 and self.fine_grain_iteration <= 3
                    ):  # no beyond 3
                        self.fine_grain_iteration += 1
                        print(
                            "FINE GRAIN MODE, ITERATION: ",
                            self.fine_grain_iteration,
                        )
                        self.change_rate = 0.5 * self.change_rate
                        # integrate twice as long
                        self.event_list[1].int_time = self.event_list[1].int_time * 4
                        self.fine_grain_status = "activated"
                        last_direction = self.direction_list[-1]
                        self.direction_array.append(self.direction_list)
                        self.direction_list = [last_direction]
                        self.data_color = self.data_color_list[
                            self.fine_grain_iteration - 1
                        ]

                # stop minimization after 2nd fine grain iteration
                if len(self.direction_list) > 7 and self.fine_grain_iteration == 3:
                    # imbalance = self.direction_list[-4:]
                    # # stop if last 20 direction changes seem to be random

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
                        },
                    }
                    if self.save:
                        self.do_save()
                    return self.final_state
                print()
                print()
                return {
                    "state": "working",
                    "name": self.__class__.__name__,
                    "results": {
                        "voltage": self.old_voltage,  # the voltage that was chosen previously and matches the counts from this round. Not the voltage that was chosen this round
                        "coinc_rate": coinc_rate,
                        "color": self.data_color,
                    },
                }
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

            print("inter result: ", self.intermediate_result)

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

        if dic.get("results") is not None:

            return self.results_dive(dic.get("results"), key)
        else:
            # print(dic.get(key))
            # print(dic)
            return dic.get(key)

    def evaluate(self, current_time, counts, **kwargs):
        if self.init is False:
            self.axis.set_yscale("log")
            self.axis.grid()
            self.init = True

        self.data = kwargs
        # off_state = {"state": "not_graphing", "name": self.__class__.__name__}

        graph_data = self.data.get("graph_data")
        # print("results: ", self.results_dive(graph_data, "delta_time"))
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
        print(kwargs)
        # for thing in kwargs:
        #     print("   thing: ", thing)
        # for item in kwargs.keys():
        #     print("key: ", item, "thing: ", kwargs[item])

    mything = "how"
    # print(concurrent)
    # print(concurrent.__class__())

    myfunction(3, 56, **{mything: "what"})
