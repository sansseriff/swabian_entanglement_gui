from .user_input import UserInput
from .measurement_management import *


class CombineStringStores(Action):
    def __init__(
        self,
        input_store_1: Store,
        input_store_2: Store,
        output_store: Store,
        prepend="./jsi_scan/",
        append=".json",
    ):
        super().__init__()
        self.input_store_1 = input_store_1
        self.input_store_2 = input_store_2
        self.output_store = output_store
        self.prepend = prepend
        self.append = append

    def evaluate(self, current_time, counts, **kwargs):
        string_1 = self.input_store_1.get_val()
        string_2 = self.input_store_2.get_val()
        new_name = self.prepend + string_1 + "_" + string_2 + self.append
        self.output_store.set_val(new_name)

        # this is a bad practice! If this method does not have a return value with the key "finished",
        # then it breaks and it's hard to debug!!
        self.final_state = {
            "state": "finished",
            "name": self.__class__.__name__,
            "new store": new_name,
        }
        return self.final_state


class FastMinimum(Action):
    def __init__(self, main_window, voltage_source, start_voltage_store):
        super().__init__()

        name_1 = Store(name="channel 1")
        name_2 = Store(name="channel 2")
        combined_names = Store(name="channel 1 and 2")
        self.add_action(
            UserInput(
                main_window,
                input_label="Channel Request",
                request_message=f"Input Channel 1",
                output_store=name_1,
            )
        )
        self.add_action(Wait(0.2))  # for avoiding double evaluation of the user inputs
        self.add_action(
            UserInput(
                main_window,
                input_label="Channel Request",
                request_message=f"Input Channel 2",
                output_store=name_2,
            )
        )
        self.add_action(SetVoltage(start_voltage_store, voltage_source, 2))
        self.add_action(Wait(2.5))
        fast_min = Extremum(
            "min",
            0.02,  # integration
            0.3,  # wait
            0.4,  # change_rate
            voltage_source,
            start_voltage_store,
            fine_grain_mode=True,
            low_res_steps=0,
            steps=7,
        )
        fast_min.update_start_iteration(3)  # change rate is now 0.4*(0.5^3) = 0.05
        self.add_action(fast_min)
        self.add_action(SetPower(4.0, voltage_source, 1))
        self.add_action(Wait(3))
        self.add_action(Integrate(2))
        self.add_action(SetPower(1.2, voltage_source, 1))
        self.add_action(Wait(3))
        self.add_action(Integrate(2))
        self.add_action(
            CombineStringStores(
                name_1,
                name_2,
                combined_names,
                prepend="./jsi_scan/4.0A_",
                append=".json",
            )
        )
        self.add_action(
            SetVoltage(1.6, voltage_source, 2)
        )  # maximize so you can zoom_to_peak in the next run
        self.add_action(SetPower(1.7, voltage_source, 1))
        self.enable_save(combined_names)
