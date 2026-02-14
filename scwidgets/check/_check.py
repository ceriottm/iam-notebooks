# postpones evaluation of annotations
# see https://stackoverflow.com/a/33533514
from __future__ import annotations

import functools
import inspect
import re
import sys
import types
from copy import deepcopy
from platform import python_version
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import IPython.core.ultratb

from .._utils import Formatter

ExecutionInfo = Tuple[
    Union[None, type],  # BaseException type
    Union[None, BaseException],
    Union[None, TracebackType],
]


class Check:
    """
    A check verifies the correctness of a function for a set of input parameters using
    a list of univariate and bivariate asserts with the option to obscure the reference
    outputs.

    :param function_to_check:
        The function that accepts each input parameters in `input_parameters`
    :param input_parameters:
        A dict or a list of dictionaries each containing the argument name and its value
        as (key, value) pair that is used as input for the function `function_to_check`.
    :param outputs_references:
        A tuple or a list of tuples each containing the expected output of the function
        `function_to_check` for the inputs in the `input_parameters`
    :param asserts:
        A list of assert functions. Each assert function verifies the outputs from
        `function_to_check`. Assert functions can be univariate (accepting only output),
        bivariate (accepting output and reference output), or nullvariate (accepting no
        arguments). If output references have been set, it can take additional output
        references to compare with. If a fingerprint is given, the it is compared while
        assert functions with a single argument are always applied on the output
        parameters.
    :param fingerprint:
        A one-way function that transforms the outputs from `function_to_check`,
        obscuring direct comparisons with the `output_references`.
    :param suppress_fingerprint_asserts:
        Specifies if the assert messages that use the fingerprint function output for
        tests are suppressed. The message might be confusing to a student as the output
        is converted by the fingerprint function.
    :param stop_on_assert_error_raised:
        Specifies if running the asserts is stopped as soon as an error is raised in an
        assert. If a lot of asserts are specified, the printing of a lot of error
        tracebacks might make debugging harder.
    """

    FunInParamT = TypeVar("FunInParamT", bound=Any)
    FunOutParamsT = Tuple[Any, ...]

    FingerprintT = TypeVar("FingerprintT", bound=Any)
    AssertFunT = Union[
        Callable[[FunOutParamsT, FunOutParamsT], str],
        Callable[[FingerprintT, FingerprintT], str],
        Callable[[FunOutParamsT], str],
        Callable[[], str],
    ]

    def __init__(
        self,
        function_to_check: Callable[..., FunOutParamsT],
        asserts: Union[List[AssertFunT], AssertFunT],
        inputs_parameters: Optional[
            Union[List[Dict[str, FunInParamT]], Dict[str, FunInParamT]]
        ] = None,
        outputs_references: Optional[Union[List[tuple], tuple]] = None,
        fingerprint: Optional[
            Callable[[Check.FunOutParamsT], Check.FingerprintT]
        ] = None,
        suppress_fingerprint_asserts: bool = True,
        stop_on_assert_error_raised: bool = True,
    ):
        self._function_to_check = function_to_check
        self._asserts = []
        self._nullvariate_asserts: List[Callable[[], str]] = []
        self._univariate_asserts: List[Callable[[tuple], str]] = []
        self._bivariate_asserts = []
        if not (isinstance(asserts, list)):
            asserts = [asserts]

        for i, assert_f in enumerate(asserts):
            nb_positional_arguments = len(
                [
                    parameters
                    for parameters in inspect.signature(assert_f).parameters.values()
                    if parameters.default is inspect._empty
                ]
            )
            self._asserts.append(assert_f)
            if nb_positional_arguments == 0:
                self._nullvariate_asserts.append(assert_f)  # type: ignore[arg-type]
            elif nb_positional_arguments == 1:
                if inputs_parameters is None:
                    raise ValueError(
                        "For functions taking two input arguments we need "
                        "inputs_parameters."
                    )
                # type checker cannot infer type change
                self._univariate_asserts.append(assert_f)  # type: ignore[arg-type]
            elif nb_positional_arguments == 2:
                if inputs_parameters is None or outputs_references is None:
                    raise ValueError(
                        "For functions taking two input arguments we need "
                        "inputs_parameters and outputs_references."
                    )
                self._bivariate_asserts.append(assert_f)
            else:
                raise ValueError(
                    f"Only assert function with 1 or 2 positional arguments are allowed"
                    f"but assert function {i} has {nb_positional_arguments} positional"
                    f"arguments"
                )

        # We cannot verify if the number of input argumets match because they can be
        # hidden in **kwargs
        if isinstance(inputs_parameters, dict):
            inputs_parameters = [inputs_parameters]

        if inputs_parameters is not None and outputs_references is not None:
            if isinstance(outputs_references, tuple):
                outputs_references = [outputs_references]
            assert len(inputs_parameters) == len(outputs_references), (
                "Number of inputs_parameters and outputs_references are mismatching: "
                "len inputs parameters != len outputs parameters "
                f"[{len(inputs_parameters)} != {len(outputs_references)}]."
            )

        self._inputs_parameters = [] if inputs_parameters is None else inputs_parameters
        self._outputs_references = (
            [] if outputs_references is None else outputs_references
        )
        self._fingerprint = fingerprint
        self._suppress_fingerprint_asserts = suppress_fingerprint_asserts
        self._stop_on_assert_error_raised = stop_on_assert_error_raised

    @property
    def function_to_check(self) -> Callable[..., FunOutParamsT]:
        return self._function_to_check

    @function_to_check.setter
    def function_to_check(self, function_to_check: Callable[..., FunOutParamsT]):
        self._function_to_check = function_to_check

    @property
    def fingerprint(self):
        return deepcopy(self._fingerprint)

    @property
    def asserts(self):
        return deepcopy(self._asserts)

    @property
    def nullvariate_asserts(self):
        return deepcopy(self._nullvariate_asserts)

    @property
    def univariate_asserts(self):
        return deepcopy(self._univariate_asserts)

    @property
    def bivariate_asserts(self):
        return deepcopy(self._bivariate_asserts)

    @property
    def inputs_parameters(self):
        return deepcopy(self._inputs_parameters)

    @property
    def outputs_references(self):
        return deepcopy(self._outputs_references)

    @property
    def nb_conducted_asserts(self):
        return len(self._asserts) * len(self._inputs_parameters) + len(
            self._nullvariate_asserts
        )

    def compute_outputs(self):
        outputs = []
        for input_parameters in self._inputs_parameters:
            output = self._function_to_check(**input_parameters)
            if not (isinstance(output, tuple)):
                output = (output,)
            if self._fingerprint is not None:
                output = self._fingerprint(*output)
                if not (isinstance(output, tuple)):
                    output = (output,)
            outputs.append(output)
        return outputs

    def compute_and_set_references(self):
        self._outputs_references = self.compute_outputs()

    def check_function(self) -> CheckResult:
        """
        For each input (first depth list) returns the result message for each assert
        (second depth list).  If a result message is empty, the assert was successful,
        otherwise it contains information about the failure.
        """
        if len(self._bivariate_asserts) > 0:
            if self._outputs_references is None:
                raise ValueError(
                    "outputs_references are None but asserts exist that require "
                    "outputs_references (second positional argument)"
                )
            assert len(self._inputs_parameters) == len(self._outputs_references), (
                "Number of inputs and reference outputs "
                "are mismatching: len inputs parameters != len outputs parameters "
                f"[{len(self._inputs_parameters)} != {len(self._outputs_references)}]."
            )

        check_result = CheckResult()

        for assert_f in self._nullvariate_asserts:
            try:
                assert_result = assert_f()
                check_result.append(assert_result, assert_f, {})
            except Exception:
                excution_info = sys.exc_info()
                check_result.append(excution_info, assert_f, {})
                if self._stop_on_assert_error_raised:
                    return check_result

        for i, input_parameters in enumerate(self._inputs_parameters):
            output = self._function_to_check(**input_parameters)
            if not (isinstance(output, tuple)):
                output = (output,)

            for uni_assert_f in self._univariate_asserts:
                try:
                    assert_result = uni_assert_f(output)
                    check_result.append(assert_result, uni_assert_f, input_parameters)
                except Exception:
                    excution_info = sys.exc_info()
                    check_result.append(excution_info, uni_assert_f, input_parameters)
                    if self._stop_on_assert_error_raised:
                        return check_result

            if self._fingerprint is not None:
                try:
                    output = self._fingerprint(*output)
                except (  # we do not raise here since it is passed to widget output # noqa B040
                    Exception
                ) as exception:
                    if python_version() >= "3.11":
                        exception.add_note(
                            "An error was raised in fingerprint function, "
                            " most likely because your output type is wrong."
                        )
                    excution_info = sys.exc_info()
                    check_result.append(
                        excution_info, self._fingerprint, input_parameters
                    )
                    return check_result

                if not (isinstance(output, tuple)):
                    output = (output,)

            for assert_f in self._bivariate_asserts:  # type: ignore[assignment]
                assert len(output) == len(
                    self._outputs_references[i]  # type: ignore[index]
                ), (
                    "Number of output parameters and reference output parameters "
                    "are mismatching: "
                    "len output parameters != len outputs references "
                    f"[{len(output)} != "
                    f"{len(self._outputs_references[i])}]."  # type: ignore[index]
                )

                try:
                    assert_result = assert_f(
                        output,
                        self._outputs_references[i],  # type: ignore[index, call-arg]
                    )
                except Exception:
                    excution_info = sys.exc_info()
                    check_result.append(excution_info, assert_f, input_parameters)
                    if self._stop_on_assert_error_raised:
                        return check_result
                check_result.append(
                    assert_result,
                    assert_f,
                    input_parameters,
                    self._suppress_fingerprint_asserts
                    and self._fingerprint is not None,
                )

        return check_result


