import os 
import json
import functools
import glob
import enum

from ipywidgets import (
    Output,
    Button,
    VBox,
    HBox,
    Layout,
    Text,
    Textarea,
    Dropdown
)

#TODO put this helper in a more meaningful place
def request_confirmation(output,callback=None,warning=None,change=""):
    """Callback wrapper that implements confirmation/cancel button before a given action/method. 
    output : The output that will display Confirmation/Cancel buttons (and warnings if any are defined).
    callback : Callback to be called if confirmation button is clicked. If None, confirmation button has the same behaviour as cancel button.
    warning : Message to be shown with buttons, indicating to user the effect of confirming
    """
    def collapse_after_confirmation(callback=None,change=""):
        if callback != None:
            callback()
        else :
            output.clear_output()
    confirm_button = Button(description="Yes",tooltip="Confirm")
    cancel_button = Button(description="Cancel",tooltip="Cancel")
    confirm_button.on_click(lambda _: collapse_after_confirmation(callback))
    cancel_button.on_click(lambda _: collapse_after_confirmation())
    with output:
        output.clear_output()
        if warning == None:
            warning = "Are you sure ?"
        print(warning)
        with output:
            display(HBox([confirm_button,cancel_button]))

class AnswerStatus(enum.Enum):
    NOT_SAVED = 0
    SAVED = 1

class Answer:
    """An interface for a widget which contains an answer for a question that can be saved to a file by the widget."""
    def __init__(self):
        self._save_output = Output()
        self._on_save_callback = None
        self._on_load_callback = None

        # inits default buttons but doesn't display or link them
        self._save_button = Button(description="Save answer", layout=Layout(width="200px", height="100%"),tooltip="Save answer to personal file")        
        self._load_button = Button(description="Reload answer", layout=Layout(width="200px", height="100%"),disabled = True,tooltip="Erase modifications and recover last saved answer")
        
    @property
    def save_output(self):
        return self._save_output

    # for observe
    def set_status_saved(self, change=None):
       self.save_status = AnswerStatus.SAVED
    def set_status_not_saved(self, change=None):
       self.save_status = AnswerStatus.NOT_SAVED

    @property
    def save_status(self):
        return self._save_status if hasattr(self, "_save_status") else None
    @save_status.setter

    def save_status(self, save_status):
        if save_status == AnswerStatus.SAVED:
            self._save_button.disabled = True
            self._save_button.remove_class("answer-not-saved")
            self._save_button.description = 'Answer saved'
            self._load_button.disabled = True
        if save_status == AnswerStatus.NOT_SAVED:
            self._save_button.description = 'Save answer'
            self._save_button.disabled = False
            self._save_button.add_class("answer-not-saved")
            self._load_button.disabled = False
            self._save_output.clear_output()

    @property
    def answer_value(self):
        raise NotImplementedError("answer_value property has not been implemented.")

    @answer_value.setter
    def answer_value(self, new_answer_value):
        raise NotImplementedError("answer property setter has not been implemented.")
    
    def show_answer_interface(self):
        # default way to instrument an answer interface
        if hasattr(self, "children"):
            self.children += (VBox([VBox([self._save_button,self._load_button] 
                                   if (self._on_load_callback is not None) else [self._save_button]), self._save_output],
                layout=Layout(align_items="flex-start")),)
        else:
            raise ValueError("Widget doesn't have a Box interface, place the answer buttons manually")

    def init_answer_callbacks(self, save_callback=None, load_callback=None):         
        if save_callback is not None and self._save_button is not None:
            # remove previous associations if present       
            if self._on_save_callback is not None:
                self._save_button.on_click(self._on_save_callback, remove=True)
            self._on_save_callback = save_callback
            self._save_button.on_click(self._on_save_callback)
        
        if load_callback is not None and self._load_button is not None:
            if self._on_load_callback is not None:
                self._load_button.on_click(self._on_load_callback, remove=True)
            self._on_load_callback = load_callback
            self._load_button.on_click(self._on_load_callback)

