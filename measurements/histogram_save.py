from .user_input import UserInput
from .measurement_management import *



class SaveHistogram(Action):
    def __init__(self, main_window):
        super().__init__()

        hist_file_name = Store(name="replace_with_file_name") # updated later
        int_time = Store(time=1, auto_convert=True)
        self.add_action(
            UserInput(
                main_window,
                input_label="hist_file_name",
                request_message=f"Input Histogram File Name",
                output_store=hist_file_name,
            )
        )
        self.add_action(
            UserInput(
                main_window,
                input_label="integration_time",
                request_message=f"Input Integration Time",
                output_store=int_time,
            )
        )
        self.add_action(Integrate(int_time, continuous=False, include_histograms=True))
        self.enable_save(save_name = hist_file_name)

