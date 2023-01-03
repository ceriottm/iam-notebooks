import warnings

import os
import sys
import traitlets
import numpy as np
import json 

import traitlets

from collections.abc import Iterable
import IPython
import ipywidgets
# TODO remove unecessary imports
from ipywidgets import (
    Output,
    FloatSlider,
    IntSlider,
    Box,
    HBox,
    VBox,
    Layout,
    Checkbox,
    Dropdown,
    Button,
    HTML,
    Text,
    Textarea,
    Label,
    Image,
)

from ._answer import Answer
from ._utils import CodeDemoStatus
from ._code_visualizer import CodeVisualizer

with open(os.path.join(os.path.dirname(__file__), 'loading.gif'), 'rb') as file:
    loading_img_byte = file.read()

_FULL_WIDTH = '99%'   # hack to give the code widgets a bit more horizontal breathing space
class LoadingImage(ipywidgets.Image):
    """
    Custom image supporting visual changes depending on status of CodeDemo
    Parameters
    ----------
        code_demo_functionality : str, no default
            Describes to which functionality of the code demo the widget belongs.
            Supported are: "update", "check" "check_update", no default
    """
    def __init__(self, **kwargs):
        if 'code_demo_functionality' not in kwargs:
            raise ValueError(f"Could not initiate {self.__class__.__name__}: no code_demo_functionality was given.")
        self._code_demo_functionality = kwargs.pop('code_demo_functionality')
        self.add_class("scwidget-loading-image")
        super().__init__(**kwargs)

    # for observe
    def set_status_unchecked(self, change=None):
        self.status = CodeDemoStatus.UNCHECKED

    # for observe
    def set_status_out_of_date(self, change=None):
        self.status = CodeDemoStatus.OUT_OF_DATE

    @property
    def status(self):
        return self._status if hasattr(self, "_status") else None

    @status.setter
    def status(self, status):
        # at the moment updating and checking are treated the same way
        # so we can use updating style also for checking
        # this migh however change in the future 
        if status == CodeDemoStatus.UPDATING:
            self.add_class("scwidget-loading-image--updating")
        elif status == CodeDemoStatus.UP_TO_DATE :
            self.remove_class("scwidget-loading-image--updating")
        elif status == CodeDemoStatus.OUT_OF_DATE:
            pass
        elif status == CodeDemoStatus.CHECKING:
            self.add_class("scwidget-loading-image--checking")
        elif status == CodeDemoStatus.CHECKED:
            self.remove_class("scwidget-loading-image--checking")
        elif status == CodeDemoStatus.UNCHECKED:
            pass
        elif not(isinstance(status, CodeDemoStatus)):
            raise ValueError(f"Status {status} is not a CodeDemoStatus.")
        else:
            raise ValueError(f'CodeDemoStatus {status} is not supported by {self.__class__.__name__}.')
        self._status = status

    def set_status(self, status):
        self.status = status

class CodeDemoButton(ipywidgets.Button):
    """
    Custom button supporting visual changes depending on status of CodeDemo
    Parameters
    ----------
        code_demo_functionality : str, no default
            Describes to which functionality of the code demo the widget belongs.
            Supported are: "update", "check" "check_update", no default
    """
    def __init__(self, **kwargs):
        if 'code_demo_functionality' not in kwargs:
            raise ValueError(f"Could not initiate {self.__class__.__name__}: no code_demo_functionality was given.")
        self._code_demo_functionality = kwargs.pop('code_demo_functionality')
        self.add_class("scwidget-button")
        super().__init__(**kwargs)

    @property
    def status(self):
        return self._status if hasattr(self, "_status") else None

    @status.setter
    def status(self, status):
        if self._code_demo_functionality == "update":
            if status == CodeDemoStatus.UPDATING:
                self.disabled = True
                self.remove_class("scwidget-button--out-of-date")
            elif status == CodeDemoStatus.UP_TO_DATE:
                self.disabled = True
                self.remove_class("scwidget-button--out-of-date")
            elif status == CodeDemoStatus.OUT_OF_DATE:
                self.disabled = False
                self.add_class("scwidget-button--out-of-date")
            elif status == CodeDemoStatus.CHECKING or status == CodeDemoStatus.CHECKED or status == CodeDemoStatus.UNCHECKED:
                pass
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by update {__self.__class__.__name__}.')
        elif self._code_demo_functionality == "check":
            if status == CodeDemoStatus.CHECKING:
                self.disabled = True
                self.remove_class("scwidget-button--unchecked")
            elif status == CodeDemoStatus.CHECKED:
                self.disabled = True
                self.description = "Checked!"
                self.remove_class("scwidget-button--unchecked")
            elif status == CodeDemoStatus.UNCHECKED:
                self.description = "Check code"
                self.disabled = False
                self.add_class("scwidget-button--unchecked")
            elif status == CodeDemoStatus.UPDATING or status == CodeDemoStatus.UP_TO_DATE or status == CodeDemoStatus.OUT_OF_DATE:
                pass
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by check {__self.__class__.__name__}.')
        elif self._code_demo_functionality == "check_update":
            if status == CodeDemoStatus.CHECKING or status == CodeDemoStatus.UPDATING:
                self.disabled = True
                self.remove_class("scwidget-button--out-of-date")
            elif status == CodeDemoStatus.CHECKED or status == CodeDemoStatus.UP_TO_DATE:
                self.disabled = True
                self.remove_class("scwidget-button--out-of-date")
            elif status == CodeDemoStatus.UNCHECKED or status == CodeDemoStatus.OUT_OF_DATE:
                self.disabled = False
                self.add_class("scwidget-button--out-of-date")
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by check_update {__self.__class__.__name__}.')
        elif not(isinstance(status, CodeDemoStatus)):
            raise ValueError(f"Status {status} is not a CodeDemoStatus.")
        self._status = status

    def set_status(self, status):
        self.status = status

    # for observe
    def set_status_unchecked(self, change=None):
        self.status = CodeDemoStatus.UNCHECKED

    # for observe
    def set_status_out_of_date(self, change=None):
        self.status = CodeDemoStatus.OUT_OF_DATE

