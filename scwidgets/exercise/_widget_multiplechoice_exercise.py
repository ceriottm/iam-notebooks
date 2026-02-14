import random
from typing import Any, Dict, List, Optional, Union

from ipywidgets import (
    HTML,
    HBox,
    HTMLMath,
    Layout,
    Output,
    RadioButtons,
    SelectMultiple,
    VBox,
)

from .._utils import Formatter
from ..css_style import CssStyle
from ..cue import SaveCueBox, SaveResetCueButton
from ._widget_exercise_registry import ExerciseRegistry, ExerciseWidget


class MultipleChoiceExercise(VBox, ExerciseWidget):
    """
    :param options:
        Either a dict or a list. If a dict is provided, the widget will display the
        dictionary’s value but save its key to the registry.

    :param key:
        Unique key for the exercise.

    :param description:
        A string describing the exercise that will be put into an HTML widget above
        the exercise.

    :param title:
        A title for the exercise. If not provided, the key is used.

    :param exercise_registry:
        An exercise registry that is used to register the answers to save them later.
        If specified the save and load panel will appear.

    :param allow_multiple:
        Whether multiple selections are allowed.

    :param randomize_order:
        Whether to randomize order of options.
    """

    def __init__(
        self,
        options: Union[List[Any], Dict[Any, Any]],
        key: Optional[str] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        exercise_registry: Optional[ExerciseRegistry] = None,
        allow_multiple: bool = False,
        randomize_order: bool = False,
        *args,
        **kwargs,
    ):
        self._description = description
        if description is not None:
            self._description_html = HTMLMath(self._description)
            self._description_html.add_class("exercise-description")
        else:
            self._description_html = None

        self._title: Union[str, None]
        if title is None:
            if key is not None:
                self._title = key
                self._title_html = HTML(f"<b>{key}</b>")
            else:
                self._title = None
                self._title_html = None
        else:
            self._title = title
            self._title_html = HTML(f"<b>{title}</b>")
        if self._title_html is not None:
            self._title_html.add_class("exercise-title")

        self._options_dict: Union[dict, None]
        if isinstance(options, dict):
            self._options_dict = options
            options_list = [(value, key) for key, value in options.items()]
        elif isinstance(options, list):
            self._options_dict = None
            options_list = options
        else:
            raise ValueError("Options must be provided as a dict or a list.")

        if randomize_order:
            random.shuffle(options_list)

        self._options_list = options_list
        self.allow_multiple = allow_multiple

        if allow_multiple:
            self._selection_widget = SelectMultiple(
                options=options_list,
                description="",
                layout=Layout(width="auto"),
            )
        else:
            self._selection_widget = RadioButtons(
                options=options_list,
                description="",
                layout=Layout(width="auto"),
            )

        if exercise_registry is None:
            self._cue_selection = self._selection_widget
            self._save_button = None
            self._load_button = None
            self._button_panel = None
        else:
            self._cue_selection = SaveCueBox(
                self._selection_widget, "value", self._selection_widget, cued=True
            )
            self._save_button = SaveResetCueButton(
                self._cue_selection,
                self._on_click_save_action,
                disable_on_successful_action=kwargs.pop(
                    "disable_save_button_on_successful_action", False
                ),
                disable_during_action=kwargs.pop(
                    "disable_save_button_during_action", True
                ),
                description="Save answer",
                button_tooltip="Saves answer to the loaded file",
            )
            self._load_button = SaveResetCueButton(
                self._cue_selection,
                self._on_click_load_action,
                disable_on_successful_action=kwargs.pop(
                    "disable_load_button_on_successful_action", False
                ),
                disable_during_action=kwargs.pop(
                    "disable_load_button_during_action", True
                ),
                description="Load answer",
                button_tooltip="Loads answer from the loaded file",
            )
            self._save_button.set_cue_widgets([self._cue_selection, self._load_button])
            self._load_button.set_cue_widgets([self._cue_selection, self._save_button])
            self._button_panel = HBox(
                [self._save_button, self._load_button],
                layout=Layout(justify_content="flex-end"),
            )

        self._output = Output()

        if exercise_registry is not None:
            ExerciseWidget.__init__(self, exercise_registry, key)
        else:
            # otherwise ExerciseWidget constructor will raise an error
            ExerciseWidget.__init__(self, None, None)

        widget_children = [CssStyle()]
        if self._title_html is not None:
            widget_children.append(self._title_html)
        if self._description_html is not None:
            widget_children.append(self._description_html)
        widget_children.append(self._cue_selection)
        if self._button_panel is not None:
            widget_children.append(self._button_panel)
        widget_children.append(self._output)

        VBox.__init__(self, widget_children, *args, **kwargs)

    @property
    def title(self) -> Union[str, None]:
        return self._title

    @property
    def description(self) -> Union[str, None]:
        return self._description

    @property
    def answer(self) -> dict:
        return {"selection": self._selection_widget.value}

    @answer.setter
    def answer(self, answer) -> None:
        if hasattr(self._cue_selection, "unobserve_widgets"):
            self._cue_selection.unobserve_widgets()
        if self._save_button is not None:
            self._save_button.unobserve_widgets()
        if self._load_button is not None:
            self._load_button.unobserve_widgets()

        self._selection_widget.value = answer["selection"]

        if hasattr(self._cue_selection, "observe_widgets"):
            self._cue_selection.observe_widgets()
        if self._save_button is not None:
            self._save_button.observe_widgets()
        if self._load_button is not None:
            self._load_button.observe_widgets()

    def _on_click_save_action(self) -> bool:
        self._output.clear_output(wait=True)
        raised_error = False
        with self._output:
            try:
                result = self.save()
                if isinstance(result, str):
                    print(Formatter.color_success_message(result))
                elif isinstance(result, Exception):
                    raise result
                else:
                    print(result)
            except Exception as e:
                print(Formatter.color_error_message("Error raised while saving file:"))
                raised_error = True
                raise e
        return not raised_error

    def _on_click_load_action(self) -> bool:
        self._output.clear_output(wait=True)
        raised_error = False
        with self._output:
            try:
                result = self.load()
                if isinstance(result, str):
                    print(Formatter.color_success_message(result))
                elif isinstance(result, Exception):
                    raise result
                else:
                    print(result)
                return True
            except Exception as e:
                print(Formatter.color_error_message("Error raised while loading file:"))
                raised_error = True
                raise e
        return not raised_error

    def handle_save_result(self, result: Union[str, Exception]) -> None:
        self._output.clear_output(wait=True)
        with self._output:
            if isinstance(result, Exception):
                print(Formatter.color_error_message("Error raised while saving file:"))
                raise result
            else:
                if self._load_button is not None:
                    self._load_button.cued = False
                if self._save_button is not None:
                    self._save_button.cued = False
                print(Formatter.color_success_message(result))

    def handle_load_result(self, result: Union[str, Exception]) -> None:
        self._output.clear_output(wait=True)
        with self._output:
            if isinstance(result, Exception):
                print(Formatter.color_error_message("Error raised while loading file:"))
                raise result
            else:
                if self._load_button is not None:
                    self._load_button.cued = False
                if self._save_button is not None:
                    self._save_button.cued = False
                print(Formatter.color_success_message(result))
