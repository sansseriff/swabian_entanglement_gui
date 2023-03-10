from typing import Any


class MeasurementList:
    def __init__(self, combobox):
        self.combobox = combobox
        self.combobox.clear()
        self.measurement_list = []
        self.idx = 0

    def add_measurement(self, action: Any, args: tuple, name: str):
        item = {"action": action, "args": args, "name": name}
        self.measurement_list.append(item)
        self.combobox.insertItem(self.idx, item["name"])
        self.idx += 1

    def load_measurement(self, combobox_index):
        item = self.measurement_list[combobox_index]
        action = item["action"]
        args = item["args"]
        # this initializes the action
        if isinstance(args, tuple):
            return action(*args)
        else:
            return action(args)
