from .measurement_management import *
from .user_input import UserInput


class ContinuousIntegrate(Action):
    def __init__(self, main_window, **kwargs):
        super().__init__(**kwargs)
        int_time = Store(time=1, auto_convert=True)
        self.add_action(
            UserInput(
                main_window=main_window,
                input_label="integration time",
                request_message="set interation time (s)",
                output_store=int_time,
            )
        )
        integrator = Integrate(int_time, continuous=True)
        self.add_action(integrator)

    def evaluate(self, current_time, counts, **kwargs):
        logger.debug(f"Evaluating Action: {self.n}")
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
                print("aborting ", self.n)
                return {"state": "abort", "name": self.n}

            if response["state"] == "finished_continuous":
                responses.pop(-1)
                break

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
                        "name": self.n,
                        "label": self.label,
                        "results": self.flatten(self.results),
                    }
                    if self.save:
                        self.do_save()
                    return self.final_state
        return {"state": "waiting", "results": responses}