class CheckResult:
    """
    Represents the result of a check, storing information about the assert results,
    assert names, input parameters, and suppressed assert messages.
    """

    def __init__(self):
        self._assert_results = []
        self._assert_names = []
        self._inputs_parameters = []
        self._suppress_assert_messages = []

    def append(
        self,
        assert_result: Union[str, AssertResult, ExecutionInfo],
        assert_f: Optional[Check.AssertFunT] = None,
        input_parameters: Optional[dict] = None,
        suppress_assert_message: Optional[bool] = False,
    ):
        self._assert_results.append(assert_result)
        if isinstance(assert_result, AssertResult):
            self._assert_names.append(assert_result.assert_name)
        else:
            self._assert_names.append(self._get_name_from_assert(assert_f))

        self._inputs_parameters.append(input_parameters)
        self._suppress_assert_messages.append(suppress_assert_message)

    @property
    def successful(self):
        return (
            len(
                [
                    result
                    for result in self._assert_results
                    if (isinstance(result, str) and result != "")
                    or (isinstance(result, AssertResult) and not (result.successful))
                ]
            )
            == 0
        )

    def message(self) -> str:
        messages = []
        for i, result in enumerate(self._assert_results):
            if (isinstance(result, str) and result == "") or (
                isinstance(result, AssertResult) and result.successful
            ):
                message = Formatter.color_assert_success(
                    f"{self._assert_names[i]} passed",
                )
                if len(self._inputs_parameters[i]) > 0:
                    message += Formatter.color_assert_success(" for input\n")

                input_parameters_message = "\n".join(
                    [
                        f"  {Formatter.color_assert_info(param_name)}:  "
                        f"{param_value!r}"
                        for param_name, param_value in self._inputs_parameters[
                            i
                        ].items()
                    ]
                )
                if input_parameters_message != "":
                    message += input_parameters_message
            else:
                message = Formatter.color_assert_failed(
                    f"{self._assert_names[i]} failed",
                )
                if len(self._inputs_parameters[i]) > 0 or not (
                    self._suppress_assert_messages[i]
                ):
                    message += Formatter.color_assert_failed(" for\n")

                input_parameters_message = "\n".join(
                    [
                        f"  {Formatter.color_assert_info(param_name)}: "
                        f"{param_value!r}"
                        for param_name, param_value in self._inputs_parameters[
                            i
                        ].items()
                    ]
                )
                assert_message = ""
                if input_parameters_message != "":
                    assert_message += input_parameters_message

                assert_result = ""
                if isinstance(result, tuple) and len(result) == 3:
                    # Execution info
                    tb = IPython.core.ultratb.VerboseTB()
                    assert_result = tb.text(*result)
                elif not (self._suppress_assert_messages[i]):
                    if hasattr(result, "message"):
                        assert_result = f"{result.message()}"
                    else:
                        assert_result = f"{Formatter.color_assert_failed(result)}"
                if assert_result != "":
                    assert_message += "\n" + assert_result
                if assert_message != "":
                    # adds "| " to the beginning of each line
                    assert_message = re.sub(
                        r"(^)",
                        r"\1" + f"{Formatter.color_assert_failed('|')} ",
                        assert_message,
                        flags=re.M,
                    )
                message += f"{assert_message}"
            messages.append(message)

        return "\n".join(messages)

    def _get_name_from_assert(self, assert_f: Any) -> str:
        if isinstance(assert_f, types.FunctionType):
            return assert_f.__name__
        elif isinstance(assert_f, functools.partial):
            return assert_f.func.__name__
        else:
            return str(assert_f)

    @property
    def assert_results(self):
        return deepcopy(self._assert_results)

    @property
    def assert_names(self):
        return deepcopy(self._assert_names)

    @property
    def inputs_parameters(self):
        return deepcopy(self._inputs_parameters)


