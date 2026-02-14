# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

import inspect
import types
from platform import python_version
from typing import Any, Callable, Dict, List, Optional, Union

from ipywidgets import HTML, Box, HBox, HTMLMath, Layout, VBox, Widget
from matplotlib.figure import Figure
from widget_code_input import WidgetCodeInput
from widget_code_input.utils import CodeValidationError

from .._utils import Formatter
from ..check import Check, CheckableWidget, CheckRegistry, CheckResult
from ..code._widget_code_input import CodeInput
from ..code._widget_parameters_panel import ParametersPanel
from ..css_style import CssStyle
from ..cue import (
    CheckCueBox,
    CheckResetCueButton,
    CueFigure,
    CueObject,
    CueOutput,
    SaveCueBox,
    SaveResetCueButton,
    UpdateCueBox,
    UpdateResetCueButton,
)
from ._widget_exercise_registry import ExerciseRegistry, ExerciseWidget


class CodeExercise(VBox, CheckableWidget, ExerciseWidget):
    """
    A widget to demonstrate code interactively in a variety of ways. It is a combination
    of the several widgets that allow to check, run and visualize code.

    :param code:
        A function or :py:class:`CodeInput` that is the input of code

    :param check_registry:
        A check registry that is used to register checks

    :param exercise_registry:
        A exercise registry that is used to register the answers to save them
        later. If specified, the save and load panel will appear.

    :param key:
        The key that is used to store the exercise in the json file.

    :param parameters:
        Input parameters for the :py:class:`ParametersPanel` class or an initialized
        :py:class:`ParametersPanel` object. Specifies the arguments in the parameter
        panel.

    :param update_mode:
        Determines how the parameters are refreshed on changes of the code input
        or parameters

    :param outputs:
        List of CueOutputs that are drawn and refreshed

    :param update:
        A function that is run during the update process. The function takes as argument
        the CodeExercise, so it can update all cue_outputs

    :param description:
        A string describing the exercises that will be put into an HTML widget
        above the exercise.

    :param title:
        A title for the exercise. If not given, `key` is used.
    """

    def __init__(
        self,
        code: Union[None, WidgetCodeInput, types.FunctionType] = None,
        check_registry: Optional[CheckRegistry] = None,
        exercise_registry: Optional[ExerciseRegistry] = None,
        key: Optional[str] = None,
        parameters: Optional[
            Union[Dict[str, Union[Check.FunInParamT, Widget]], ParametersPanel]
        ] = None,
        update_mode: str = "manual",
        outputs: Union[None, Figure, CueOutput, List[CueOutput]] = None,
        update: Optional[
            Union[
                Callable[[CodeExercise], Union[Any, Check.FunOutParamsT]],
                Callable[[], Union[Any, Check.FunOutParamsT]],
            ]
        ] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        *args,
        **kwargs,
    ):
        allowed_update_modes = ["manual", "continuous", "release"]
        if update_mode not in allowed_update_modes:
            raise TypeError(
                f"Got update mode {update_mode!r} but only "
                f"{allowed_update_modes} are allowed."
            )
        self._update_mode = update_mode

        self._update_func: Optional[
            Union[
                Callable[[CodeExercise], Union[Any, Check.FunOutParamsT]],
                Callable[[], Union[Any, Check.FunOutParamsT]],
            ]
        ] = update

        # We test update instead of self._update_func because self._update_func
        # has one additional argument because of self
        self._update_func_nb_nondefault_args: Optional[int]
        if update is not None:
            self._update_func_nb_nondefault_args = len(
                [
                    value
                    for value in inspect.signature(update).parameters.values()
                    if not isinstance(value.default, inspect._empty)
                ]
            )
            if self._update_func_nb_nondefault_args > 1:
                raise ValueError(
                    f"The given update function has "
                    f"{self._update_func_nb_nondefault_args} parameters without "
                    "defaults, but only zero or one are supported."
                )
        else:
            self._update_func_nb_nondefault_args = None

        self._description = description
        if description is None:
            self._description_html = None
        else:
            self._description_html = HTMLMath(self._description)
        if title is None:
            if key is None:
                self._title = None
                self._title_html = None
            else:
                self._title = key
                self._title_html = HTML(f"<b>{key}</b>")
        else:
            self._title = title
            self._title_html = HTML(f"<b>{title}</b>")

        if self._description_html is not None:
            self._description_html.add_class("exercise-description")
        if self._title_html is not None:
            self._title_html.add_class("exercise-title")

        # verify if input argument `parameter` is valid
        if parameters is not None:
            allowed_parameter_types = [dict, ParametersPanel]
            parameter_type_allowed = False
            for allowed_parameter_type in allowed_parameter_types:
                if isinstance(parameters, allowed_parameter_type):
                    parameter_type_allowed = True
            if not (parameter_type_allowed):
                raise TypeError(
                    f"Got parameter {type(parameters)!r} but only "
                    f"{allowed_parameter_types} are allowed."
                )

        # verify if input argument `parameter` is valid
        if isinstance(code, types.FunctionType):
            code = CodeInput(function=code)
        elif code is not None and not (isinstance(code, WidgetCodeInput)):
            raise TypeError(
                "For input code expected type None, FunctionType or "
                f"WidgetCodeInput but got {type(code)!r}"
            )

        # check compatibility between code and parameters, can only be checked if
        # update_func is not used because we cannot know how the code input is used
        if update is None and code is not None and parameters is not None:
            if isinstance(parameters, dict):
                compatibility_result = code.compatible_with_signature(
                    list(parameters.keys())
                )
            elif isinstance(parameters, ParametersPanel):
                compatibility_result = code.compatible_with_signature(
                    list(parameters.parameters.keys())
                )
            if compatibility_result != "":
                raise ValueError(
                    "code and parameters do no match:  " + compatibility_result
                )

        name = kwargs.get("name", key)
        if exercise_registry is not None:
            ExerciseWidget.__init__(self, exercise_registry, key)
        else:
            # otherwise ExerciseWidget constructor will raise an error
            ExerciseWidget.__init__(self, None, None)

        self._code = code
        self._output = CueOutput()

        if outputs is None:
            outputs = []
        elif not (isinstance(outputs, list)):
            outputs = [outputs]

        self._cue_outputs: List[CueOutput] = []
        for output in outputs:
            if isinstance(output, Figure):
                # This needs to happen before the creation of the
                # ParametersPanel otherwise the figure is not properly closed. I
                # am not sure why, I guess it is something related to interact
                self._cue_outputs.append(CueFigure(output))
            elif isinstance(output, CueOutput):
                self._cue_outputs.append(output)
            else:
                self._cue_outputs.append(CueObject(output))

        self._parameters_panel: Union[ParametersPanel, None]
        if isinstance(parameters, dict):
            self._parameters_panel = ParametersPanel(**parameters)
        elif isinstance(parameters, ParametersPanel):
            self._parameters_panel = parameters
        else:
            self._parameters_panel = None

        self._cue_code = self._code

        if check_registry is None or self._code is None:
            self._check_button = None
        else:
            self._cue_code = CheckCueBox(
                self._code, "function_body", self._cue_code, cued=True
            )
            self._check_button = CheckResetCueButton(
                [self._cue_code],
                self._on_click_check_action,
                disable_on_successful_action=kwargs.pop(
                    "disable_check_button_on_successful_action", False
                ),
                disable_during_action=kwargs.pop(
                    "disable_check_button_during_action", True
                ),
                description="Check Code",
                button_tooltip="Check the correctness of your code",
            )

        self._cue_parameters_panel = self._parameters_panel
        if self._parameters_panel is None and self._update_func is None:
            self._update_button = None
            self._cue_parameters_panel = None
        else:
            # set up update button and cueing
            # -------------------------------

            if self._code is not None:
                self._cue_code = UpdateCueBox(
                    self._code,
                    "function_body",
                    self._cue_code,
                    cued=True,
                    layout=Layout(width="98%", height="auto"),
                )

            # set up parameter panel
            # ----------------------

            if self._parameters_panel is not None:
                if self._update_mode == "continuous":
                    self._parameters_panel.set_parameters_widget_attr(
                        "continuous_update", True
                    )
                elif self._update_mode == "release":
                    self._parameters_panel.set_parameters_widget_attr(
                        "continuous_update", False
                    )

                if self._update_mode in ["continuous", "release"]:
                    self._parameters_panel.observe_parameters(
                        self._on_trait_parameters_changed, "value"
                    )

                    if self._code is not None:
                        # the button only cues on cue_code change
                        widgets_to_observe = [self._code]
                        traits_to_observe = ["function_body"]
                    else:
                        widgets_to_observe = None
                        traits_to_observe = None
                    # assume when continuous that the function is fast
                    # and that disabling causes flicker
                    update_button_disable_during_action = False
                    if self._code is not None:
                        for cue_output in self._cue_outputs:
                            # TODO this has to be made public
                            cue_output._widgets_to_observe = [self._code]
                            cue_output._traits_to_observe = ["function_body"]
                            cue_output.observe_widgets()

                    self._cue_parameters_panel = UpdateCueBox(
                        [],
                        [],
                        self._parameters_panel,
                        cued=self._code is not None,
                    )
                else:
                    widgets_to_observe = None
                    traits_to_observe = None
                    update_button_disable_during_action = True

                    self._cue_parameters_panel = UpdateCueBox(
                        self._parameters_panel.panel_parameters_widget,
                        self._parameters_panel.panel_parameters_trait,  # type: ignore
                        self._parameters_panel,
                    )

                    for cue_output in self._cue_outputs:
                        if self._code is not None:
                            # TODO this has to be made public
                            cue_output._widgets_to_observe = [
                                self._code
                            ] + self._parameters_panel.panel_parameters_widget
                            # fmt: off
                            cue_output._traits_to_observe = (

                                [  # type: ignore[assignment]
                                    "function_body"
                                ]
                                + self._parameters_panel.panel_parameters_trait
                            )
                            # fmt: on

                            cue_output.observe_widgets()
                        else:
                            # TODO this has to be made public
                            cue_output._widgets_to_observe = (
                                self._parameters_panel.panel_parameters_widget
                            )
                            cue_output._traits_to_observe = (
                                self._parameters_panel.panel_parameters_trait  # type: ignore[assignment] # noqa: E501
                            )
                            cue_output.observe_widgets()
            elif self._code is not None:
                widgets_to_observe = [self._code]
                traits_to_observe = ["function_body"]
                # only code demo with an update function exists,
                # we therefore assume update is slow
                update_button_disable_during_action = True
            else:
                widgets_to_observe = []
                traits_to_observe = []
                # only update function exists, we assume update is slow
                update_button_disable_during_action = True

            reset_update_cue_widgets = []
            if self._cue_code is not None:
                reset_update_cue_widgets.append(self._cue_code)
            if self._cue_parameters_panel is not None:
                reset_update_cue_widgets.append(self._cue_parameters_panel)
            if self._cue_outputs is not None:
                reset_update_cue_widgets.extend(self._cue_outputs)

            if self._code is not None or self._update_mode == "manual":
                if self._code is not None:
                    description = "Run Code"
                    button_tooltip = (
                        "Runs the code and updates outputs with the "
                        "specified parameters"
                    )
                else:
                    description = "Update"
                    button_tooltip = "Updates outputs with the specified parameters"
                self._update_button = UpdateResetCueButton(
                    reset_update_cue_widgets,  # type: ignore[arg-type]
                    self._on_click_update_action,
                    disable_on_successful_action=kwargs.pop(
                        "disable_update_button_on_successful_action", False
                    ),
                    disable_during_action=kwargs.pop(
                        "disable_update_button_during_action",
                        update_button_disable_during_action,
                    ),
                    widgets_to_observe=widgets_to_observe,
                    traits_to_observe=traits_to_observe,  # type: ignore[arg-type]
                    description=description,
                    button_tooltip=button_tooltip,
                    cued=True,
                )
            else:
                self._update_button = None

        if self._exercise_registry is None or (
            self._code is None and self._parameters_panel is None
        ):
            self._save_button = None
            self._load_button = None
            self._save_cue_box = None
        else:
            save_widgets_to_observe = []
            save_traits_to_observe = []

            if self._cue_code is not None:
                save_widgets_to_observe.append(self._code)
                save_traits_to_observe.append("function_body")

            if self._parameters_panel is not None:
                save_widgets_to_observe.extend(
                    self._parameters_panel.panel_parameters_widget
                )
                save_traits_to_observe.extend(
                    self._parameters_panel.panel_parameters_trait
                )

            if self._cue_code is not None:
                self._cue_code = SaveCueBox(
                    save_widgets_to_observe,
                    save_traits_to_observe,  # type: ignore[arg-type]
                    self._cue_code,
                    cued=True,
                )

            self._save_cue_box = self._cue_code
            self._save_button = SaveResetCueButton(
                SaveCueBox(Box()),  # dummy cue box, because we set cues later on
                self._on_click_save_action,
                cued=True,
                disable_on_successful_action=kwargs.pop(
                    "disable_save_button_on_successful_action", False
                ),
                disable_during_action=kwargs.pop(
                    "disable_save_button_during_action", True
                ),
                description="Save code",
                button_tooltip="Loads your code and parameters from the loaded file",
            )
            self._load_button = SaveResetCueButton(
                SaveCueBox(Box()),  # dummy cue box, because we set cues later on
                self._on_click_load_action,
                cued=True,
                disable_on_successful_action=kwargs.pop(
                    "disable_load_button_on_successful_action", False
                ),
                disable_during_action=kwargs.pop(
                    "disable_load_button_during_action", True
                ),
                description="Load code",
                button_tooltip="Saves your code and parameters to the loaded file",
            )

            # click on load button resets cue of save buton and vise-versa
            self._save_button.set_cue_widgets(
                [
                    widget
                    for widget in [
                        self._cue_code,
                        self._cue_parameters_panel,
                        self._load_button,
                    ]
                    if widget is not None
                ]
            )
            self._load_button.set_cue_widgets(
                [
                    widget
                    for widget in [
                        self._cue_code,
                        self._cue_parameters_panel,
                        self._save_button,
                    ]
                    if widget is not None
                ]
            )

        demo_children = [CssStyle()]
        if self._title_html is not None:
            demo_children.append(self._title_html)
        if self._description_html is not None:
            demo_children.append(self._description_html)

        if self._cue_code is not None:
            demo_children.append(self._cue_code)
        if self._cue_parameters_panel is not None:
            demo_children.append(self._cue_parameters_panel)

        buttons = []
        if self._check_button is None and self._update_button is None:
            self._code_buttons = HBox([])
        elif self._check_button is None:
            self._code_buttons = HBox([self._update_button])
        elif self._update_button is None:
            self._code_buttons = HBox([self._check_button])
        else:
            self._code_buttons = HBox([self._check_button, self._update_button])
        buttons.append(self._code_buttons)

        if self._save_button is not None and self._load_button is not None:
            self._answer_buttons = HBox(
                [self._save_button, self._load_button],
                layout=Layout(justify_content="flex-end"),
            )
        else:
            self._answer_buttons = Box([])
        buttons.append(self._answer_buttons)

        self._buttons_panel = HBox(
            buttons, layout=Layout(justify_content="space-between")
        )

        demo_children.extend(
            [
                self._buttons_panel,
                self._output,
            ]
        )
        demo_children.extend(self._cue_outputs)

        VBox.__init__(
            self,
            demo_children,
            *args,
            **kwargs,
        )
        CheckableWidget.__init__(self, check_registry, name)
        # In this case there is no code to be written by the student, so the code
        # exercise should work out of the box. Since the cues for the parameters
        # are also disabled, we update at the beginning once.
        if self._update_mode in ["release", "continuous"] and self._code is None:
            self.run_update()

    @property
    def answer(self) -> dict:
        return {
            "code": None if self._code is None else self._code.function_body,
            "parameters_panel": (
                None
                if self._parameters_panel is None
                else self._parameters_panel.parameters
            ),
        }

    @answer.setter
    def answer(self, answer: dict):
        if self._save_cue_box is not None:
            self._save_cue_box.unobserve_widgets()
        if self._save_button is not None:
            self._save_button.unobserve_widgets()
        if self._load_button is not None:
            self._load_button.unobserve_widgets()

        if answer["code"] is not None and self._code is not None:
            self._code.function_body = answer["code"]
        if (
            answer["parameters_panel"] is not None
            and self._parameters_panel is not None
        ):
            self._parameters_panel.update_parameters(answer["parameters_panel"])

        if self._save_cue_box is not None:
            self._save_cue_box.observe_widgets()
        if self._save_button is not None:
            self._save_button.observe_widgets()
        if self._load_button is not None:
            self._load_button.observe_widgets()

    @property
    def parameters_panel(self) -> Union[ParametersPanel, None]:
        """
        :return: The parameters panel widget.
        """

        return self._parameters_panel

    @property
    def panel_parameters(self) -> Dict[str, Check.FunInParamT]:
        """
        :return: Only parameters that are tunable in the parameter panel are returned.
            Fixed parameters are ignored.
        """
        return (
            {}
            if self._parameters_panel is None
            else self._parameters_panel.panel_parameters
        )

    @property
    def parameters(self) -> Dict[str, Check.FunInParamT]:
        """
        :return: All parameters that were given on initialization are returned,
            including fixed parameters.
        """
        return (
            {} if self._parameters_panel is None else self._parameters_panel.parameters
        )

    @property
    def title(self) -> Union[str, None]:
        return self._title

    @property
    def description(self) -> Union[str, None]:
        return self._description

    def _on_trait_parameters_changed(self, change: dict):
        self.run_update()

    def _on_click_check_action(self) -> bool:
        self._output.clear_output(wait=True)
        raised_error = False
        with self._output:
            try:
                self._check()
            except Exception as e:
                raised_error = True
                if python_version() >= "3.11":
                    e.add_note("This error is most likely not related to your code.")
                raise e
        return not (raised_error)

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
                raised_error = True
                print(Formatter.color_error_message("Error raised while saving file:"))
                raise e
        return not (raised_error)

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
            except Exception as e:
                raised_error = True
                print(Formatter.color_error_message("Error raised while loading file:"))
                raise e
        return not (raised_error)

    def _check(self) -> List[Union[CheckResult, Exception]]:
        return CheckableWidget.check(self)

    def run_check(self) -> None:
        if self._check_button is not None:
            self._check_button.click()
        else:
            self._on_click_check_action()

    def compute_output_to_check(self, *args, **kwargs) -> Check.FunOutParamsT:
        return self.run_code(*args, **kwargs)

    def handle_checks_result(self, results: List[Union[CheckResult, Exception]]):
        self._output.clear_output(wait=True)
        with self._output:
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    raise result
                elif isinstance(result, CheckResult):
                    if result.successful:
                        print(Formatter.color_success_message("Check was successful"))
                        print(Formatter.color_success_message("--------------------"))
                        print(result.message())
                    else:
                        print(Formatter.color_error_message("Check failed"))
                        print(Formatter.color_error_message("------------"))
                        print(result.message())
                else:
                    print(result)
                # add linebreak if not end
                if i != len(results):
                    print()

    def handle_save_result(self, result: Union[str, Exception]):
        self._output.clear_output(wait=True)
        with self._output:
            if isinstance(result, Exception):
                raise result
            else:
                if self._load_button is not None:
                    self._load_button.cued = False
                if self._save_button is not None:
                    self._save_button.cued = False
                if self._save_cue_box is not None:
                    self._save_cue_box.cued = False
                print(Formatter.color_success_message(result))

    def handle_load_result(self, result: Union[str, Exception]):
        self._output.clear_output(wait=True)
        with self._output:
            if isinstance(result, Exception):
                raise result
            else:
                if self._load_button is not None:
                    self._load_button.cued = False
                if self._save_button is not None:
                    self._save_button.cued = False
                if self._save_cue_box is not None:
                    self._save_cue_box.cued = False
                print(Formatter.color_success_message(result))

    @property
    def code(self):
        return self._code

    @property
    def output(self) -> Union[CueOutput, None]:
        return self._cue_outputs[0] if len(self._cue_outputs) > 0 else None

    @property
    def outputs(self) -> List[CueOutput]:
        return self._cue_outputs

    @property
    def figure(self) -> Union[Figure, None]:
        return (
            self._cue_outputs[0].figure
            if len(self._cue_outputs) > 0
            and isinstance(self._cue_outputs[0], CueFigure)
            else None
        )

    def _on_click_update_action(self) -> bool:
        self._output.clear_output(wait=True)
        raised_error = False
        # runs code and displays output
        with self._output:
            try:
                for cue_output in self.outputs:
                    if hasattr(cue_output, "clear_display"):
                        cue_output.clear_display(wait=True)

                if self._update_func is not None:
                    if self._update_func_nb_nondefault_args == 0:
                        self._update_func()  # type: ignore[call-arg]
                    else:
                        self._update_func(self)  # type: ignore[call-arg]
                elif self._code is not None:
                    self.run_code(**self.parameters)

                for cue_output in self.outputs:
                    if hasattr(cue_output, "draw_display"):
                        cue_output.draw_display()

            except CodeValidationError as e:
                raised_error = True
                raise e
            except Exception as e:
                raised_error = True
                raise e

            # The clear_output command at the beginning of the function waits till
            # something is printed. If nothing is printed, it is not cleared. We
            # enforce it to be invoked by printing an empty char
            print("\0", end="")

        return not (raised_error)

    def run_update(self):
        """
        Invokes an update run, the same that is invoked by a click on the update button,
        or when a parameter is changed for `update_mode` "release" and "continuous"
        """
        if self._update_button is not None:
            # to also invoke the reset cue action, we click the cued button
            self._update_button.click()
        else:
            # we might be in update_mode "release" or "continuous" where no button is
            # displayed
            self._on_click_update_action()

    def run_code(self, *args, **kwargs) -> Check.FunOutParamsT:
        """
        Runs the `code` with the given (keyword) arguments and returns the output of the
        `code`. If no `code` was given on initialization, then a `ValueError` is raised.
        """
        try:
            if self._code is None:
                raise ValueError(
                    "run_code was invoked, but no code was given on initializaion"
                )
            return self._code(*args, **kwargs)
        except CodeValidationError as e:
            raise e
        except Exception as e:
            # we give the student the additional information that this is most likely
            # not because of his code
            if python_version() >= "3.11":
                e.add_note("This might be not related to your code input.")
            raise e
