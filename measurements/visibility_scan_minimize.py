from .measurement_management import (
    Action,
    DependentAction,
    DistributeData,
    Extremum,
    SetVoltage,
    Wait,
    ConcurrentAction,
    GraphUpdate,
    Scan,
)
import yaml


class VisibilityScanMinimize(Action):
    def __init__(self, voltage_source, graph_axis):
        super().__init__()

        with open(
            "./measurements/visibility_scan_minimize.yaml", "r", encoding="utf8"
        ) as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        params = params["visibility"]

        """add a series of actions that will be done during the program's
        main event loop. (this is a way of avoiding a series of messy
        if statements that determine what to do at what time
        in the event loop) """

        # +-Concurrent----------+
        # | +-Action-+ +------+ |
        # | |+------+| |      | |
        # | || Scan || |      | |
        # | ||      || |      | |
        # | |+------+| |graph | |
        # | |+------+| |      | |
        # | || Mini || |      | |
        # | || Maxi || |      | |
        # | |+------+| |      | |
        # | +--------+ +------+ |
        # +---------------------+
        scan_and_find_extremes = DependentAction("coarse_scan")
        scan_and_find_extremes.add_action(Scan(params["int_fast"], voltage_source))
        minimum_and_maximum = DistributeData("coarse_scan")

        minimum = Extremum(
            "min", 1, 1, 0.05, voltage_source, 0, "coarse_scan", fine_grain_mode=True
        )
        minimum.enable_save(save_name="minimum_data.json")
        minimum_and_maximum.add_action(minimum)
        maximum = Extremum(
            "max", 0.25, 4, 0.2, voltage_source, 0, "coarse_scan", fine_grain_mode=True
        )
        maximum.enable_save(save_name="maximum_data.json")
        minimum_and_maximum.add_action(maximum)

        scan_and_find_extremes.add_action(minimum_and_maximum)

        # how do you tell Minimize where to find the curve with the max and the min values? It doesn't exist yet...
        # if these are not finished, I want the result to bubble up to the the graph object.
        # if they are finished, I want them to export data to either the next object or the graph object.

        # these two are to get the interferometer stable before the coarse scan
        self.add_action(SetVoltage(0, voltage_source, 2))
        self.add_action(Wait(10))

        self.add_action(
            ConcurrentAction(scan_and_find_extremes, GraphUpdate(graph_axis))
        )
        self.enable_save(save_name=params["save_name"])


# tracker = Action()
# self.event_loop_action = tracker