class AssertResult:
    """
    Represents the result of an assertion check, storing information about
    the assertion name, parameter indices, parameter values, and messages.
    If any of `parameter_indices`, `parameter_values`, or `messages` is a list,
    then all must be lists of the same length.

    :param assert_name:
        The name of the assertion being checked.
    :param parameter_indices:
        The index or indices of the parameters that were evaluated in the assertion.
        If a single index is provided, it will be converted into a list.
    :param parameter_values:
        The value(s) of the parameters at the given indices that were checked in the
        assertion. If a single value is provided, it will be converted into a list.
    :param messages:
        A message or list of messages describing the assertion result for each parameter
        index. If a single message is provided, it will be converted into a list.
    """

    def __init__(
        self,
        assert_name: str,
        parameter_indices: Union[int, List[int]],
        parameter_values: Union[Any, List[Any]],
        messages: Union[str, List[str]],
    ):
        self._assert_name = assert_name

        # we do not include parameter_values in the check because it can be a list
        # by type definition
        if isinstance(parameter_indices, list) or isinstance(messages, list):
            if (
                not (isinstance(parameter_indices, list))
                or not (isinstance(parameter_values, list))
                or not (isinstance(messages, list))
            ):
                raise ValueError(
                    "If one of the inputs parameter_indices, parameter_values or "
                    "messages is a list, then all must be lists of the same size."
                )
            elif len(parameter_indices) != len(parameter_values) or len(
                parameter_indices
            ) != len(messages):
                raise ValueError(
                    "If one of the inputs parameter_indices, parameter_values or "
                    "messages is a list, then all must be lists of the same size, "
                    "but got len(parameter_indices), len(parameter_values), "
                    f"len(messages) [{len(parameter_indices)}, "
                    f"{len(parameter_values)}, {len(messages)}]"
                )
        if not (isinstance(parameter_indices, list)):
            parameter_indices = [parameter_indices]
        self._parameter_indices = parameter_indices

        if not (isinstance(parameter_values, list)):
            parameter_values = [parameter_values]
        self._parameter_values = parameter_values

        if not (isinstance(messages, list)):
            messages = [messages]
        self._messages = messages

    def message(self) -> str:
        message = ""
        for i in range(len(self._parameter_indices)):
            message += (
                Formatter.color_assert_info(f"> output {self._parameter_indices[i]}: ")
                + f"{self._parameter_values[i]}\n"
                + Formatter.color_assert_failed(self._messages[i])
            )
        return message

    @property
    def assert_name(self) -> str:
        return self._assert_name

    @property
    def successful(self):
        return len(self._parameter_indices) == 0
