# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

from collections import OrderedDict
from typing import Callable, List, Optional, Union

from ipywidgets import Button, HBox, Layout, Output, VBox, Widget

from .._utils import Formatter
from ..css_style import CssStyle
from ._check import Check, CheckResult


class CheckableWidget:
    """
    A base class for any widget to inherit from to be compatible with the
    :py:class:`CheckRegistry`. The widget can be registered to a `CheckRegistry`,
    which allows applying checks.

    :param check_registry:
        the check registry that registers the checks for this widget

    :param name:
        Optional name of the widget that is shown in the messages of the checks
    """

    def __init__(
        self, check_registry: Optional[CheckRegistry] = None, name: Optional[str] = None
    ):
        self._check_registry = check_registry
        if self._check_registry is not None:
            self._check_registry.register_widget(self, name)

    def compute_output_to_check(
        self, *input_args: Check.FunInParamT
    ) -> Check.FunOutParamsT:
        """
        The widget returns the output that will be verified by the added checks.
        """
        raise NotImplementedError("compute_output_to_check has not been implemented")

    def handle_checks_result(
        self, results: List[Union[CheckResult, Exception]]
    ) -> None:
        """
        Function that controls how results of the checks are handled.
        """
        raise NotImplementedError("handle_checks_result has not been implemented")

    def add_check(self, *args, **kwargs):
        """
        Adds checks to the widget. Accepts either a `Check` object (or list of
        `Check` objects) directly, or parameters that define a new check.
        """
        # simple dispatch logic
        if len(args) + len(kwargs) == 1:
            self._add_check_from_check(*args, **kwargs)
        else:
            self._add_check_from_check_parameters(*args, **kwargs)

    def _add_check_from_check(self, checks: Union[List[Check], Check]):
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, no checks can be added"
            )
        if isinstance(checks, Check):
            checks = [checks]
        for check in checks:
            self._check_registry.add_check(
                self,
                check.asserts,
                check.inputs_parameters,
                check.outputs_references,
                check.fingerprint,
            )

    def _add_check_from_check_parameters(
        self,
        asserts: Union[List[Check.AssertFunT], Check.AssertFunT],
        inputs_parameters: Optional[Union[List[dict], dict]] = None,
        outputs_references: Optional[
            Union[List[Check.FunOutParamsT], Check.FunOutParamsT]
        ] = None,
        fingerprint: Optional[
            Callable[[Check.FunOutParamsT], Check.FingerprintT]
        ] = None,
        suppress_fingerprint_asserts: bool = True,
    ):
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, no checks can be added"
            )

        self._check_registry.add_check(
            self,
            asserts,
            inputs_parameters,
            outputs_references,
            fingerprint,
            suppress_fingerprint_asserts,
        )

    def compute_and_set_references(self):
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, "
                "compute_and_set_references cannot be used"
            )

        self._check_registry.compute_and_set_references(self)

    def check(self) -> List[Union[CheckResult, Exception]]:
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, " "check cannot be used"
            )
        return self._check_registry.check_widget(self)

    @property
    def checks(self):
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, " "no checks to access"
            )
        return self._check_registry._checks[self]

    @property
    def check_registry(self):
        return self._check_registry

    @property
    def nb_conducted_asserts(self):
        if self._check_registry is None:
            raise ValueError(
                "No check registry given on initialization, " "no checks to access"
            )
        return self._check_registry.nb_conducted_asserts(self)