class CodeDemoBox(ipywidgets.Box):
    """
    Custom box supporting visual changes depending on status of CodeDemo
    Parameters
    ----------
        code_demo_functionality : str, no default
            Describes to which functionality of the code demo the widget belongs.
            Supported are: "update", "check" "check_update", no default
    """
    def __init__(self, **kwargs):
        if 'code_demo_functionality' not in kwargs:
            raise ValueError("Could not initiate CodeDemoButton: no code_demo_functionality was given")
        self._code_demo_functionality = kwargs.pop('code_demo_functionality')
        self.add_class("scwidget-box")
        super().__init__(**kwargs)

    # for observe
    def set_status_unchecked(self, change=None):
        self.status = CodeDemoStatus.UNCHECKED

    # for observe
    def set_status_out_of_date(self, change=None):
        self.status = CodeDemoStatus.OUT_OF_DATE

    @property
    def status(self):
        return self._status if hasattr(self, "_status") else None

    @status.setter
    def status(self, status):
        if self._code_demo_functionality == "check":
            if status == CodeDemoStatus.CHECKED:
                self.remove_class("scwidget-box--unchecked")
            elif status == CodeDemoStatus.UNCHECKED:
                self.add_class("scwidget-box--unchecked")
            elif status == CodeDemoStatus.CHECKING:
                self.remove_class("scwidget-box--unchecked")
            elif status == CodeDemoStatus.UPDATING or status == CodeDemoStatus.UP_TO_DATE or status == CodeDemoStatus.OUT_OF_DATE:
                pass
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by check {__self.__class__.__name__}.')
        elif self._code_demo_functionality == "update":
            if status == CodeDemoStatus.UP_TO_DATE:
                self.remove_class("scwidget-box--out-of-date")
            elif status == CodeDemoStatus.OUT_OF_DATE:
                self.add_class("scwidget-box--out-of-date")
            elif status == CodeDemoStatus.UPDATING:
                self.remove_class("scwidget-box--out-of-date")
            elif status == CodeDemoStatus.CHECKING or status == CodeDemoStatus.CHECKED or status == CodeDemoStatus.UNCHECKED:
                pass
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by update {__self.__class__.__name__}.')
        elif self._code_demo_functionality == "check_update":
            if status == CodeDemoStatus.UP_TO_DATE:
                self.remove_class("scwidget-box--out-of-date")
            elif status == CodeDemoStatus.OUT_OF_DATE:
                self.add_class("scwidget-box--out-of-date")
            elif status == CodeDemoStatus.UPDATING:
                self.remove_class("scwidget-box--out-of-date")
            else:
                raise ValueError(f'CodeDemoStatus {status} is not supported by check_update {__self.__class__.__name__}.')
        elif not(isinstance(status, CodeDemoStatus)):
            raise ValueError(f"Status {status} is not a CodeDemoStatus.")
        self._status = status

    def set_status(self, status):
        self.status = status

