import re

from termcolor import colored


class Formatter:
    LINE_LENGTH = 120
    INFO_COLOR = "blue"
    ERROR_COLOR = "red"
    SUCCESS_COLOR = "green"

    @staticmethod
    def format_title_message(message: str) -> str:
        return message.center(Formatter.LINE_LENGTH - len(message) // 2, "-")

    @staticmethod
    def break_lines(message: str) -> str:
        return "\n ".join(
            re.findall(r".{1," + str(Formatter.LINE_LENGTH) + "}", message)
        )

    @staticmethod
    def color_error_message(message: str) -> str:
        return colored(message, Formatter.ERROR_COLOR, attrs=["bold"])

    @staticmethod
    def color_success_message(message: str) -> str:
        return colored(message, Formatter.SUCCESS_COLOR, attrs=["bold"])
        print(Formatter.color_success_message(message))

    @staticmethod
    def color_info_message(message: str):
        return colored(message, Formatter.INFO_COLOR, attrs=["bold"])
        print(Formatter.color_info_message(message))

    @staticmethod
    def color_assert_failed(message: str) -> str:
        return colored(message, "light_" + Formatter.ERROR_COLOR)

    @staticmethod
    def color_assert_info(message: str) -> str:
        return colored(message, "light_" + Formatter.INFO_COLOR)

    @staticmethod
    def color_assert_success(message: str) -> str:
        return colored(message, "light_" + Formatter.SUCCESS_COLOR)
