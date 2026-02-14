# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

from typing import Any, List, Optional, Union

from IPython.display import display
from ipywidgets import Widget
from traitlets.utils.sentinel import Sentinel

from ._widget_cue_output import CueOutput


class CueObject(CueOutput):
    """
    A cued displayable `ipywidget.Output` for any Python object.  Provides utilities to
    clear and redraw the object, for example, after an update.

    :param object:
        The object to display
    :param widgets_to_observe:
        The widget to observe if the `traits_to_observe` has changed.
    :param traits_to_observe:
        The trait from the `widgets_to_observe` to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    :param css_style:
        - **base**: the css style of the box during initialization
        - **cue**: the css style that is added when
          `traits_to_observe` in widget `widgets_to_observe` changes.
          It is supposed to change the style of the box such that the user has a visual
          cue that `widget_to_cue` has changed.
    """

    def __init__(
        self,
        object: Any = None,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: bool = True,
        css_style: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        CueOutput.__init__(
            self,
            widgets_to_observe,
            traits_to_observe,
            cued,
            css_style,
            **kwargs,
        )

        self._object = object
        self.draw_display()

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, object: Any):
        self._object = object

    def clear_display(self, wait=False):
        self.clear_output(wait=wait)

    def draw_display(self):
        with self:
            if isinstance(self._object, str):
                print(self._object)
            elif self._object is not None:
                display(self._object)
