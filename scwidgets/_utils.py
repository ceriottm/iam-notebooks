import inspect
import enum

# TODO(low) need to consider traits
def copy_widget(widget):
    signature = inspect.getfullargspec(type(widget).__init__)
    return type(widget)(*[getattr(widget, arg) for arg in signature.args[1:]])

#TODO move somewhere more meaningful
class CodeDemoStatus(enum.Enum):
    """
    These enumes describe the status of a custom Widget related to the CodeDemo. The usual status flows are:
    update status flow
      UP_TO_DATE -- user change --> OUT_OF_DATE -- update initiated --> UPDATING -- update finishes --> UP_TO_DATE
    check status flow
      CHECKED -- user change --> UNCHECKED -- check initiated --> CKECKING -- update finishes --> CHECKED
    """
    UPDATING = 0
    UP_TO_DATE = 1
    OUT_OF_DATE = 2
    CHECKING = 3
    CHECKED = 4
    UNCHECKED = 5
