# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

from typing import List, Optional, Union

from ipywidgets import Output, Widget
from traitlets.utils.sentinel import Sentinel

from ._widget_cue import CueWidget


class CueOutput(Output, CueWidget):
    """
    A cued displayable `ipywidget.Output` for any Python object.

    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    :param css_style:
        - **base**: the css style of the box during initialization
        - **cue**: the css style that is added when `traits_to_observe`
          in widget `widgets_to_observe` changes.
          It is supposed to change the style of the box such that the user has a visual
          cue that `widget_to_cue` has changed.
    """

    def __init__(
        self,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: bool = True,
        css_style: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        if css_style is None:
            css_style = {
                "base": "scwidget-cue-output",
                "cue": "scwidget-cue-output--cue",
            }
        if "base" not in css_style.keys():
            raise ValueError('css_style is missing key "base".')
        if "cue" not in css_style.keys():
            raise ValueError('css_style is missing key "cue".')

        self._css_style = css_style

        # TODO make disabling of cued transparent
        if widgets_to_observe is None and traits_to_observe is None:
            cued = False
        if widgets_to_observe is None:
            widgets_to_observe = []
        if traits_to_observe is None:
            traits_to_observe = []

        Output.__init__(self, **kwargs)
        CueWidget.__init__(self, widgets_to_observe, traits_to_observe, cued)

        self.add_class(self._css_style["base"])

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
