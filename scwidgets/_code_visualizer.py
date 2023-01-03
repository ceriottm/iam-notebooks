import matplotlib.pyplot as plt

from ipywidgets import Output

from IPython.display import display

from ._utils import CodeDemoStatus

class CodeVisualizer:
    """CodeDemo supports this interface to execute code before and after the update of the visualizers. It does not inherit from ABC, because then it would conflict with the inheritence of widgets.
    """
    def __init__(self):
        self.add_class("scwidget-visualizer")

    def before_visualizers_update(self):
        raise NotImplementedError("before_visualizers_update has not been implemented.")

    def after_visualizers_update(self):
        raise NotImplementedError("after_visualizers_update has not been implemented.")

    @property
    def status(self):
        return self._status if hasattr(self, "_status") else None

    @status.setter
    def status(self, status):
        if status == CodeDemoStatus.UP_TO_DATE:
            self.remove_class("scwidget-visualizer--out-of-date")
        elif status == CodeDemoStatus.OUT_OF_DATE:
            self.add_class("scwidget-visualizer--out-of-date")
        elif status == CodeDemoStatus.UPDATING:
            self.remove_class("scwidget-visualizer--out-of-date")
        elif not(isinstance(status, CodeDemoStatus)):
            raise ValueError(f"Status {status} is not a CodeDemoStatus.")
        else:
            raise ValueError(f'CodeDemoStatus {status} is not supported by code visualizer {self.__class__.__name__}.')
        self._status = status

    def set_status(self, status):
        self.status = status

    # for observe
    def set_status_unchecked(self, change=None):
        self.status = CodeDemoStatus.UNCHECKED

    # for observe
    def set_status_out_of_date(self, change=None):
        self.status = CodeDemoStatus.OUT_OF_DATE

class PyplotOutput(Output, CodeVisualizer):
    """VBox"""

    # should be figure kwargs? https://stackoverflow.com/a/14770951
    def __init__(self, figure, **kwargs):
        super().__init__(**kwargs)

        self.figure = figure
        self.figure.canvas.toolbar_visible = "fade-in-fade-out"
        self.figure.canvas.toolbar_position = "right"
        self.figure.canvas.header_visible = False
        self.figure.canvas.footer_visible = False
        with self:
            # self.figure.canvas.show() does not work, dont understand
            # self.figure.show()
            plt.show(self.figure.canvas)

    def before_visualizers_update(self):
        for ax in self.figure.get_axes():
            if ax.has_data() or len(ax.artists) > 0:
                ax.clear()

    def after_visualizers_update(self):
        pass


class AnimationOutput(Output, CodeVisualizer):
    def __init__(self, figure):
        super().__init__()
        self.figure = figure
        self.animation = None
    
    @property
    def figure(self):
        return self._figure

    @figure.setter
    def figure(self, new_figure):
        new_figure.canvas.toolbar_visible = True
        new_figure.canvas.header_visible = False
        new_figure.canvas.footer_visible = False
        plt.close(new_figure)
        self._figure = new_figure
    
    def before_visualizers_update(self):
        self.clear_output()
        for ax in self.figure.get_axes():
            if ax.has_data() or len(ax.artists) > 0:
                ax.clear()

    def after_visualizers_update(self):
        if self.animation is None:
            return

        with self:
            display(self.animation)        

class ClearedOutput(Output, CodeVisualizer):
    """Mini-wrapper for Output to provide an output space that gets cleared when it is updated e.g. to print some output or reload a widget."""

    def __init__(self):
        super().__init__()

    def before_visualizers_update(self):
        self.clear_output()

    def after_visualizers_update(self):
        pass
