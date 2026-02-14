from typing import Any, Callable, Dict, List, Union

from ipywidgets import Output, VBox, Widget, fixed, interactive
from traitlets.utils.sentinel import Sentinel

from ..check import Check


class ParametersPanel(VBox):
    """
    A wrapper around `ipywidgets.interactive` to have more control on how the
    parameters are connected and the parameters are observed by the buttons and panels
    :param parameters:
        Can be any input that is allowed as keyword arguments in
        `ipywidgets.interactive` for the parameters. `_option` and other widget layout
        parameters are controlled by `CodeExercise`.
    """

    def __init__(
        self,
        **parameters: Dict[str, Union[Check.FunInParamT, Widget]],
    ):
        if "_option" in parameters.keys():
            raise ValueError(
                "Found interactive argument `_option` in parameters, but "
                "ParametersPanel should be controlled by an exercise widget "
                "to ensure correct initialization."
            )

        # we use a dummy function because interactive executes it once on init
        # and the actual function might be expensive to compute
        def dummy_function(**kwargs):
            pass

        self._interactive_widget = interactive(dummy_function, **parameters)
        assert isinstance(self._interactive_widget.children[-1], Output), (
            "Assumed that interactive returns an output as last child. "
            "Parameter will be wrongly initialized if this is not True."
        )
        # Because interact only keeps a list of the widgets we build a map
        # so the params can be changed in arbitrary order.
        # Last widget is an output that interact adds to the widgets.
        self._param_to_widget_map = {
            key: widget
            for key, widget in zip(
                parameters.keys(), self._interactive_widget.kwargs_widgets
            )
        }
        super().__init__(self.panel_parameters_widget)

    @property
    def param_to_widget_map(self) -> dict[str, Widget]:
        """
        :return: A dictionary mapping parameter names to their corresponding widgets.
        """
        return self._param_to_widget_map

    @property
    def panel_parameters_trait(self) -> List[str]:
        return ["value"] * len(self.panel_parameters)

    @property
    def panel_parameters_widget(self) -> List[Widget]:
        """
        :return: Only parameters that are tunable in the parameter panel are returned.
            Fixed parameters are ignored.
        """
        return [
            widget
            for widget in self._param_to_widget_map.values()
            if not (isinstance(widget, fixed))
        ]

    @property
    def parameters(self) -> Dict[str, Any]:
        """
        :return: All parameters that were given on initialization are returned,
            also including fixed parameters.
        """
        return {key: widget.value for key, widget in self._param_to_widget_map.items()}

    @property
    def panel_parameters(self) -> Dict[str, Any]:
        """
        :return: Only parameters that are tunable in the parameter panel are returned.
            Fixed parameters are ignored.
        """
        return {
            key: widget.value
            for key, widget in self._param_to_widget_map.items()
            if not (isinstance(widget, fixed))
        }

    def update_parameters(self, new_parameters: Dict[str, Any]):
        for key, value in new_parameters.items():
            self.param_to_widget_map[key].value = value

    def observe_parameters(
        self,
        handler: Callable[[dict], None],
        trait_name: Union[str, Sentinel, List[str]],
        notification_type: Union[None, str, Sentinel] = "change",
    ):
        for widget in self.panel_parameters_widget:
            widget.observe(handler, trait_name, notification_type)

    def unobserve_parameters(
        self,
        handler: Callable[[dict], None],
        trait_name: Union[str, Sentinel, List[str]],
        notification_type: Union[None, str, Sentinel] = "change",
    ):
        for widget in self.panel_parameters_widget:
            widget.unobserve(handler, trait_name, notification_type)

    def set_parameters_widget_attr(self, name: str, value):
        for widget in self.panel_parameters_widget:
            if hasattr(widget, name):
                setattr(widget, name, value)