class CodeDemo(VBox, Answer):
    """
    Widget to demonstrate code interactively in a variety of ways.
    A code demo is in essence a combination of the widgets: one `code_input` + one `input_parameters_box` + one or more `code_visualizer`. Any widget can also be set None and is then not displayed.
    Parameters
    ----------
        code_input : WidgetCodeInput, default=None
            An widget supporting the input of code usually for a student to fill in a solution.
        input_parameters_box : ParametersBox, default=None
        update_visualizers : function, default=None
            It processes the code `code_input` and to updae the `visualizers`. The `update_visualizers` function is assumed to support the signature
            def update_visualizers(*input_parameters_box.parameters, code_input if not None, visualizers if not None)
        visualizers : Iterable of Widgets or Widget, default=None
            Any kind of widget that can be displayed. Optionally the visualizer has a `before_visualizers_update` and/or a `after_visualizers_update` function which allows set up the visualizer before and after the `update_visualizers` function is executed
        code_checker : CodeChecker
            It handles the correctness check of the code in `code_input`.
        merge_check_and_update_buttons: bool, default=True
            It handles the correctness check of the code in `code_input`.
    """

    def __init__(
        self,
        code_input=None,
        input_parameters_box=None,
        visualizers=None,
        update_visualizers=None,
        check_registry=None,
        merge_check_and_update_buttons=True,
    ):

        self._code_input = code_input
        self._input_parameters_box = input_parameters_box

        if visualizers is not None:
            if not (isinstance(visualizers, Iterable)):
                self._visualizers = [visualizers]
            else:
                self._visualizers = visualizers
        else:
            self._visualizers = []

        self._update_visualizers = update_visualizers
        self._check_registry = check_registry
        if self._check_registry is not None:
            self._check_registry.register_checks(self)

        self._merge_check_and_update_buttons = merge_check_and_update_buttons

        if self._code_input != None:
            self._code_input.observe(self.set_status_not_saved,"function_body")
        # TODO should this be mentioned to the user?
        # if len(self._visualizers) == 0 and self._update_visualizers is not None:
        #    warnings.warn("self._update_visualizers is given without visualizers.")
        if len(self._visualizers) > 0 and self._update_visualizers is None:
            raise ValueError(
                "Non-empty not None `visualizers` are given but without a `update_visualizers` function. The `visualizers` are used by the code demo"
            )
        self._error_output = Output(layout=Layout(width="100%", height="100%"))

        ### create check and update button BEGIN
        if self.has_check_button() and self.has_update_button():
            if not self._merge_check_and_update_buttons:
                self._check_button = CodeDemoButton(code_demo_functionality="check",
                        description="Check code",
                        tooltip="Checks the correctness of the code",
                        layout=Layout(width="200px", height="100%"))
                self._check_button.on_click(self.check)
                self._check_button.set_status(CodeDemoStatus.UNCHECKED)
                self._update_button = CodeDemoButton(code_demo_functionality="update",
                        description="Rerun code and update",
                        tooltip="Reruns the code and updates the visualizers",
                        layout=Layout(width="200px", height="100%"))
                self._update_button.on_click(self.update)
                self._update_button.set_status(CodeDemoStatus.OUT_OF_DATE)
                self._demo_button_box = HBox([self._check_button, self._update_button])
            else:
                if self._code_input is not None:
                    button_description = 'Check code and update'
                    button_tooltip = 'Checks the correctness of the code and updates the visualizers'
                else:
                    button_description = 'Update'
                    button_tooltip = 'Updates the visualizers'
                check_and_update_button = CodeDemoButton(code_demo_functionality="check_update",
                        description=button_description,
                        tooltip=button_tooltip,
                        layout=Layout(width="250px", height="100%"))
                check_and_update_button.on_click(self.check_and_update)
                self._update_button = check_and_update_button
                self._check_button = check_and_update_button
                # TODO check if making a merged status is not a better idea
                check_and_update_button.set_status(CodeDemoStatus.UNCHECKED)
                check_and_update_button.set_status(CodeDemoStatus.OUT_OF_DATE)
                self._demo_button_box = HBox([check_and_update_button])
        elif not (self.has_check_button()) and self.has_update_button():
            if self._code_input is not None:
                button_description =  'Rerun code and Update'
                button_tooltip = 'Reruns the code and updates the visualizers'
            else:
                button_description =  'Update'
                button_tooltip = 'Updates the visualizers'
            self._update_button = CodeDemoButton(code_demo_functionality="update",
                    description=button_description,
                    tooltip=button_tooltip,
                    layout=Layout(width="200px", height="100%"))
            self._update_button.on_click(self.update)
            self._update_button.set_status(CodeDemoStatus.OUT_OF_DATE)
            self._demo_button_box = HBox([self._update_button])
        elif self.has_check_button() and not (self.has_update_button()):
            self._check_button = CodeDemoButton(code_demo_functionality="check",
                    description="Check code",
                    tooltip="Checks the correctness of the code",
                    layout=Layout(width="200px", height="100%"))
            self._check_button.on_click(self.check)
            self._check_button.set_status(CodeDemoStatus.UNCHECKED)
            self._demo_button_box = HBox([self._check_button])
        else:
            self._demo_button_box = HBox([])
        ### create check and update button END

        if self.has_check_functionality() or self.has_update_functionality():
            global loading_img_byte
            # TODO this is a quickfix, because I dont understand why the size of the image
            #      changes when a Button, part of issue #10
            if (self.update_button is not None) or (self.check_button is not None):
                width = "5%"
            else:
                width = "10%"
            self._loading_img = LoadingImage(code_demo_functionality='check_update',
                layout=Layout(width=width, height=width),
                value=loading_img_byte,
            format='gif')
            if self.has_check_functionality():
                self._loading_img.set_status(CodeDemoStatus.UNCHECKED)
            if self.has_update_functionality():
                self._loading_img.set_status(CodeDemoStatus.OUT_OF_DATE)
            self._demo_button_box.children += (self._loading_img, )

        self._validation_text = HTML(value="", layout=Layout(width="100%", height="100%"))

        self._error_output = Output(layout=Layout(width="100%", height="100%"))

        ### create visual cues BEGIN
        self._update_visual_cues = {}
        self._check_visual_cues = {}

        if self.has_check_functionality() and self._code_input is not None:
            self._check_visual_cues['code_input'] = CodeDemoBox(code_demo_functionality="check")
            self._check_visual_cues['code_input'].set_status(CodeDemoStatus.UNCHECKED)

        if self.has_update_functionality():
            if self._code_input is not None:
                self._update_visual_cues['code_input'] = CodeDemoBox(code_demo_functionality="update")
                self._update_visual_cues['code_input'].set_status(CodeDemoStatus.OUT_OF_DATE)
            if self._input_parameters_box is not None:
                # _controls needs do be 
                #self._input_parameters_box._controls.values():
                for control_id, _ in self._input_parameters_box.controls.items():
                    self._update_visual_cues[f'parameter_box_{control_id}'] = CodeDemoBox(code_demo_functionality="update")
                    self._update_visual_cues[f'parameter_box_{control_id}'].set_status(CodeDemoStatus.UNCHECKED)
            if len(self._visualizers) > 0:
                self._update_visual_cues['visualizers'] = CodeDemoBox(code_demo_functionality="update")
                self._update_visual_cues['visualizers'].set_status(CodeDemoStatus.OUT_OF_DATE)
        ### create visual cues END

        demo_widgets = []
        if self._code_input is not None:
            # TODO rm as widget code input changes
            self._code_input.code_theme = 'default'
            code_input_panel = []
            if self.has_check_functionality():
                self._code_input.observe(
                        self.set_status_unchecked, "function_body")
                self._code_input.observe(
                        self._check_visual_cues['code_input'].set_status_unchecked, "function_body")
                self._code_input.observe(
                        self._check_visual_cues['code_input'].set_status_unchecked, "function_body")
                self._code_input.observe(
                        self.check_button.set_status_unchecked, "function_body")
                self._code_input.observe(
                        self._loading_img.set_status_unchecked, "function_body")
                code_input_panel.append(self._check_visual_cues['code_input'])

            if self.has_update_functionality():
                #self._code_input.observe(
                #        self.set_status_out_of_date, "function_body")
                self._code_input.observe(
                        self._update_visual_cues['code_input'].set_status_out_of_date, "function_body")
                self._code_input.observe(
                        self._loading_img.set_status_out_of_date, "function_body")
                if self.update_button is not None:
                    self._code_input.observe(
                            self.update_button.set_status_out_of_date, "function_body")
                if len(self._visualizers) > 0:
                    self._code_input.observe(
                            self._update_visual_cues['visualizers'].set_status_out_of_date, "function_body")
                code_input_panel.append(self._update_visual_cues['code_input'])

            code_input_panel.append(VBox([self._code_input], layout=Layout(width=_FULL_WIDTH, height='auto')))
            demo_widgets.append(HBox(code_input_panel, layout=Layout(margin='0 0 20px 0')))

        if self._input_parameters_box is not None:
            if self.has_update_functionality():
                for control_id, control in self._input_parameters_box.controls.items():
                    control.observe(
                            self._update_visual_cues[f'parameter_box_{control_id}'].set_status_out_of_date, "value")
                    if len(self._visualizers) > 0:
                        control.observe(
                                self._update_visual_cues['visualizers'].set_status_out_of_date, "value")
                    for visualizer in self._visualizers:
                        if isinstance(visualizer,CodeVisualizer): #TODO @Question for Alex : how we make StructureWidgets from chemiscope adhere to the CodeVisualizer interface?
                            control.observe(
                                    visualizer.set_status_out_of_date, "value")
                    if self.update_button is not None:
                        control.observe(
                                self.update_button.set_status_out_of_date, "value")
                    if self._input_parameters_box.refresh_mode != "click":
                        if self.has_check_functionality():
                            control.observe(self.check_and_update, "value")
                        else:
                            control.observe(self.update, "value")
                ### try to erase this and move the logic

            demo_widgets.append(HBox([self._input_parameters_box],
                                    layout=Layout(margin='0 0 20px 0')
                                    ))

        if self.has_check_button():
            self._code_input_button_panel = HBox(
                                    [self._demo_button_box,
                                     self._validation_text],
                                    layout=Layout(align_items="flex-start", width=_FULL_WIDTH,
                                        margin='0 0 20px 0')
                                )
        elif (self.check_button is None) and (self.update_button is not None):
            self._code_input_button_panel = HBox([self._demo_button_box],
                                    layout=Layout(align_items="flex-start", width=_FULL_WIDTH,
                                        margin='0 0 20px 0'))
        else:
            self._code_input_button_panel =  HBox([self._demo_button_box], layout=Layout(align_items="flex-start", width=_FULL_WIDTH))
        demo_widgets.append(self._code_input_button_panel)
        demo_widgets.append(self._error_output)

        if len(self._visualizers) > 0:
            if self.has_update_functionality():
                demo_widgets.append(
                        HBox([self._update_visual_cues['visualizers'],
                        VBox(self._visualizers, layout=Layout(width=_FULL_WIDTH))],
                        layout=Layout(width=_FULL_WIDTH))
                    )
            else:
                demo_widgets.append(HBox([VBox(self._visualizers)]))

        # avoids horizontal scrollbar that tends to appear for no reasons regardless of how much we shrink the widget 
        super().__init__(demo_widgets, layout=Layout(width=_FULL_WIDTH, overflow='hidden auto'))

        # inits answer interface 
        self._save_output = self._error_output # redirects save output to the error area

        # needed for chemiscope, chemiscope does not acknowledge updates of settings
        # until the widget has been displayed
        # TODO why this function does not work "self.on_displayed(self, self.update)"  but this one?
        if self.has_check_functionality():
             if self.check_button is not None:
                 self.check_button.disabled = False
             self.set_status_unchecked()
        if self.has_update_functionality():
            if self.update_button is not None:
                self.update_button.disabled = False
            self.set_status_out_of_date()

    def run_demo(self):
        if self.has_update_functionality():
            self.update()

    def on_click_check_button(self, callback, remove=False):
        if self.check_button is not None:
            self.check_button.on_click(callback, remove)

    def on_click_update_button(self, callback, remove=False):
        if self.update_button is not None:
            self.update_button.on_click(callback, remove)

    @property
    def check_output(self):
        return self._error_output

    def has_update_button(self):
        # used to determine if update button has to be initialized
        # to cover the cases where no code input is used
        return self.has_update_functionality() and (

            self._code_input is not None or self._input_parameters_box is None 
            or self._input_parameters_box.refresh_mode == "click"
        )

    def has_update_functionality(self):
        # if there are visualizers, there is something that must be updated
        return len(self._visualizers) > 0

    def has_check_functionality(self):
        return self._check_registry is not None

    def has_check_button(self):
        return self.has_check_functionality()

    def check_and_update(self, change=None):
        self.check(change)
        self.update(change)

    def check(self, change=None):
        """
        Returns int number of failed checks
        """
        if self.has_check_functionality():
            self.set_check_status(CodeDemoStatus.CHECKING)
        if self._check_registry is None:
            return True
        self._error_output.clear_output()
        self._validation_text.value = ""
        try:
            checks_failed = True
            with self._error_output:
                checks_failed = not(self._check_registry.check_widget_outputs(self))
        except Exception as e:
            checks_failed = True
            with self._error_output:
                raise e
        finally:
            self._validation_text.value = "&nbsp;" * 4
            if checks_failed:
                self._validation_text.value += f"<span style='color:red'> An assert failed.</style>"
            else:
                self._validation_text.value += (
                    f"<span style='color:green'> All asserts passed!</style>"
                )
            # TODO something wrong with loading image when if case is used
            #if self.has_check_functionality() and self._separate_check_and_update_buttons:
            self.set_check_status(CodeDemoStatus.CHECKED)
        return checks_failed

    @property
    def save_button(self):
        return self._save_button

    @property
    def answer_value(self):
        return self.code_input.function_body

    @answer_value.setter
    def answer_value(self, new_answer_value):
        self.code_input.function_body = new_answer_value

    def show_answer_interface(self):
        save_widget = HBox([VBox([VBox([self._save_button,self._load_button])],
                    layout = Layout(display='flex',
                    flex_flow='column',
                    align_items='flex-end',
                    width=_FULL_WIDTH))], layout=Layout(align_items="flex-end", width='95%')
        )
        self._code_input_button_panel.children += (save_widget,)

    @property
    def update_button(self):
        return self._update_button if self.has_update_button() else None

    @property
    def check_button(self):
        return self._check_button if self.has_check_button() else None

    # TODO still a bit twisted if check and update should be splitted
    # or buttons should handle cases where nothing happens?
    # we could merge update and check status
    def set_update_status(self, status):        
        if self.update_button is not None:
            self.update_button.set_status(status)
        for visual_cue in self._update_visual_cues.values():
            visual_cue.set_status(status)
        for visualizer in self._visualizers:
            if isinstance(visualizer,CodeVisualizer): #TODO  @Question for Alex : how we make StructureWidgets from chemiscope adhere to the CodeVisualizer interface?
                visualizer.set_status(status)
        #if self._input_parameters_box is not None:
        #    self._input_parameters_box.set_status(status)
        self._loading_img.set_status(status)

    def set_check_status(self, status):
        # sets the status of all widgets related for checks
        if self.check_button is not None:
            self.check_button.set_status(status)
        for visual_cue in self._check_visual_cues.values():
            visual_cue.set_status(status)
        self._loading_img.set_status(status)

    # for observe
    def set_status_unchecked(self, change=None):
        self._validation_text.value = "&nbsp;" * 4  # clear validation text if it is unchecked
        self.set_check_status(CodeDemoStatus.UNCHECKED)

    # for observe
    def set_status_out_of_date(self, change=None):
        self.set_update_status(CodeDemoStatus.OUT_OF_DATE)

    def update(self, change=None):
        if self.has_update_functionality():
            self.set_update_status(CodeDemoStatus.UPDATING)
        try:
            if self._visualizers is not None:
                for visualizer in self._visualizers:
                    if hasattr(visualizer, "before_visualizers_update"):
                        visualizer.before_visualizers_update()

            if self._update_visualizers is not None:
                # TODO in CodeDemo change signature to
                #example2p3_process(parmeters_kwargs, None, []):

                if self._input_parameters_box is None:
                    parameters = []
                else:
                    parameters = self._input_parameters_box.parameters

                if self._code_input is not None and self._visualizers is not None:
                    self._update_visualizers(
                        *parameters, self._code_input, self._visualizers
                    )
                elif self._code_input is not None and self._visualizers is None:
                    self._update_visualizers(*parameters, self._code_input)
                elif self._code_input is None and self._visualizers is not None:
                    self._update_visualizers(*parameters, self._visualizers)
                else:
                    self._update_visualizers(*parameters)

            if self._visualizers is not None:
                for visualizer in self._visualizers:
                    if hasattr(visualizer, "after_visualizers_update"):
                        visualizer.after_visualizers_update()
        except Exception as e:
            with self._error_output:
                raise e
        finally:
            if self.has_update_functionality():
                self.set_update_status(CodeDemoStatus.UP_TO_DATE)

        if self.has_update_functionality():
            self.set_update_status(CodeDemoStatus.UP_TO_DATE)
        
        # If there is nothing to update for changes, always leave the button clickable
        if self.has_update_button() and self._code_input is None and self._input_parameters_box is None:
            self.update_button.set_status(CodeDemoStatus.OUT_OF_DATE)

         # If there is nothing to update for changes, always leave the button clickable
        if self.has_update_button() and self._code_input is None and self._input_parameters_box is None:
            self.update_button.set_status(CodeDemoStatus.OUT_OF_DATE)
    def compute_output(self, *args, **kwargs):
        # TODO remove function within function
        # For checking we ignore
        if 'suppress_stdout' in kwargs.keys():
            suppress_stdout = kwargs.pop('suppress_stdout')
        else:
            suppress_stdout = False
        suppress_stdout = False
            #if suppress_stdout:
            #    orig_stdout = sys.stdout
            #print(args, kwargs)
            #with ConfigurableOutput(suppress_std_out=False, suppress_std_err=False):
        out = self._code_input.get_function_object()(*args, **kwargs)
            #if suppress_stdout:
            #    sys.stdout = orig_stdout

        return out

    @property
    def code_input(self):
        return self._code_input

    @property
    def input_parameters_box(self):
        return self._input_parameters_box

    @property
    def visualizers(self):
        return self._visualizers

    @property
    def update_visualizers(self):
        return self._update_visualizers

    @update_visualizers.setter
    def update_visualizers(self, new_update_visualizers):
        # is not part of widget, can be setted
        self._update_visualizers = new_update_visualizers

    @property
    def check_registry(self):
        return self._check_registry

    @property
    def merge_check_and_update_buttons(self):
        return self._merge_check_and_update_buttons



