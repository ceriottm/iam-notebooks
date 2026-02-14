from typing import Callable, Dict, List, Optional, Union

from ipywidgets import Button, Widget
from traitlets.utils.sentinel import Sentinel

from ._widget_cue import CueWidget


class ResetCueButton(Button, CueWidget):
    """
    A button that resets the cueing of the `cue_widgets` on a successful action.

    :param cue_widgets:
       List of cue boxes the button resets on successful click
       We assert that all boxes observe the same traits of the same widget
    :param action:
        A callable that returns a boolean that specifies if the action was successful.
        It is called on a button click, and the cues in `cue_widgets` are removed
        if it was successful. If set to ``False``, nothing happens.
    :param disable_on_successful_action:
        Specifies if the button should be disabled on a successful action
    :param disable_during_action:
        Specifies if the button should be disabled during the action
    :param css_style:
        - **base**: the css style of the box during initialization
        - **cue**: the css style that is added when `traits_to_observe`
          in widget `widget_to_observe` changes.
          It is supposed to change the style of the box such that the user has a visual
          cue that `widget_to_cue` has changed.
    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed. If ``None``
        then widgets from `cue_widgets` are taken.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe changes of.
        Specify `traitlets.All` to observe all traits. If ``None`` then traits
        from `cue_widgets` are taken.
    :param cued:
        Specifies if it is cued on initialization. If ``None`` then the button is
        cued when `cue_widgets` is cued.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Button`.
    """

    def __init__(
        self,
        cue_widgets: Union[CueWidget, List[CueWidget]],
        action: Callable[[], bool],
        disable_on_successful_action: bool = True,
        disable_during_action: bool = True,
        css_style: Optional[Dict[str, str]] = None,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: Union[None, bool] = None,
        *args,
        **kwargs,
    ):
        if css_style is None:
            css_style = {
                "base": "scwidget-reset-cue-button",
                "cue": "scwidget-reset-cue-button--cue",
            }
        if "base" not in css_style.keys():
            raise ValueError('css_style is missing key "base".')
        if "cue" not in css_style.keys():
            raise ValueError('css_style is missing key "cue".')

        if not (isinstance(cue_widgets, list)):
            cue_widgets = [cue_widgets]

        self._action = action
        self._disable_on_successful_action = disable_on_successful_action
        self._disable_during_action = disable_during_action

        self._css_style = css_style

        tooltip = kwargs.pop("button_tooltip", None)
        Button.__init__(self, *args, tooltip=tooltip, **kwargs)

        if widgets_to_observe is None:
            widgets_to_observe = []
            for cue_widget in cue_widgets:
                widgets_to_observe.extend(cue_widget.widgets_to_observe)
        if traits_to_observe is None:
            traits_to_observe = []
            for cue_widget in cue_widgets:
                traits_to_observe.extend(cue_widget.traits_to_observe)
        if cued is None:
            cued = any([cue_widget.cued for cue_widget in cue_widgets])

        CueWidget.__init__(
            self,
            widgets_to_observe=widgets_to_observe,
            traits_to_observe=traits_to_observe,
            cued=cued,
        )
        self._cue_widgets = cue_widgets

        self.on_click(self._on_click)

        self.add_class(self._css_style["base"])

    @property
    def cue_widgets(self) -> List[CueWidget]:
        return self._cue_widgets

    def set_cue_widgets(
        self, cue_widgets: List[CueWidget], overwrite_cue_observes: bool = True
    ):
        """
        :param cue_widgets:
           List of cue boxes the button resets on successful click
           We assert that all boxes observe the same traits of the same widget

        :param overwrite_cue_observes:
            If `True`, the function will override the existing observation settings
            based on `cue_widgets`.
        """
        # set new cue widgets
        widgets_to_observe = []
        traits_to_observe = []
        for cue_widget in cue_widgets:
            widgets_to_observe.extend(cue_widget.widgets_to_observe)
            traits_to_observe.extend(cue_widget.traits_to_observe)
        if overwrite_cue_observes:
            self.set_widgets_to_observe(widgets_to_observe, traits_to_observe)
            self.cued = any([cue_widget.cued for cue_widget in cue_widgets])
        self._cue_widgets = cue_widgets

    @property
    def cued(self):
        return self._cued

    @cued.setter
    def cued(self, cued: bool):
        if cued:
            self.add_class(self._css_style["cue"])
            self.disabled = False
        else:
            self.remove_class(self._css_style["cue"])
        self._cued = cued

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        self._action = action

    @property
    def disable_on_successful_action(self):
        return self._disable_on_successful_action

    @disable_on_successful_action.setter
    def disable_on_successful_action(self, disable_on_successful_action: bool):
        self._disable_on_successful_action = disable_on_successful_action

    def _on_click(self, button: Button):
        self.disabled = self._disable_during_action
        success = False
        try:
            success = self._action()
        except Exception as e:
            raise e
        finally:
            for cue_box in self._cue_widgets:
                cue_box.cued = False
            self.cued = False
            self.disabled = success and self._disable_on_successful_action


