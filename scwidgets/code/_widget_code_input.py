import ast
import copy
import inspect
import re
import sys
import textwrap
import traceback
import types
import warnings
from functools import wraps
from typing import Any, List, Optional, Tuple, Union

from widget_code_input import WidgetCodeInput
from widget_code_input.utils import (
    CodeValidationError,
    format_syntax_error_msg,
    is_valid_variable_name,
)

from ..check import Check


class CodeInput(WidgetCodeInput):
    """
    Small wrapper around WidgetCodeInput that controls the output

    :param function:
        A Python function to be parse automatically. Note that the parsing
        may alter the original formatting or lose certain syntactical nuances. If this
        behavior is undesired, provide the function explicitly using other parameters.
    :param function_name: The name of the function
    :param function_paramaters: The parameters as a continuous string as specified in
        the signature of the function. e.g  for `foo(x, y = 5)` it should be
        `"x, y = 5"`
    :param docstring: The docstring of the function
    :param function_body: The function definition without indentation
    :param builtins: A dictionary containing variable names and values that are added
        to the globals __builtins__ and thus available on initialization
    """

    valid_code_themes = ["nord", "solarizedLight", "basicLight"]

    def __init__(
        self,
        function: Optional[types.FunctionType] = None,
        function_name: Optional[str] = None,
        function_parameters: Optional[str] = None,
        docstring: Optional[str] = None,
        function_body: Optional[str] = None,
        builtins: Optional[dict[str, Any]] = None,
        code_theme: str = "basicLight",
    ):
        if function is not None:
            function_name = (
                function.__name__ if function_name is None else function_name
            )
            function_parameters = (
                self.get_function_parameters(function)
                if function_parameters is None
                else function_parameters
            )
            docstring = self.get_docstring(function) if docstring is None else docstring
            function_body = (
                self.get_function_body(function)
                if function_body is None
                else function_body
            )

        # default parameters from WidgetCodeInput
        if function_name is None:
            raise ValueError("function_name must be given if no function is given.")
        function_parameters = "" if function_parameters is None else function_parameters
        function_body = "" if function_body is None else function_body
        self._builtins = {} if builtins is None else builtins
        super().__init__(
            function_name, function_parameters, docstring, function_body, code_theme
        )

        # this list is retrieved from
        # https://github.com/osscar-org/widget-code-input/blob/eb10ca0baee65dd3bf62c9ec5d9cb2f152932ff5/js/widget.js#L249-L253
        if code_theme not in CodeInput.valid_code_themes:
            raise ValueError(
                f"Given code_theme {code_theme!r} invalid. Please use one of "
                f"the values {CodeInput.valid_code_themes}"
            )

    @property
    def unwrapped_function(self) -> types.FunctionType:
        """
        Returns the compiled function object.

        This can be assigned to a variable and then called, for instance:

          func = widget.wrapped_function # This can raise a SyntaxError
          retval = func(parameters)

        :raise SyntaxError: if the function code has syntax errors (or if
          the function name is not a valid identifier)
        """
        # we shallow copy the builtins to be able to overwrite it
        # if self.builtins changes
        globals_dict = {
            "__builtins__": copy.copy(globals()["__builtins__"]),
            "__name__": "__main__",
            "__doc__": None,
            "__package__": None,
        }

        globals_dict["__builtins__"].update(self._builtins)

        if not is_valid_variable_name(self.function_name):
            raise SyntaxError("Invalid function name '{}'".format(self.function_name))

        # Optionally one could do a ast.parse here already, to check syntax
        # before execution
        try:
            exec(
                compile(self.full_function_code, __name__, "exec", dont_inherit=True),
                globals_dict,
            )
        except SyntaxError as exc:
            raise CodeValidationError(
                format_syntax_error_msg(exc), orig_exc=exc
            ) from exc

        return globals_dict[self.function_name]

    def __call__(self, *args, **kwargs) -> Check.FunOutParamsT:
        """Calls the wrapped function"""
        return self.function(*args, **kwargs)

    def compatible_with_signature(self, parameters: List[str]) -> str:
        """
        This function checks if the arguments are compatible with the function signature
        and returns an explanatory message if this is not the case.
        """
        if "**" in self.function_parameters:
            # function has keyword arguments so it is compatible
            return ""
        for parameter_name in inspect.signature(self.function).parameters.keys():
            if not (parameter_name in parameters):
                return (
                    f"The input parameter {parameter_name} is not compatible with "
                    "the function code."
                )
        return ""

    @property
    def function_parameters_name(self) -> List[str]:
        """
        Returns the names of the function parameters
        """
        return self.function_parameters.replace(",", "").split(" ")

    @staticmethod
    def get_docstring(function: types.FunctionType) -> Union[str, None]:
        """
        Returns the docstring of a function, if it exists, without leading or trailing
        whitespace or triple quotes.
        """
        docstring = function.__doc__
        return (
            None
            if docstring is None
            else textwrap.dedent(docstring).strip('"""')  # noqa: B005
        )

    @staticmethod
    def _get_function_source_and_def(
        function: types.FunctionType,
    ) -> Tuple[str, ast.FunctionDef]:
        function_source = inspect.getsource(function)
        function_source = textwrap.dedent(function_source)
        module = ast.parse(function_source)
        if len(module.body) != 1:
            raise ValueError(
                f"Expected code with one function definition but found {module.body}"
            )
        function_definition = module.body[0]
        if not isinstance(function_definition, ast.FunctionDef):
            raise ValueError(
                f"While parsing code found {module.body[0]}"
                " but only ast.FunctionDef is supported."
            )
        return function_source, function_definition

    @staticmethod
    def get_function_parameters(function: types.FunctionType) -> str:
        """
        Returns the parameters of a function as a continuous string,
        e.g  for `foo(x, y = 5)` it would return `"x, y = 5"`
        """
        function_parameters = []
        function_source, function_definition = CodeInput._get_function_source_and_def(
            function
        )
        idx_start_defaults = len(function_definition.args.args) - len(
            function_definition.args.defaults
        )
        for i, arg in enumerate(function_definition.args.args):
            function_parameter = ast.get_source_segment(function_source, arg)
            # Following PEP 8 in formatting
            if arg.annotation:
                annotation = function_parameter = ast.get_source_segment(
                    function_source, arg.annotation
                )
                function_parameter = f"{arg.arg}: {annotation}"
            else:
                function_parameter = f"{arg.arg}"
            if i >= idx_start_defaults:
                default_val = ast.get_source_segment(
                    function_source,
                    function_definition.args.defaults[i - idx_start_defaults],
                )
                # Following PEP 8 in formatting
                if arg.annotation:
                    function_parameter = f"{function_parameter} = {default_val}"
                else:
                    function_parameter = f"{function_parameter}={default_val}"
            function_parameters.append(function_parameter)

        if function_definition.args.kwarg is not None:
            function_parameters.append(f"**{function_definition.args.kwarg.arg}")

        return ", ".join(function_parameters)

    @staticmethod
    def get_function_body(function: types.FunctionType) -> str:
        """
        Extracts the body of the given function, removing the signature, docstrings,
        and adjusting indentation appropriately.
        """
        source_lines, _ = inspect.getsourcelines(function)

        found_def = False
        def_index = 0
        for i, line in enumerate(source_lines):
            if "def" in line:
                found_def = True
                def_index = i
                break
        if not (found_def):
            raise ValueError(
                "Did not find any def definition. Only functions with a "
                "definition are supported"
            )

        # Remove function definition
        line = re.sub(r"^\s*def\s+[^\(]*\(.*\)(.*?):\n?", "", line)
        source_lines[def_index] = line
        # Remove any potential wrappers
        source_lines = source_lines[i:]

        source = "".join(source_lines)
        # Remove docstrings
        source = re.sub(
            r"((.*?)\'\'\'(.*?)\'\'\'.*?[;\n]|(.*?)\"\"\"(.*?)\"\"\"(.*?)[;\n])",
            "",
            source,
            flags=re.DOTALL,
        )

        # Adjust indentation
        lines = source.split("\n")
        if lines:
            leading_indent = len(lines[0]) - len(lines[0].lstrip())
            source = "\n".join(
                line[leading_indent:] if line.strip() else "" for line in lines
            )

        return source.strip()

    @property
    def function(self) -> types.FunctionType:
        """
        Returns the compiled function object wrapped by an try-catch block
        raising a `CodeValidationError`.

        This can be assigned to a variable and then called, for instance:

          func = widget.function # This can raise a CodeValidationError
          retval = func(parameters)

        :raise CodeValidationError: if the function code has syntax errors (or if
          the function name is not a valid identifier)
        """

        def catch_exceptions(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                """Wrap and check exceptions to return a longer and clearer
                exception."""

                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    err_msg = format_generic_error_msg(exc, code_widget=self)
                    raise CodeValidationError(err_msg, orig_exc=exc) from exc

            return wrapper

        return catch_exceptions(self.unwrapped_function)

    @property
    def builtins(self) -> dict[str, Any]:
        return self._builtins

    @builtins.setter
    def builtins(self, value: dict[str, Any]):
        self._builtins = value


# Temporary fix until https://github.com/osscar-org/widget-code-input/pull/26
# is merged
def format_generic_error_msg(exc, code_widget):
    """
    Returns a string reproducing the traceback of a typical error.
    This includes line numbers, as well as neighboring lines.

    It will require also the code_widget instance, to get the actual source code.

    :note: this must be called from within the exception, as it will get the
        current traceback state.

    :param exc: The exception that is being processed.
    :param code_widget: the instance of the code widget with the code that
        raised the exception.
    """
    error_class, _, tb = sys.exc_info()
    frame_summaries = traceback.extract_tb(tb)
    # The correct frame summary corresponding to widget_code_intput is not
    # always at the end therefore we loop through all of them
    wci_frame_summary = None
    for frame_summary in frame_summaries:
        if frame_summary.filename == "widget_code_input":
            wci_frame_summary = frame_summary
    if wci_frame_summary is None:
        warnings.warn(
            "Could not find traceback frame corresponding to "
            "widget_code_input, we output whole error message.",
            stacklevel=2,
        )

        return exc
    line_number = wci_frame_summary[1]
    code_lines = code_widget.full_function_code.splitlines()

    err_msg = f"{error_class.__name__} in code input: {str(exc)}\n"
    if line_number > 2:
        err_msg += f"     {line_number - 2:4d} {code_lines[line_number - 3]}\n"
    if line_number > 1:
        err_msg += f"     {line_number - 1:4d} {code_lines[line_number - 2]}\n"
    err_msg += f"---> {line_number:4d} {code_lines[line_number - 1]}\n"
    if line_number < len(code_lines):
        err_msg += f"     {line_number + 1:4d} {code_lines[line_number]}\n"
    if line_number < len(code_lines) - 1:
        err_msg += f"     {line_number + 2:4d} {code_lines[line_number + 1]}\n"

    return err_msg
