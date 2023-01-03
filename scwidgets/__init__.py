__version__ = "0.0.0"

from ._utils import (
    CodeDemoStatus
)

from ._check_registry import (
    CheckRegistry
)

from ._code_demo import (
    CodeDemo,
    ParametersBox,
    CodeChecker
)
from ._code_visualizer import (
    CodeVisualizer,
    PyplotOutput,
    ClearedOutput,
    AnimationOutput
)
from ._answer import (
    Answer,
    AnswerRegistry,
    TextareaAnswer
)

__all__ = [
    "CodeDemo",
    "ParametersBox",
    "CodeChecker",
    "CodeVisualizer",
    "PyplotOutput",
    "ClearedOutput",
    "AnimationOutput",
    "Answer",
    "AnswerRegistry"
    "TextareaAnswer",
]
import os
import IPython
with open(os.path.join(os.path.dirname(__file__), 'scwidget_style.css')) as file:
    style_txt = file.read()
    style_html = IPython.display.HTML("<style>"+style_txt+"</style>")
    IPython.display.display(style_html)