class AnswerRegistry(VBox):
    """
    A widget to enter the name of the learner, and to save the state of registered widgets to a .json file, and load them back afterwards.
    """
    @property
    def prefix(self):
        return self._prefix

    def is_valid_filename(self, filename):
        return ((self.prefix is not None and filename.startswith(self.prefix+"-") \
                or (self.prefix is None))) \
                and (filename.endswith("json"))

    @staticmethod
    def standardize_filename(filename):
        return filename.lower()

    def __init__(self, prefix=None, *args, **kwargs):
        self._prefix = prefix
        #prefix must be lowercase in order to ensure files are correctly maintained (only lowercase)
        self._callbacks = {}
        self._current_path = os.getcwd()
        self._json_list = [filename for filename in
                map(os.path.basename, glob.glob(self._current_path + "/*.json"))
                if self.is_valid_filename(filename)]
        self._json_list.append("Create new answer file")
        self._answers_filename = None

        #Create/load/unload registry widgets
        self._student_name_text  = Text(placeholder='Enter your name here',  style= {'description_width': 'initial'})
        self._load_answers_button = Button(description='Confirm')
        self._create_savefile_button = Button(description='Confirm')
        self._reload_button = Button(description='Choose other file')
        self._reload_all_answers_button = Button(description='Reload all answers',tooltip="Reload answers saved in .json file to notebook.")
        self._new_savefile = HBox([self._student_name_text, self._create_savefile_button])
        self._dropdown = Dropdown(
                            options=self._json_list,
                            description='Choose:',
                            disabled=False,
                        )
        self._savebox = HBox([self._dropdown, self._new_savefile]) \
                                if len(self._json_list) == 1 \
                                else HBox([self._dropdown, self._load_answers_button])

        self._current_dropdown_value = self._dropdown.value
        self._answer_widgets = {}
        self._preoutput = Output(layout=Layout(width='99%', height='99%'))
        self._output = Output(layout=Layout(width='99%', height='99%'))
        self._save_all_button = Button(description = 'Save all answers')
        super().__init__(
                [self._preoutput, self._savebox, self._output])

        #Stateful behavior:
        self._load_answers_button.on_click(self._load_all)
        self._create_savefile_button.on_click(self._create_savefile)
        self._dropdown.observe(self._on_choice,names='value')
        self._reload_button.on_click(self._enable_savebox)
        self._save_all_button.on_click(lambda _ : request_confirmation(self._output,self._save_all))
        self._reload_all_answers_button.on_click(lambda _ : request_confirmation(self._output,self._load_all))
        with self._preoutput:
            print("Please choose a save file and confirm before answering questions.")

    def clear_output(self):
        self._output.clear_output()

    def _on_choice(self,change=""):
        """
        a callback which observes _dropdown widget and proposes _new_savefile or _load_answers_button widgets depending on _current_dropdown_value
        """
        if change['new'][-5:-1] != change['old'][-5:-1]:
            if change['new'] == self._dropdown.options[-1]:
                self._savebox.children = [self._dropdown, self._new_savefile]
            else:
                self._savebox.children = [self._dropdown, self._load_answers_button]
        self._current_dropdown_value = change['new']

    def _load_answer(self, change="", answer_key=""):        
        with open(self._answers_filename, "r") as answers_file:
            answers = json.load(answers_file)
            if not answer_key in answers:
                raise ValueError("Cannot load {answer_key} from answer file.")
            if not answer_key in self._answer_widgets:
                raise ValueError("Key {answer_key} is not associated with a registered answer widget.")
            self._answer_widgets[answer_key].answer_value = answers[answer_key]
            self._answer_widgets[answer_key].set_status_saved()

    def _load_all(self, change=""):
        """
        loads registry when _load_answers_button is clicked
        """
        self.clear_output()
        self._answers_filename = self._current_dropdown_value
        error_occured = False
        with open(self._answers_filename, "r") as answers_file:
            answers = json.load(answers_file)
            for answer_key, answer_value in answers.items():
                if not answer_key in self._answer_widgets:
                    with self._output:
                        error_occured = True
                        # TODO improve message and restrict error trace to this ValueError
                        raise ValueError(f"Your json file contains unexpected Answer with key : {answer_key}.  ")
                else:
                    self._answer_widgets[answer_key].answer_value = answer_value
                    self._answer_widgets[answer_key].set_status_saved()

        if not error_occured:
            self._disable_savebox()
            self.children = [self._savebox, HBox([self._reload_button, self._save_all_button,self._reload_all_answers_button]), self._output]
            with self._output:
                print(f"\033[92m File '{self._answers_filename}' loaded successfully.")

    def _verify_valid_student_name(self):
        if AnswerRegistry.is_name_empty(self._student_name_text.value):
            self.clear_output()
            # TODO we should we classify prints and so we can give them styles
            with self._output:
                print(f"\033[91m Your name is empty. Please provide a new one.")
            return False

        forbidden_characters = AnswerRegistry.extract_forbidden_characters(self._student_name_text.value)
        if len(forbidden_characters) > 0:
            self.clear_output()
            with self._output:
                print(f"\033[91m The name '{self._student_name_text.value}' contains invalid special characters {forbidden_characters}. Please provide another name.")
            return False

        return True

    def _create_savefile(self, change=""):
        """
        creates a new registry when _new_savefile_button is clicked
        """
        # Checks that the name is valid. If invalid, erase the name.

        if not(self._verify_valid_student_name()):
            return

        # if prefix is defined, it is added to the filename
        answers_filename = ""
        if (self._prefix is not None):
            answers_filename += self.prefix + "-"
        answers_filename += AnswerRegistry.standardize_filename(self._student_name_text.value) + ".json"

        if os.path.exists(answers_filename):
            self.clear_output()
            with self._output:
                print(f"\033[91m The name '{self._student_name_text.value.lower()}' is already used in file '{self._answers_filename}'. Please provide a new one.")
        else:
            self._answers_filename = answers_filename
            answers = {key: widget.answer_value for key, widget in self._answer_widgets.items()}
            with open(self._answers_filename, "w") as answers_file:
                json.dump(answers, answers_file)
            self._disable_savebox()
            self._json_list = list(dict.fromkeys([self._answers_filename] + self._json_list))
            self._dropdown.options = self._json_list
            self.children = [self._savebox,  HBox([self._reload_button, self._save_all_button]), self._output]
            self.clear_output()
            with self._output:
                print(f"\033[92m File {self._answers_filename} successfully created and loaded.")

    def _save_answer(self, change, answer_key=None):
        if answer_key is None:
            raise ValueError("Cannot save answer with None answer_key")
        self._answer_widgets[answer_key].save_output.clear_output()
        if (self._answers_filename is None) or not(os.path.exists(self._answers_filename)):
            # outputs error at the widget where the save button is attached to
            with self._answer_widgets[answer_key].save_output:
                raise FileNotFoundError(f"No file has been loaded.")
            return False
        else:
            with open(self._answers_filename, "r") as answers_file:
                answers = json.load(answers_file)
            answers[answer_key] = self._answer_widgets[answer_key].answer_value
            self._answer_widgets[answer_key].set_status_saved()
            with open(self._answers_filename, "w") as answers_file:
                json.dump(answers , answers_file)
            # outputs message at the widget where the save button is attached to
            with self._answer_widgets[answer_key].save_output:
                print(f"The answer was successfully recorded in '{self._answers_filename}'")
            return True

    def _save_all(self,change=None):
        self._output.clear_output()
        for widgets in self._answer_widgets.values():
            widgets._save_button.click()
        with self._output : 
            print(f"All answers were successfully recorded in '{self._answers_filename}'")

        
    @staticmethod
    def is_name_empty(name):
        return len(name) == name.count(" ")

    @staticmethod
    def extract_forbidden_characters(name):
        character_list = []
        forbidden_characters = "./\\"
        for character in forbidden_characters:
            if character in name:
                character_list += character
        return character_list

    def _disable_savebox(self):
        self._create_savefile_button.disabled = True
        self._load_answers_button.disabled = True
        self._dropdown.disabled = True
        self._student_name_text.disabled = True

    def _enable_savebox(self, change=""):
        # clean old states
        self._answers_filename = None
        #self._json_list = [os.path.basename(path)
        #        for path in glob.glob(self._current_path + "/*.json")
        #            if (os.path.basename(path).startswith(self.prefix+"-")
        #                and self.prefix != "") or (self.prefix == "")]
        self._json_list = [filename for filename in
                map(os.path.basename, glob.glob(self._current_path + "/*.json"))
                if self.is_valid_filename(filename)]
        self._json_list.append("Create new answer file")
        self._create_savefile_button.disabled = False
        self._load_answers_button.disabled = False
        self._dropdown.disabled = False
        self._student_name_text.disabled = False
        self.children = [self._savebox, self._output]
        self.clear_output()
        # Clears output in each answer when another registry is loaded
        for key, answer_widget in self._answer_widgets.items() : 
            answer_widget.save_output.clear_output()

    def register_answer_widget(self, answer_key, widget):
        self._answer_widgets[answer_key] = widget
        if isinstance(widget, Answer):
            self._callbacks[answer_key] = ( functools.partial(self._save_answer, answer_key=answer_key), 
                                            functools.partial(self._load_answer, answer_key=answer_key) )
            widget.init_answer_callbacks(*self._callbacks[answer_key])
            widget.show_answer_interface()            
        else:
            raise ValueError(f"Widget {widget} is not of type {Answer.__name__}. Therefore does not support saving the of answer.")



class TextareaAnswer(VBox, Answer):
    """ A widget that contains a Textarea whose value can be saved"""
    def __init__(self, *args, **kwargs):
        if 'layout' not in kwargs.keys():
            kwargs['layout'] = Layout(width='99%')
        self._answer_textarea = Textarea(*args, **kwargs)
        super(VBox, self).__init__(
                [self._answer_textarea], layout=Layout(align_items="flex-start", width='100%'))
        self._answer_textarea.observe(self.set_status_not_saved,"value") #@Joao added observe here

    @property
    def answer_value(self):
        return self._answer_textarea.value

    @answer_value.setter
    def answer_value(self, new_answer_value):
        self._answer_textarea.value = new_answer_value
