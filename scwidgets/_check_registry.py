import functools
import ipywidgets
import numpy as np
from copy import deepcopy

class CheckRegistry:
    def __init__(self):
        self._checks = {}

    def register_checks(self, widget):
        """initialize checks, if checks exist then it resets them"""
        self._checks[widget] = []

    def add_check(self, widget, inputs_parameters, reference_outputs=None, custom_asserts=None, fingerprint=None, equal=None):
        check = Check(widget, inputs_parameters, reference_outputs, custom_asserts, fingerprint, equal)
        self._checks[widget].append(check)

    def compute_and_set_reference_outputs(self, widget, change=None):
        for check in self._checks[widget]:
            check.compute_and_set_reference_outputs()

    def print_reference_outputs(self, widget, ignore_errors=False):
        try:
            for i, check in enumerate(self._checks[widget]):
                print(f"Check {i}:\n{[reference_output for reference_output in check.compute_reference_outputs()]}")
        except: 
            if ignore_errors:
                pass
            else:
                raise 

    def print_widget_outputs(self, widget, widget_output_to_str=None):
        if widget_output_to_str is None:
            widget_output_to_str  = lambda x: str(x)
        # patching the __repr__ does not work work
        class ChangePrintBehaviour:
            def __init__(self, obj):
                self._obj = obj
            def __repr__(self):
                return widget_output_to_str(self._obj)
        for i, check in enumerate(self._checks[widget]):
            print(f"Check {i}:\n{[ChangePrintBehaviour(widget_output) for widget_output in check.compute_widget_outputs()]}")

    def check_widget_outputs(self, widget, change=None):
        check_successes = []
        for check in self._checks[widget]:
            check_successes.append( check.check_widget_outputs() )
        return all(check_successes)

class Check:
    """
    A check is collection of asserts with the same configuration.

    The widget must have a `compute_output` function with all arguments named.

    inputs_parameters: list of dict,
        the dict contains the named arguments used with compute_output
    reference_outputs: list of outputs,
        each entry is one output of the the compute_output function of the widget
    custom_assert : function
        can raise assert errors
    fingerprint : function,
        is applied on widget_output to get a fingerprint
        a fingerprint is a numpy array, a tuple of numpy arrays, a  serializable
    equal : function
        returns boolean


    workflow with fingerprint function:
        widget_output = widget.compute_output(**input)
        custom_assert(widget_output, fingerprint_of_reference_output) -> can raise assertion errors   [if not None]
        fingerprint_widget_output  = fingerprint(widget_output)
        assert equal(fingerprint_of_widget_output, fingerprint_of_reference_output)  [if not None]

    workflow without fingerprint function (if it is None):
        widget_output = widget.compute_output(**input)
        assert isinstance(widget_output, reference_output)
        assert widget_output.shape == reference_output.shape [if has shape]
        assert len(widget_output) == len(reference_output) [if has len but not shape]
        custom_assert(widget_output, reference_output) -> can raise assertion errors   [if not None]
        assert equal(widget_output, reference_output) [if not None]
    """
    def __init__(self, widget, inputs_parameters, reference_outputs=None, custom_asserts=None, fingerprint=None, equal=None):
        if not(hasattr(widget, "compute_output")):
            raise ValueError("Widget does not have function with name 'compute_and_set_reference_outputs', which is needed to produce refeference outputs.")

        if reference_outputs is not None and len(reference_outputs) != len(inputs_parameters):
            raise ValueError(f"Number of inputs and outputs must be the same: len(inputs_parameters) != len(reference_outputs) ({len(inputs_parameters)} != {len(reference_outputs)})")

        self._widget = widget
        self._inputs_parameters = inputs_parameters
        self._reference_outputs = reference_outputs
        self._custom_asserts = custom_asserts
        self._fingerprint = fingerprint
        self._equal = equal

    @property
    def fingerprint(self):
        return self._fingerprint

    def compute_and_set_reference_outputs(self):
        self._reference_outputs = self.compute_reference_outputs()

    def compute_reference_outputs(self):
        reference_outputs = []
        for input_parameters in self._inputs_parameters:
            try:
                reference_output = self._widget.compute_output(**input_parameters)
            except Exception as e:
                raise e
            if self._fingerprint is not None:
                reference_output = self._fingerprint(reference_output)
            reference_outputs.append(reference_output)
        return reference_outputs

    def compute_widget_outputs(self):
        widget_outputs = []
        for input_parameters in self._inputs_parameters:
            try:
                widget_output = self._widget.compute_output(**input_parameters)
            except Exception as e:
                raise e
            widget_outputs.append(widget_output)
        return widget_outputs

    def check_widget_outputs(self):
        if self._reference_outputs is None:
            raise ValueError("Reference outputs are None. Please first run comppute_and_set_reference_outputs or specify reference_outputs on initialization.")
        assert len(self._inputs_parameters) == len(self._reference_outputs), "number of inputs and reference outputs mismatching. Something went wrong in setting reference outputs"
        for i in range(len(self._reference_outputs)):
            # requires deepcopy because test might change input
            output = self._widget.compute_output(**deepcopy(self._inputs_parameters[i]))

            if self._fingerprint is None:
                #numeric = [int, float, np.floating ]
                #if not(isinstance(output, type(self._reference_outputs[i]))):
                #    # Type mismatches between built-in (except complex) and numpy numeric types should be ignored.
                #    if not type(output) in numeric:
                #        print(f"TypeAssert failed: Expected type {type(self._reference_outputs[i])} but got {type(output)}.")
                #        return False
                if hasattr(self._reference_outputs[i], "shape") and (output.shape != self._reference_outputs[i].shape):
                    print(f"ShapeAssert failed: Expected shape {self._reference_outputs[i].shape} but got {output.shape}.")
                    return False
                elif hasattr(self._reference_outputs[i], "__len__") and (len(output) != len(self._reference_outputs[i])):
                    print(f"LenAssert failed: Expected len {self._reference_outputs[i]} but got {len(output)}.")
                    return False

            if self._custom_asserts is not None:
                try:
                    self._custom_asserts(output, self._reference_outputs[i])
                except AssertionError as e:
                    print(f"Assert failed: {e}")
                    return False

            if self._fingerprint is not None:
                output = self._fingerprint(output)

            if (self._equal is not None) and \
                    not(self._equal(output, self._reference_outputs[i])):
                if self._fingerprint is None:
                    print(f"EqualAssert failed: Expected {self._reference_outputs[i]} but got {output}.")
                else:
                    print(f"EqualAssert failed.")
                return False
        return True