# TODO(low) checkbox
class ParametersBox(VBox, Answer):
    """
    Widget to display and control a sequence of parameters.
    
    ----------
        refresh_mode : string, default="auto"
            Options : "auto" (update on slider release), "continuous" (continuous update, as in ipywidgets), "click" (requires button press to update).
            Determines if the visualizers are instantly updated on a parameter change of `input_parameters_box`. 
            If processing the code is computationally demanding, this parameter should be set to "click" for a better user experience. The user then has to manually update by a button click.
    """
    value = traitlets.Dict({}, sync=True)

    def __init__(self, 
                refresh_mode=True, # TODO name should also include check functionality 
                **kwargs):
        # TODO make sure that order of the **kwargs is transparent for the user
        # TODO customization of parameters box 
        # TODO(low) change button logic in order to implement continuous_update without visual cue flickering
        self._refresh_mode = refresh_mode
        if self._refresh_mode == "continuous":
            self.continuous_update = True
        else :
            self.continuous_update = False
        self._controls = {}

        if (self.continuous_update) and (len(kwargs) == 0):
            warnings.warn(
                "refresh_mode is True, but input_parameters_box has no sliders. refresh_mode does not affect anything without parameters. Setting refresh_mode to 'auto'."
            )
            self._refresh_mode = False
        for k, v in kwargs.items():
            if type(v) is tuple:
                if type(v[0]) is float:
                    (
                        val,
                        min,
                        max,
                        step,
                        desc,
                        slargs,
                    ) = ParametersBox.float_make_canonical(k, *v)
                    self._controls[k] = FloatSlider(
                        value=val,
                        min=min,
                        max=max,
                        step=step,
                        description=desc,
                        continuous_update=self.continuous_update,
                        style={"description_width": "initial"},
                        layout=Layout(width="50%", min_width="5in"),
                        **slargs,
                    )
                elif type(v[0]) is int:
                    (
                        val,
                        min,
                        max,
                        step,
                        desc,
                        slargs,
                    ) = ParametersBox.int_make_canonical(k, *v)
                    self._controls[k] = IntSlider(
                        value=val,
                        min=min,
                        max=max,
                        step=step,
                        description=desc,
                        continuous_update=self.continuous_update,
                        style={"description_width": "initial"},
                        layout=Layout(width="50%", min_width="5in"),
                        **slargs,
                    )
                elif type(v[0]) is bool:
                    val, desc, slargs = ParametersBox.bool_make_canonical(k, *v)
                    self._controls[k] = Checkbox(
                        value=val,
                        description=desc,
                        continuous_update=self.continuous_update,
                        style={"description_width": "initial"},
                        layout=Layout(width="50%", min_width="5in"),
                        **slargs,
                    )
                elif type(v[0]) is str:
                    val, desc, options, slargs = ParametersBox.str_make_canonical(k, *v)
                    self._controls[k] = Dropdown(
                        options=options,
                        value=val,
                        description=desc,
                        disabled=False,
                        style={"description_width": "initial"},
                        layout=Layout(width="50%", min_width="5in"),
                    )
                #elif: type(v[0]) is Widget:
                #    # TODO check if widget can be added
                #    pass
                else:
                    raise ValueError("Unsupported parameter type")
            else:
                # assumes an explicit control has been passed
                self._controls[k] = v

        # TODO this causes a warning which I dont understand
        #super().__init__(**kwargs)
        #    object.__init__() takes exactly one argument (the instance to initialize)
        #    This is deprecated in traitlets 4.2.This error will be raised in a future release of traitlets.
        #      super(Widget, self).__init__(**kwargs)
        super().__init__()
        self.children = [control for control in self._controls.values()]
        # links changes to the controls to the value dict
        for k in self._controls:
            self._controls[k].observe(self._parameter_handler(k), "value")
            self.value[k] = self._controls[k].value
    @property
    def refresh_mode(self):
        return self._refresh_mode
    @property
    def status(self):
        return self._status if hasattr(self, "_status") else None

    @status.setter
    def status(self, status):
        if status == CodeDemoStatus.UP_TO_DATE:
            for control_id, control in self.controls.items():
                control.disabled = False
        elif status == CodeDemoStatus.UPDATING:
            for control_id, control in self.controls.items():
                control.disabled = True
        elif status == CodeDemoStatus.OUT_OF_DATE:
            for control_id, control in self.controls.items():
                control.disabled = False
        elif not(isinstance(status, CodeDemoStatus)):
            raise ValueError(f"Status {status} is not a CodeDemoStatus.")
        self._status = status

    @property
    def answer_value(self):
        return json.dumps(self.value)

    @answer_value.setter
    def answer_value(self, new_answer_value):
        new_values = json.loads(new_answer_value)
        for k in new_values:
            self._controls[k].value = new_values[k]

    def set_status(self, status):
        self.status = status

    @property
    def controls(self):
        return self._controls
    def show_answer_interface(self):
        save_widget = HBox([VBox([HBox([self._save_button,self._load_button])])], layout=Layout(align_items="flex-end", width='95%')
        )
        self.children = [control for control in self._controls.values()] + [save_widget]
        stateful_behaviour = [control.observe(self.set_status_not_saved,"value") for control_id, control in self.controls.items()]
        return save_widget
    def _parameter_handler(self, k):
        def _update_parameter(change):
            # traitlets.Dict cannot track updates, only assignment
            dict_copy = self.value.copy()
            dict_copy[k] = self._controls[k].value
            self.value = dict_copy

        return _update_parameter

    @property
    def parameters(self):
        return tuple(self.value.values())

    @staticmethod
    def float_make_canonical(
        key, default, minval=None, maxval=None, step=None, desc=None, slargs=None, *args
    ):
        # gets the (possibly incomplete) options for a float value, and completes as needed
        if minval is None:
            minval = min(default, 0)
        if maxval is None:
            maxval = max(default, 100)
        if step is None:
            step = (maxval - minval) / 100
        if desc is None:
            desc = key
        if slargs is None:
            slargs = {}
        if len(args) > 0:
            raise ValueError("Too many options for a float parameter")
        return default, minval, maxval, step, desc, slargs

    @staticmethod
    def int_make_canonical(
        key, default, minval=None, maxval=None, step=None, desc=None, slargs=None, *args
    ):
        # gets the (possibly incomplete) options for a int value, and completes as needed
        if minval is None:
            minval = min(default, 0)
        if maxval is None:
            maxval = max(default, 10)
        if step is None:
            step = 1
        if desc is None:
            desc = key
        if slargs is None:
            slargs = {}
        if len(args) > 0:
            raise ValueError("Too many options for a int parameter")
        if type(minval) is not int or type(maxval) is not int or type(step) is not int:
            raise ValueError("Float option for an int parameter")
        return default, minval, maxval, step, desc, slargs

    @staticmethod
    def bool_make_canonical(key, default, desc=None, slargs=None, *args):
        # gets the (possibly incomplete) options for a bool value, and completes as needed
        if desc is None:
            desc = key
        if slargs is None:
            slargs = {}
        if len(args) > 0:
            raise ValueError("Too many options for a bool parameter")
        return default, desc, slargs

    @staticmethod
    def str_make_canonical(key, default, options, desc=None, slargs=None):
        if desc is None:
            desc = key
        if slargs is None:
            slargs = {}
        if not (all([type(option) is str for option in options])):
            raise ValueError("Non-str in options")
        return default, desc, options, slargs