class SaveResetCueButton(ResetCueButton):
    """
    A button that resets the cueing of the `cue_widgets` on a successful Save action.

    :param cue_widgets:
       List of cue boxes the button resets on successful click
       We assert that all boxes observe the same traits of the same widget
    :param action:
        A callable that returns a boolean that specifies if the action was successful.
        It is called on a button click, and the cues in `cue_widgets` are removed
        if it was successful. If set to ``False``, nothing happens.
    :param disable_on_successful_action:
        Specifies if the button should be disabled on a successful action
    :param disable_during_action:
        Specifies if the button should be disabled during the action
    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed. If ``None``
        then widgets from `cue_widgets` are taken.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe changes of.
        Specify `traitlets.All` to observe all traits. If ``None``, traits
        from `cue_widgets` are taken.
    :param cued:
        Specifies if it is cued on initialization. If ``None`` then the button is
        cued when `cue_widget`: is cued.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Button`.
    """

    def __init__(
        self,
        cue_widgets: Union[CueWidget, List[CueWidget]],
        action: Callable[[], bool],
        disable_on_successful_action: bool = True,
        disable_during_action: bool = True,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: Union[None, bool] = None,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-save-reset-cue-button",
            "cue": "scwidget-save-reset-cue-button--cue",
        }
        super().__init__(
            cue_widgets,
            action,
            disable_on_successful_action,
            disable_during_action,
            css_style,
            widgets_to_observe,
            traits_to_observe,
            cued,
            *args,
            **kwargs,
        )


class CheckResetCueButton(ResetCueButton):
    """
    A button that resets the cueing of the :param cue_widgets: on a successful check
    action.

    :param cue_widgets:
       List of cue boxes the button resets on successful click
       We assert that all boxes observe the same traits of the same widget
    :param action:
        A callable that returns a boolean that specifies if the action was successful.
        It is called on a button click, and the cues in `cue_widgets` are removed
        if it was successful. If set to ``False``, nothing happens.
    :param disable_on_successful_action:
        Specifies if the button should be disabled on a successful action
    :param disable_during_action:
        Specifies if the button should be disabled during the action
    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed. If ``None``
        then widgets from `cue_widgets` are taken.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe changes of.
        Specify `traitlets.All` to observe all traits. If ``None``, traits
        from `cue_widgets` are taken.
    :param cued:
        Specifies if it is cued on initialization. If ``None`` then the button is
        cued when `cue_widget`: is cued.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Button`.
    """

    def __init__(
        self,
        cue_widgets: Union[CueWidget, List[CueWidget]],
        action: Callable[[], bool],
        disable_on_successful_action: bool = True,
        disable_during_action: bool = True,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: Union[None, bool] = None,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-check-reset-cue-button",
            "cue": "scwidget-check-reset-cue-button--cue",
        }
        super().__init__(
            cue_widgets,
            action,
            disable_on_successful_action,
            disable_during_action,
            css_style,
            widgets_to_observe,
            traits_to_observe,
            cued,
            *args,
            **kwargs,
        )


class UpdateResetCueButton(ResetCueButton):
    """
    A button that resets the cueing of the :param cue_widgets: on a successful update
    action.

    :param cue_widgets:
       List of cue boxes the button resets on successful click
       We assert that all boxes observe the same traits of the same widget
    :param action:
        A callable that returns a boolean that specifies if the action was successful.
        It is called on a button click, and the cues in `cue_widgets` are removed
        if it was successful. If set to ``False``, nothing happens.
    :param disable_on_successful_action:
        Specifies if the button should be disabled on a successful action
    :param disable_during_action:
        Specifies if the button should be disabled during the action
    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed. If ``None``
        then widgets from `cue_widgets` are taken.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe changes of.
        Specify `traitlets.All` to observe all traits. If ``None``, traits
        from `cue_widgets` are taken.
    :param cued:
        Specifies if it is cued on initialization. If ``None`` then the button is
        cued when `cue_widget`: is cued.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Button`.
    """

    def __init__(
        self,
        cue_widgets: Union[CueWidget, List[CueWidget]],
        action: Callable[[], bool],
        disable_on_successful_action: bool = True,
        disable_during_action: bool = True,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: Union[None, bool] = None,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-update-reset-cue-button",
            "cue": "scwidget-update-reset-cue-button--cue",
        }
        super().__init__(
            cue_widgets,
            action,
            disable_on_successful_action,
            disable_during_action,
            css_style,
            widgets_to_observe,
            traits_to_observe,
            cued,
            *args,
            **kwargs,
        )
