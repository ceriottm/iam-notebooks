__version__ = "0.2.1"
__authors__ = "the scicode-widgets developer team"

from .check import *  # noqa: F403
from .code import *  # noqa: F403
from .cue import *  # noqa: F403
from .exercise import *  # noqa: F403

__all__ = [  # noqa: F405
    # cue
    "CueOutput",
    "CueObject",
    "CueFigure",
    # code
    "CodeInput",
    "ParametersPanel",
    # check
    "CheckRegistry",
    "assert_equal",
    "assert_shape",
    "assert_numpy_allclose",
    "assert_type",
    "assert_numpy_floating_sub_dtype",
    "assert_numpy_sub_dtype",
    # exercise
    "CodeExercise",
    "TextExercise",
    "ExerciseRegistry",
]
