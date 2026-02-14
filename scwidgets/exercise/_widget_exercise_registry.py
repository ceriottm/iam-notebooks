# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

import glob
import json
import os
from collections import OrderedDict
from typing import Hashable, Optional, Union

from IPython.display import display
from ipywidgets import Button, Dropdown, HBox, Label, Layout, Output, Text, VBox

from .._utils import Formatter
from ..css_style import CssStyle


class ExerciseWidget:
    """
    Any widget inheriting from this class can be (de)serialized
    by :py:class:`WidgetStateRegistry`. The serialization offered by `ipywidgets`
    cannot be loaded out-of-the-box for a restarted notebook since the widget IDs change

    :param exercise_registry:
        the exercise registry that registers the answers for this widget

    :param exercise_key:
        Identifier for the widget, must be unique for each registered widget

    Reference
    ---------
    https://ipywidgets.readthedocs.io/en/7.x/examples/Widget%20Low%20Level.html
    https://github.com/jupyter-widgets/ipywidgets/issues/2369
    """

    def __init__(
        self,
        exercise_registry: Union[None, ExerciseRegistry],
        exercise_key: Union[None, Hashable],
    ):
        if exercise_registry is not None and exercise_key is None:
            raise ValueError(
                "exercise registry was given but no exercise key was given"
            )
        elif exercise_registry is None and exercise_key is not None:
            raise ValueError(
                "exercise key was given but no exercise registry was given"
            )
        # we need to use a key because self is not persistent on kernel restarts
        self._exercise_registry = exercise_registry
        self._exercise_key = exercise_key

        if self._exercise_registry is not None and exercise_key is not None:
            self._exercise_registry.register_widget(self, self._exercise_key)

    @property
    def answer(self) -> dict:
        """
        Translates the widget state into a string
        """
        raise NotImplementedError("answer has not been implemented")

    @answer.setter
    def answer(self, answer: dict):
        """
        Sets the answer from a given string
        """
        raise NotImplementedError("answer has not been implemented")

    def handle_save_result(self, result: Union[str, Exception]) -> None:
        """
        Function that controls how a save result is handled. If the result is a string,
        the saving was successful. The result contains a string that can be outputed.
        """
        raise NotImplementedError("handle_save_result has not been implemented")

    def handle_load_result(self, result: Union[str, Exception]) -> None:
        """
        Function that controls how a load result is handled. If the result is a string,
        the loading was successful. The result contains a string that can be outputed.
        """
        raise NotImplementedError("handle_load_result has not been implemented")

    def save(self) -> Union[str, Exception]:
        if self._exercise_registry is None:
            raise ValueError(
                "No exercise registry given on initialization, save cannot be used"
            )
        if self._exercise_key is None:
            raise ValueError(
                "No exercise key given on initialization, save cannot be used"
            )
        return self._exercise_registry.save_answer(self._exercise_key)

    def load(self) -> Union[str, Exception]:
        if self._exercise_registry is None:
            raise ValueError(
                "No exercise registry given on initialization, load cannot be used"
            )
        if self._exercise_key is None:
            raise ValueError(
                "No exercise key given on initialization, load cannot be used"
            )
        return self._exercise_registry.load_answer_from_loaded_file(self._exercise_key)

    @property
    def exercise_registry(self):
        return self._exercise_registry

    @property
    def exercise_key(self):
        return self._exercise_key


class FilenameParser:
    @staticmethod
    def is_valid_filename(prefix, filename):
        return (
            (
                prefix is not None
                and filename.startswith(prefix + "-")
                or (prefix is None)
            )
        ) and (filename.endswith("json"))

    @staticmethod
    def standardize_filename(filename: str) -> str:
        return filename.lower().replace(" ", "_")

    @property
    def filename_prefix(self):
        return self._filename_prefix

    @staticmethod
    def is_name_empty(name):
        return len(name) == name.count(" ")

    @staticmethod
    def extract_forbidden_characters(name):
        character_list = []
        forbidden_characters = "./\\"
        for character in forbidden_characters:
            if character in name:
                character_list += character
        return character_list

    @staticmethod
    def verify_valid_student_name(student_name: str):
        if FilenameParser.is_name_empty(student_name):
            raise ValueError("Your name is empty. Please provide one.")

        forbidden_characters = FilenameParser.extract_forbidden_characters(student_name)
        if len(forbidden_characters) > 0:
            return ValueError(
                f"The name '{student_name}' contains invalid special "
                f"characters {forbidden_characters}. Please provide another name."
            )


