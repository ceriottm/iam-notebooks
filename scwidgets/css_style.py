import os

from ipywidgets import HTML


class CssStyle(HTML):
    """
    This HTML widget has to be displayed so the CSS style is loaded in the notebook.

    :param preamble: Text to appear before the style sheet
    """

    def __init__(self, preamble: str = ""):
        with open(os.path.join(os.path.dirname(__file__), "css/widgets.css")) as file:
            style_txt = file.read()

        HTML.__init__(self, preamble + "<style>" + style_txt + "</style>")


def get_css_style() -> HTML:
    return CssStyle(
        preamble="HTML with scicode-widget CSS style sheet. "
        "Please keep this cell output alive."
    )