class CodeChecker:
    """
    reference_code_parameters : dict
    equality_function : function, default=np.allclose
    """

    def __init__(self, reference_code_parameters, equality_function=None):
        self.reference_code_parameters = reference_code_parameters

        self._equality_function = equality_function
        if self._equality_function is None:
            self._equality_function = np.allclose

    @property
    def equality_function(self):
        return self._equality_function

    @equality_function.setter
    def equality_function(self, new_equality_function):
        self._equality_function = new_equality_function

    @property
    def nb_checks(self):
        return (
            0
            if self.reference_code_parameters is None
            else len(self.reference_code_parameters)
        )

    def check(self, code_input):
        def student_code_wrapper(*args, **kwargs):
            # For checking we ignore
            try:
                orig_stdout = sys.stdout
                out = code_input.get_function_object()(*args, **kwargs)
                sys.stdout = orig_stdout
            except Exception as e:
                sys.stdout = orig_stdout
                # because some errors in code widgets do not print the
                # traceback correctly, we print the last step manually
                tb = sys.exc_info()[2]
                while not (tb.tb_next is None):
                    tb = tb.tb_next
                if tb.tb_frame.f_code.co_name == code_input.function_name:
                    # index = line-1
                    line_number = tb.tb_lineno - 1
                    code = (
                        code_input.function_name
                        + '"""\n'
                        + code_input.docstring
                        + '"""\n'
                        + code_input.function_body
                    ).splitlines()
                    error = f"<widget_code_input.widget_code_input in {code_input.function_name}({code_input.function_parameters})\n"
                    for i in range(
                        max(0, line_number - 2), min(len(code), line_number + 3)
                    ):
                        if i == line_number:
                            error += f"----> {i} {code[i]}\n"
                        else:
                            error += f"      {i} {code[i]}\n"
                    e.args = (str(e.args[0]) + "\n\n" + error,)
                raise e
            return out

        if isinstance(self.reference_code_parameters, dict):
            iterator = self.reference_code_parameters.items()
        # TODO not clear what it is in case not a dict
        else:
            iterator = self.reference_code_parameters

        nb_failed_checks = 0
        for x, y in iterator:
            out = student_code_wrapper(*x)
            nb_failed_checks += int(not (self.equality_function(y, out)))
        return nb_failed_checks