class ExerciseRegistry(VBox):
    """ """

    def __init__(self, filename_prefix: Optional[str] = None, *args, **kwargs):
        self._filename_prefix = filename_prefix
        self._widgets: OrderedDict = OrderedDict()
        self._loaded_file_name: Union[str, None] = None

        # upper panel box
        dropdown_options = self._get_dropdown_options()
        self._choose_label = Label("Choose:")
        self._answers_files_dropdown = Dropdown(options=dropdown_options)
        # button to confirm selected filename from dropdown list
        self._load_file_button = Button(description="Load file")
        # box to create new answer file
        self._student_name_text = Text(
            placeholder="Enter your name here", style={"description_width": "initial"}
        )
        self._confirm_create_new_file_button = Button(description="Create file")
        # if a valid file has been found the dropdown options is > 1
        # the one default option is to create new file
        if len(self._answers_files_dropdown.options) > 1:
            self._upper_panel_box = HBox(
                [
                    self._choose_label,
                    self._answers_files_dropdown,
                    self._load_file_button,
                ]
            )
        else:
            self._upper_panel_box = HBox(
                [
                    self._choose_label,
                    self._answers_files_dropdown,
                    self._student_name_text,
                    self._confirm_create_new_file_button,
                ]
            )

        # lower panel box
        self._choose_other_file_button = Button(
            description="Choose other file",
            disabled=True,
            tooltip="Unloads the current file so you can load or " "create a new file.",
        )
        self._save_all_answers_button = Button(
            description="Save all answers",
            disabled=True,
            tooltip="Save all answers saved into a .json file.",
        )
        self._lower_panel_box = HBox(
            [
                self._choose_other_file_button,
                self._save_all_answers_button,
            ]
        )
        # lower panel appears when file has been loaded and is there display within an
        # output that can be cleared
        self._lower_panel_output = Output()

        # output for user messages
        self._output = Output()
        kwargs["layout"] = kwargs.pop("layout", Layout(width="100%"))
        VBox.__init__(
            self,
            [
                CssStyle(),
                self._upper_panel_box,
                self._lower_panel_output,
                self._output,
            ],
            *args,
            **kwargs,
        )

        # confirmation box
        self._confirm_save_button = Button(description="Yes", tooltip="Confirm")
        self._cancel_save_button = Button(description="Cancel", tooltip="Cancel")
        self._confirmation_button_box = HBox(
            [self._confirm_save_button, self._cancel_save_button]
        )

        # upper panel box events
        self._confirm_create_new_file_button.on_click(
            self._on_click_confirm_create_new_file_button
        )
        self._load_file_button.on_click(self._on_click_load_file_button)
        self._answers_files_dropdown.observe(
            self._on_answers_files_dropdown_value_changed, names="value"
        )

        # lower panel box events
        self._choose_other_file_button.on_click(self._on_click_choose_other_file_button)
        self._save_all_answers_button.on_click(self._on_click_save_all_answers_button)

        # confirmation box events
        self._confirm_save_button.on_click(self._on_click_confirm_save_button)
        self._cancel_save_button.on_click(self._on_click_cancel_save_button)

    @property
    def filename_prefix(self):
        return self._filename_prefix

    @filename_prefix.setter
    def filename_prefix(self, filename_prefix: str):
        self._filename_prefix = filename_prefix
        dropdown_options = self._get_dropdown_options()
        self._answers_files_dropdown.options = dropdown_options

    @property
    def registered_widgets(self):
        return self._widgets.copy()

    @property
    def loaded_file_name(self) -> Union[str, None]:
        return self._loaded_file_name

    def register_widget(self, widget: ExerciseWidget, exercise_key: Hashable):
        """
        :param widget:
            widget answer that is saved on click of the save button
        :param exercise_key:
            unique exercise key for the widget to be stored under,
            so it can be reloaded persistently after a restart of the python kernel
        """
        self._widgets[exercise_key] = widget

    def create_new_file_from_dropdown(self) -> str:
        """Creates a new file containing all students answers from the selected
        file in the dropdown menu.

        :raises FileExistsError: If the file already exists
        :return: The success message
        """
        self.create_new_file_from_student_name(self._student_name_text.value)
        return f"File {self._loaded_file_name!r} created and loaded."

    def get_answer_filename(self, student_name: str) -> str:
        """Returns the filename containing all answers for the student name.

        :param student_name: The name of the student used in the filename
        :raises ValueError: If the student name is not valid
        :return: The filename
        """
        FilenameParser.verify_valid_student_name(student_name)

        answers_filename = ""
        # if prefix is defined, it is added to the filename
        if self._filename_prefix is not None:
            answers_filename += self._filename_prefix + "-"
        student_name_standardized = FilenameParser.standardize_filename(student_name)
        answers_filename += student_name_standardized + ".json"
        return answers_filename

    def create_new_file_from_student_name(self, student_name: str):
        """Creates a new exercise file containing all the student's answers.

        :param student_name: The name of the student used for the exercise file
        :raises FileExistsError: If the file already exists
        :return: A message to print
        """
        answers_filename = self.get_answer_filename(student_name)

        if os.path.exists(answers_filename):
            raise FileExistsError(
                f"The name is already used for file {answers_filename!r}."
                " Please provide a new name."
            )
        else:
            answers = {key: widget.answer for key, widget in self._widgets.items()}
            with open(answers_filename, "w") as answers_file:
                json.dump(answers, answers_file)

            new_dropdown_options = list(self._answers_files_dropdown.options)
            new_dropdown_options.insert(-1, answers_filename)
            self._answers_files_dropdown.options = new_dropdown_options
            self._answers_files_dropdown.value = answers_filename

            self._disable_upper_panel_box()
            self._enable_lower_panel_box()
            self._show_lower_panel_box()

            self._loaded_file_name = answers_filename

    def load_answer_from_student_name(
        self, student_name: str, exercise_key: Union[Hashable, ExerciseWidget]
    ):
        """
        Loads the answer with key `exercise_key` from the file corresponding to
        `student_name`.

        :raises KeyError: Corresponding widget to `exercise_key` cannot be found
        :raises KeyError: Corresponding key in file cannot be found
        :raises FileNotFoundError: If the file cannot be found
        :param student_name: The name of the student
        :param exercise_key: Unique exercise key for widget to store, so it can
            be reloaded persistently after a restart of the python kernel
        """
        self.load_answer(self.get_answer_filename(student_name), exercise_key)

    def load_answer_from_loaded_file(
        self, exercise_key: Union[Hashable, ExerciseWidget]
    ) -> str:
        """
        Loads the answer with key `exercise_key` from the currently loaded file.

        :raises ValueError: No file has been loaded
        :raises KeyError: Corresponding widget to `exercise_key` cannot be found
        :raises KeyError: Corresponding key in file cannot be found
        :raises FileNotFoundError: If the file cannot be found
        :param exercise_key: Unique exercise key for widget to store, so it can
            be reloaded persistently after a restart of the python kernel
        """
        if self._loaded_file_name is None:
            raise ValueError("No file has been loaded.")

        self.load_answer(self._loaded_file_name, exercise_key)
        return f"Exercise has been loaded from file {self._loaded_file_name!r}."

    def load_answer(
        self, answers_filename: str, exercise_key: Union[Hashable, ExerciseWidget]
    ):
        """
        Loads the answer with key `exercise_key` from the `answer_filename`.

        :raises KeyError: Corresponding widget to `exercise_key` cannot be found
        :raises KeyError: Corresponding key in file cannot be found
        :raises FileNotFoundError: If the file cannot be found
        :param answers_filename: The file with the answer
        :param exercise_key: Unique exercise key for widget to store, so it can
            be reloaded persistently after a restart of the python kernel
        """
        if isinstance(exercise_key, ExerciseWidget):
            exercise_key = exercise_key.exercise_key

        if exercise_key not in self._widgets.keys():
            raise KeyError(
                f"There is no widget registered with exercise key {exercise_key!r}."
            )

        if not (os.path.exists(answers_filename)):
            raise FileNotFoundError(
                f"The file {answers_filename!r} does not exist. Maybe you have renamed "
                "or deleted it? Please choose another file or create a new one."
            )

        answers_filename = self._answers_files_dropdown.value
        with open(answers_filename, "r") as answers_file:
            answers = json.load(answers_file)
        if exercise_key not in answers.keys():
            raise KeyError(
                "Your file does not contain the answer with exercise key "
                f"{exercise_key!r}."
            )
        else:
            self._widgets[exercise_key].answer = answers[exercise_key]
        self._loaded_file_name = answers_filename

    def load_file_from_dropdown(self) -> str:
        """
        Loads all answers from the selected file in the dropdown menu.
        """
        if (
            self._answers_files_dropdown.value
            == self._create_new_file_dropdown_option()
        ):
            raise ValueError("No file has been selected in the dropdown list.")
        if self._loaded_file_name is None:
            answers_filename = self._answers_files_dropdown.value
        else:
            answers_filename = self._loaded_file_name

        self.load_file(answers_filename)
        return f"All answers loaded from file {self._loaded_file_name!r}."

    def load_file_from_student_name(self, student_name: str):
        self.load_file(self.get_answer_filename(student_name))

    def load_file(self, answers_filename: str):
        """
        Loads all answers from the selected file in the dropdown menu.

        :raises FileNotFoundError: If the file cannot be found
        :raises ValueError: If the loaded file contains an answer with key that
            has not been registered
        """

        if not (os.path.exists(answers_filename)):
            raise FileNotFoundError(
                f"The file {answers_filename!r} does not exist. Maybe you have renamed "
                "or deleted it? Please choose another file or create a new one."
            )

        with open(answers_filename, "r") as answers_file:
            answers = json.load(answers_file)
        for exercise_key, answer in answers.items():
            if exercise_key not in self._widgets.keys():
                raise ValueError(
                    f"Your file contains an answer with key {exercise_key!r} "
                    f"with no corresponding registered widget."
                )
            else:
                self._widgets[exercise_key].answer = answer
        self._loaded_file_name = answers_filename

        # only notify all widgets when result was successful
        for widget in self._widgets.values():
            result = f"Exercise has been loaded from file {self._loaded_file_name!r}."
            widget.handle_load_result(result)

        self._answers_files_dropdown.value = answers_filename
        self._disable_upper_panel_box()
        self._enable_lower_panel_box()
        self._show_lower_panel_box()

    def save_answer(self, exercise_key: Hashable) -> str:
        if not (exercise_key in self._widgets.keys()):
            raise KeyError(
                f"There is no widget registered with exercise key {exercise_key!r}."
            )

        if self._loaded_file_name is None:
            # outputs error at the widget where the save button is attached to
            raise FileNotFoundError(
                "No file has been loaded. Please first load/create a file."
            )
        elif not (os.path.exists(self._loaded_file_name)):
            raise FileNotFoundError(
                "Loaded file does not exist anymore. Maybe you have renamed "
                "or deleted it? Please choose another file or create a new one."
            )
        else:
            with open(self._loaded_file_name, "r") as answers_file:
                answers = json.load(answers_file)
            answers[exercise_key] = self._widgets[exercise_key].answer

            with open(self._loaded_file_name, "w") as answers_file:
                json.dump(answers, answers_file)
            result = f"Exercise has been saved in file {self._loaded_file_name!r}."
        return result

    def save_all_answers(self) -> str:
        """
        Saves all answers to the loaded JSON file.
        Returns a success message or raises an error when failed
        """
        if self._loaded_file_name is None:
            raise FileNotFoundError(
                "No file has been loaded. Please first load/create a file."
            )
        elif not (os.path.exists(self._loaded_file_name)):
            raise FileNotFoundError(
                "Loaded file does not exist anymore. Maybe you have renamed "
                "or deleted it? Please choose another file or create a new one."
            )
        else:
            with open(self._loaded_file_name, "r") as answers_file:
                answers = json.load(answers_file)
            for exercise_key, widget in self._widgets.items():
                answers[exercise_key] = widget.answer

            with open(self._loaded_file_name, "w") as answers_file:
                json.dump(answers, answers_file)

            # only notifiy all widgets when result was successful
            for widget in self._widgets.values():
                result = f"Exercise has been saved in file {self._loaded_file_name!r}."
                widget.handle_save_result(result)

            return f"All answers were saved in file {self._loaded_file_name!r}."

    ######################
    # on event functions #
    ######################

    def _on_click_confirm_save_button(self, change: dict):
        self._output.clear_output(wait=True)
        with self._output:
            try:
                message = self.save_all_answers()
                print(Formatter.color_success_message(message))
            except Exception as exception:
                print(Formatter.color_error_message("Error raised while saving file:"))
                raise exception

    def _on_click_choose_other_file_button(self, change: dict):
        self._output.clear_output()
        with self._output:
            dropdown_options = self._get_dropdown_options()
            self._answers_files_dropdown.options = dropdown_options
            self._enable_upper_panel_box()
            self._clear_lower_panel_box()
            self._disable_lower_panel_box()
            self._loaded_file_name = None

    def _on_click_load_file_button(self, change: dict):
        self._output.clear_output(wait=True)
        with self._output:
            try:
                result = self.load_file_from_dropdown()
                print(Formatter.color_success_message(result))
            except Exception as exception:
                print(Formatter.color_error_message("Error raised while loading file:"))
                raise exception

    def _on_answers_files_dropdown_value_changed(self, change: dict):
        if change["new"] == self._create_new_file_dropdown_option():
            self._upper_panel_box.children = [
                self._choose_label,
                self._answers_files_dropdown,
                self._student_name_text,
                self._confirm_create_new_file_button,
            ]
        else:
            self._upper_panel_box.children = [
                self._choose_label,
                self._answers_files_dropdown,
                self._load_file_button,
            ]

    def _on_click_confirm_create_new_file_button(self, change: dict):
        self._output.clear_output(wait=True)
        with self._output:
            try:
                result = self.create_new_file_from_dropdown()
                print(Formatter.color_success_message(result))
            except Exception as exception:
                print(
                    Formatter.color_error_message("Error raised while creating file:")
                )
                raise exception

    def _on_click_cancel_save_button(self, change: dict):
        self._output.clear_output()

    def _on_click_save_all_answers_button(self, change: dict):
        self._output.clear_output(wait=True)
        with self._output:
            display(self._confirmation_button_box)
            print(Formatter.color_info_message("Are you sure?"))

    #####################
    # private functions #
    #####################

    def _get_dropdown_options(self):
        # current work directory valid file names
        dropdown_options = [
            filename
            for filename in map(os.path.basename, glob.glob(os.getcwd() + "/*.json"))
            if FilenameParser.is_valid_filename(self.filename_prefix, filename)
        ]
        dropdown_options.sort()
        dropdown_options.append(self._create_new_file_dropdown_option())
        return dropdown_options

    def _create_new_file_dropdown_option(self):
        return "--- Create new answer file ---"

    def _disable_upper_panel_box(self):
        self._choose_label.style.text_color = "gray"
        self._answers_files_dropdown.disabled = True
        self._student_name_text.disabled = True
        self._confirm_create_new_file_button.disabled = True
        self._load_file_button.disabled = True

    def _enable_upper_panel_box(self):
        self._choose_label.style.text_color = "black"
        self._answers_files_dropdown.disabled = False
        self._student_name_text.disabled = False
        self._confirm_create_new_file_button.disabled = False
        self._load_file_button.disabled = False

    def _disable_lower_panel_box(self):
        for widget in self._lower_panel_box.children:
            widget.disabled = True

    def _enable_lower_panel_box(self):
        for widget in self._lower_panel_box.children:
            widget.disabled = False

    def _show_lower_panel_box(self):
        with self._lower_panel_output:
            display(self._lower_panel_box)

    def _clear_lower_panel_box(self):
        self._lower_panel_output.clear_output()
