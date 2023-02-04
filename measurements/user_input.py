from .measurement_management import *
from PySide2.QtWidgets import QInputDialog, QAction
from PySide2.QtCore import (
    QObject,
    Signal,
    QTimer,
)
import threading
import yaml
from dataclasses import dataclass
import logging


class TextDialog(QObject):
    sig = Signal(str)

    def get_text(self, main_window, message):
        # this is called by the main_window.show_dialog() method
        main_window.user_message[0], main_window.user_message[1] = QInputDialog.getText(
            None, "User Input", message
        )
        return


class UserInput(Action):
    def __init__(
        self,
        main_window,
        input_label: str = "shg_true_power",
        request_message: str = "input data here",
        output_store: Store = None,
    ):
        super().__init__()
        self.init = True
        self.main_window = main_window
        self.request_message = request_message
        self.input_label = input_label
        self.output_store = output_store

    def evaluate(self, current_time, counts, **kwargs):
        if self.init:
            self.init = False
            # why singleShot: https://stackoverflow.com/questions/56524140/showing-qinputdialog-and-other-gui-objects-from-various-threads
            # why lambda function: https://stackoverflow.com/questions/7489262/singleshot-slot-with-arguments
            QTimer.singleShot(
                0, lambda: self.main_window.show_dialog(self.request_message)
            )

        if self.main_window.user_message[0] is None:
            return {"state": "waiting"}
        else:
            self.final_state = {
                "state": "finished",
                "name": self.__class__.__name__,
                self.input_label: self.main_window.user_message[0],
            }
            if self.output_store is not None:
                self.output_store.set_val(self.main_window.user_message[0])
            print("user message: ", self.main_window.user_message)
            # self.main_window.user_message is either ['number', True] or ['', False] (false when the cancel button is clicked)
            # print(self.final_state)
            self.main_window.user_message = [None, None]
            return self.final_state