class CheckRegistry(VBox):
    """
    Manages the assignment of checks to widgets and the execution of checks. It allows
    to run the checks of all widgets and properly pipes the result to the corresponding
    function of the widget.
    """

    def __init__(self, *args, **kwargs):
        self._checks = OrderedDict()
        self._names = OrderedDict()
        self._set_all_references_button = Button(description="Set all references")
        self._check_all_widgets_button = Button(description="Check all widgets")
        self._output = Output()
        kwargs["layout"] = kwargs.pop("layout", Layout(width="100%"))

        self._buttons_hbox = HBox()

        # needs to be after the _buttons_hbox already was created
        self.display_set_all_references_button = kwargs.pop(
            "display_set_all_references_button", False
        )

        VBox.__init__(
            self,
            [
                CssStyle(),
                self._buttons_hbox,
                self._output,
            ],
            *args,
            **kwargs,
        )

        self._set_all_references_button.on_click(
            self._on_click_set_all_references_button
        )
        self._check_all_widgets_button.on_click(self._on_click_check_all_widgets_button)

    @property
    def checks(self):
        """
        Returns all checks registered for each widget.
        """
        return self._checks

    @property
    def display_set_all_references_button(self) -> bool:
        return self._display_set_all_references_button

    @display_set_all_references_button.setter
    def display_set_all_references_button(self, value: bool):
        if value:
            self._display_set_all_references_button = True
            self._buttons_hbox.children = (
                self._check_all_widgets_button,
                self._set_all_references_button,
            )
        else:
            self._display_set_all_references_button = False
            self._buttons_hbox.children = (self._check_all_widgets_button,)

    @property
    def registered_widgets(self):
        """
        Returns a copy of all widgets currently registered with this registry.
        """
        return self._widgets.copy()

    def nb_conducted_asserts(self, widget: CheckableWidget):
        """
        The total number of asserts that will be conducted for the widget

        :param widget:
            the checks of the widget are targeted
        """
        return sum([check.nb_conducted_asserts for check in self._checks[widget]])

    def register_widget(self, widget: CheckableWidget, name: Optional[str] = None):
        self._checks[widget] = []
        if name is None:
            self._names[widget] = len(self._names) + 1
        else:
            self._names[widget] = name

    def add_check(
        self,
        widget: CheckableWidget,
        asserts: Union[List[Check.AssertFunT], Check.AssertFunT],
        inputs_parameters: Optional[Union[List[dict], dict]] = None,
        outputs_references: Optional[
            Union[List[Check.FunOutParamsT], Check.FunOutParamsT]
        ] = None,
        fingerprint: Optional[
            Callable[[Check.FunOutParamsT], Check.FingerprintT]
        ] = None,
        suppress_fingerprint_asserts: bool = True,
        stop_on_assert_error_raised: bool = False,
    ):
        """
        Adds a new check for the specified widget. The check is defined using assert
        functions, and optional input parameters, output references, and fingerprint
        function.
        :param widget:
            The widget to which the check is being added.
        :param asserts:
            Functions to validate the widget's output.
        :param inputs_parameters:
            Inputs to provide when calling the widget's output computation method.
        :param outputs_references:
            Expected reference outputs used for assertions.
        :param fingerprint:
            Optional function to obfuscate outputs before assertions.
        :param suppress_fingerprint_asserts:
            If True, suppresses assert messages involving fingerprinted outputs.
        """
        if not (issubclass(type(widget), CheckableWidget)):
            raise ValueError("Argument widget must be subclass of CheckableWidget")
        if widget not in self._checks.keys():
            raise ValueError(
                "Argument widget must be first registered before checks can be added."
            )
        check = Check(
            widget.compute_output_to_check,
            asserts,
            inputs_parameters,
            outputs_references,
            fingerprint,
            suppress_fingerprint_asserts,
            stop_on_assert_error_raised,
        )
        self._checks[widget].append(check)

    def compute_and_set_references(self, widget: Widget):
        for check in self._checks[widget]:
            try:
                check.compute_and_set_references()
            except Exception as exception:
                widget.handle_checks_result([exception])
                raise exception

    def compute_outputs(self, widget: CheckableWidget):
        for check in self._checks[widget]:
            try:
                return check.compute_outputs()
            except Exception as exception:
                widget.handle_checks_result([exception])
                raise exception

    def compute_and_set_all_references(self):
        for widget in self._checks.keys():
            self.compute_and_set_references(widget)

    def check_widget(
        self, widget: CheckableWidget
    ) -> List[Union[CheckResult, Exception]]:
        checks_result = []
        try:
            for check in self._checks[widget]:
                result = check.check_function()
                checks_result.append(result)
            widget.handle_checks_result(checks_result)
            return checks_result
        except Exception as exception:
            checks_result.append(exception)
            widget.handle_checks_result(checks_result)
            return checks_result

    def check_all_widgets(
        self,
    ) -> OrderedDict[CheckableWidget, List[Union[CheckResult, Exception]]]:
        messages: OrderedDict[CheckableWidget, List[Union[CheckResult, Exception]]] = (
            OrderedDict()
        )
        for widget in self._checks.keys():
            try:
                messages[widget] = self.check_widget(widget)
            except Exception as exception:
                messages[widget] = [exception]
        return messages

    def _on_click_set_all_references_button(self, change: dict):
        self._output.clear_output(wait=True)
        with self._output:
            self.compute_and_set_all_references()
            print(Formatter.color_success_message("Successfully set all references."))

    def _on_click_check_all_widgets_button(self, change: dict):
        self._output.clear_output(wait=True)
        try:
            # we raise the error within in the output so we can iterate through all
            # widget results even when an exception is raised
            # to prevent silent exceptions raised before the output in check_all_widgets
            # we wrap it in a try-catch block
            widgets_results = self.check_all_widgets()
            for widget, widget_results in widgets_results.items():
                with self._output:
                    if wrong_types := [
                        result
                        for result in widget_results
                        if not (
                            isinstance(result, Exception)
                            or isinstance(result, CheckResult)
                        )
                    ]:
                        raise ValueError(
                            f"Not supported result type {type(wrong_types[0])}. "
                            "Only results of type `Exception` and `CheckResult` "
                            "are supported."
                        )
                    elif [
                        result
                        for result in widget_results
                        if isinstance(result, Exception)
                    ]:
                        print(
                            Formatter.color_error_message(
                                f"Widget {self._names[widget]}: ‼ (error)"
                            )
                        )

                    elif not [
                        result
                        for result in widget_results
                        if isinstance(result, CheckResult) and not result.successful
                    ]:
                        print(
                            Formatter.color_success_message(
                                f"Widget {self._names[widget]}: ✓ (success)"
                            )
                        )
                    else:
                        print(
                            Formatter.color_error_message(
                                f"Widget {self._names[widget]}: 𐄂 (failed)"
                            )
                        )
        except Exception as exception:
            with self._output:
                print(
                    Formatter.color_error_message(
                        "Error raised while checking widgets:"
                    ),
                    exception,
                )
                raise exception
