# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

from typing import List, Optional, Union

import matplotlib
import matplotlib.pyplot as plt
from IPython.display import display
from ipywidgets import Widget
from matplotlib.figure import Figure
from traitlets.utils.sentinel import Sentinel

from ._widget_cue_output import CueOutput


class CueFigure(CueOutput):
    """
    A cued, displayable `ipywidget.Output` for a `matplotlib` figure.  Provides
    utilities to clear and draw the updated figure.  For the `matplotlib inline`
    backend, it closes the active figure to prevent any display outside of the
    container, which happens on the creation of the figure because `pyplot` does magic
    behind the curtain that is hard to suppress.  For the matplotlib interactive widget
    backend, named "nbagg", it wraps the figure within.

    :param figure:
        The `matplotlib` figure
    :param widgets_to_observe:
        The widget to observe if the :param traits_to_observe: has changed.
    :param traits_to_observe:
        The trait from the :param widgets_to_observe: to observe if changed.
        Specify `traitlets.All` to observe all traits.
    :param cued:
        Specifies if it is cued on initialization
    :param show_toolbars:
        Hide toolbars and headers when using in widget mode.
    :param css_style:
        - **base**: the css style of the box during initialization
        - **cue**: the css style that is added when :param
          traits_to_observe: in widget :param widgets_to_observe: changes.
          It is supposed to change the style of the box such that the user has a visual
          cue that :param widget_to_cue: has changed.
    """

    def __init__(
        self,
        figure: Figure,
        widgets_to_observe: Union[None, List[Widget], Widget] = None,
        traits_to_observe: Union[
            None, str, Sentinel, List[Union[str, Sentinel, List[str]]]
        ] = None,
        cued: bool = True,
        show_toolbars: bool = False,
        css_style: Optional[dict] = None,
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
        self.figure = figure

        if matplotlib.backends.backend in [
            "module://matplotlib_inline.backend_inline",
            "macosx",
            "agg",
        ]:
            # we close the figure so the figure is only contained in this widget
            # and not shown using plt.show()
            plt.close(self.figure)
        elif (
            matplotlib.backends.backend == "module://ipympl.backend_nbagg"
            or matplotlib.backends.backend == "widget"
        ):
            # jupyter lab 3 uses "module://ipympl.backend_nbagg"
            # jupyter lab 4 uses "widget"
            with self:
                self.figure.canvas.show()
        else:
            raise NotImplementedError(
                f"matplotlib backend {matplotlib.backends.backend!r} not supported. "
                "Please change backend to 'widget' by running `%matplotlib widget` "
                "that should be supported on all systems."
            )

        if show_toolbars:
            # hides unnecessary elements shown with %matplotlib widget
            self.figure.canvas.header_visible = False
            self.figure.canvas.footer_visible = False
            self.figure.canvas.toolbar_visible = False
            self.figure.canvas.resizable = False

        self.draw_display()

    def clear_display(self, wait=False):
        """
        :param wait:
            same meaning as for the `wait` parameter in the `ipywidgets.clear_output`
            function
        """
        if matplotlib.backends.backend in [
            "module://matplotlib_inline.backend_inline",
            "macosx",
            "agg",
        ]:
            self.clear_figure()
            self.clear_output(wait=wait)
        elif (
            matplotlib.backends.backend == "module://ipympl.backend_nbagg"
            or matplotlib.backends.backend == "widget"
        ):
            # jupyter lab 3 uses "module://ipympl.backend_nbagg"
            # jupyter lab 4 uses "widget"
            self.clear_figure()
            if not (wait):
                self.figure.canvas.draw_idle()
                self.figure.canvas.flush_events()
        else:
            raise NotImplementedError(
                f"matplotlib backend {matplotlib.backends.backend!r} not supported. "
                "Please change backend to 'widget' by running `%matplotlib widget` "
                "that should be supported on all systems."
            )

    def draw_display(self):
        """
        Enforces redrawing the figure
        """
        if matplotlib.backends.backend in [
            "module://matplotlib_inline.backend_inline",
            "macosx",
            "agg",
        ]:
            with self:
                display(self.figure)
        elif (
            matplotlib.backends.backend == "module://ipympl.backend_nbagg"
            or matplotlib.backends.backend == "widget"
        ):
            # jupyter lab 3 uses "module://ipympl.backend_nbagg"
            # jupyter lab 4 uses "widget"
            self.figure.canvas.draw_idle()
            self.figure.canvas.flush_events()
        else:
            raise NotImplementedError(
                f"matplotlib backend {matplotlib.backends.backend!r} not supported. "
                "Please change backend to 'widget' by running `%matplotlib widget` "
                "that should be supported on all systems."
            )

    def clear_figure(self):
        """
        Clears the figure while retaining axes as figure.clear() removes the axes
        sometimes.
        """
        for ax in self.figure.get_axes():
            if ax.has_data() or len(ax.artists) > 0:
                ax.clear()
