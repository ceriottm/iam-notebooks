from typing import List, Optional, Union

from ipywidgets import VBox, Widget
from traitlets.utils.sentinel import Sentinel

from ._widget_cue import CueWidget


class CueBox(VBox, CueWidget):
    """
    A box around the widget `widget_to_cue` that adds a visual cue defined in the
    `css_style` when the trait `traits_to_observe` in the widget `widgets_to_observe`
    changes. If the `widgets_to_observe` is a list, each widget is observed separately.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param widget_to_cue:
        The widget to wrap the box around to give a visual cue, once
        `traits_to_observe` has changed
        If None, then the `widget_to_cue` is set to `widgets_to_observe`.
    :param cued:
        Specifies if it is cued on initialization
    :param css_style:
        - **base**: the css style of the box during initialization
        - **cue**: the css style that is added when `traits_to_observe`
          in widget `widgets_to_observe` changes.
          It is supposed to change the style of the box such that the user has a visual
          cue that `widget_to_cue` has changed.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Box`.
    """

    def __init__(
        self,
        widgets_to_observe: Union[List[Widget], Widget],
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
        widget_to_cue: Optional[Widget] = None,
        cued: bool = True,
        css_style: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        if widget_to_cue is None and isinstance(widgets_to_observe, list):
            raise ValueError(
                "When widgets_to_observe is a list, widget_to_cue must be"
                " given, since it is ambiguous which widget to cue."
            )

        if css_style is None:
            css_style = {
                "base": "scwidget-cue-box",
                "cue": "scwidget-cue-box--cue",
            }
        if "base" not in css_style.keys():
            raise ValueError('css_style is missing key "base".')
        if "cue" not in css_style.keys():
            raise ValueError('css_style is missing key "cue".')
        self._css_style = css_style

        if widget_to_cue is None and not (isinstance(widgets_to_observe, list)):
            self._widget_to_cue = widgets_to_observe
        else:
            self._widget_to_cue = widget_to_cue

        VBox.__init__(self, [self._widget_to_cue], *args, **kwargs)

        self.add_class(self._css_style["base"])
        CueWidget.__init__(self, widgets_to_observe, traits_to_observe, cued)

    @property
    def widget_to_cue(self):
        return self._widget_to_cue

    @property
    def cued(self):
        return self._cued

    @cued.setter
    def cued(self, cued: bool):
        if cued:
            self.add_class(self._css_style["cue"])
        else:
            self.remove_class(self._css_style["cue"])
        self._cued = cued


class SaveCueBox(CueBox):
    """
    A box around the widget `widget_to_cue` that adds a visual cue related to saving
    when the trait `traits_to_observe` in the widget `widgets_to_observe` changes.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    :param widget_to_cue:
        The widget to wrap the box around to give a visual cue, once
        `traits_to_observe` has changed
        If None, then the `widget_to_cue` is set to `widgets_to_observe`.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Box`.
    """

    def __init__(
        self,
        widgets_to_observe: Widget,
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
        widget_to_cue: Optional[Widget] = None,
        cued: bool = True,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-save-cue-box",
            "cue": "scwidget-save-cue-box--cue",
        }
        super().__init__(
            widgets_to_observe, traits_to_observe, widget_to_cue, cued, css_style
        )


class CheckCueBox(CueBox):
    """
    A box around the widget `widget_to_cue` that adds a visual cue related to checking
    when the trait `traits_to_observe` in the widget `widgets_to_observe` changes.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param widget_to_cue:
        The widget to wrap the box around to give a visual cue, once
        `traits_to_observe` has changed
        If None, then the `widget_to_cue` is set to `widgets_to_observe`.
    :param cued:
        Specifies if it is cued on initialization

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Box`.
    """

    def __init__(
        self,
        widgets_to_observe: Widget,
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
        widget_to_cue: Optional[Widget] = None,
        cued: bool = True,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-check-cue-box",
            "cue": "scwidget-check-cue-box--cue",
        }
        super().__init__(
            widgets_to_observe, traits_to_observe, widget_to_cue, cued, css_style
        )


class UpdateCueBox(CueBox):
    """
    A box around the widget `widget_to_cue` that adds a visual cue related to updating
    when the trait `traits_to_observe` in the widget `widgets_to_observe` changes.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    :param widget_to_cue:
        The widget to wrap the box around to give a visual cue, once
        `traits_to_observe` has changed
        If None, then the `widget_to_cue` is set to `widgets_to_observe`.

    Further accepts the same (keyword) arguments as :py:class:`ipywidgets.Box`.
    """

    def __init__(
        self,
        widgets_to_observe: Widget,
        traits_to_observe: Union[
            str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = "value",
        widget_to_cue: Optional[Widget] = None,
        cued: bool = True,
        *args,
        **kwargs,
    ):
        css_style = {
            "base": "scwidget-update-cue-box",
            "cue": "scwidget-update-cue-box--cue",
        }
        super().__init__(
            widgets_to_observe, traits_to_observe, widget_to_cue, cued, css_style
        )
