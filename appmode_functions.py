"""
Functions to make the interaction work with the appmode and Code input widget.

give a setup class that initialize the environment variable like the widgets to get_recompute and it returns the function
synchronizing the interactivity.
"""
import numpy as np
import tabulate
from ipywidgets import Label, Button, Output, FloatSlider, HBox, VBox, Layout, HTML, Accordion

def get_recompute(setup_class):
    
    code_widget = setup_class.code_widget
    check_function_output = setup_class.check_function_output
    reference_func = setup_class.reference_func
    test_values_dict = setup_class.test_values_dict
    sliders_dict = setup_class.sliders_dict
    widgets = setup_class.widgets
    replot = setup_class.replot
    
    def recompute(e):
        if e is not None:
            if e['type'] != 'change' or e['name'] not in ['value', 'function_body']:
                return     
        replot_kwargs = {k:slider.value for k,slider in sliders_dict.items()}
        replot(**replot_kwargs)

        # Print info on the "correctness" of the user's function
        try:
            check_user_value(code_widget, check_function_output, reference_func, test_values_dict)
        except:
            pass
    
    
    for widget in widgets:
        widget.observe(recompute)
        
    return recompute


def check_user_value(code_widget, check_function_output, reference_func, test_values_dict):
    import itertools
    import numpy as np
    
    # I don't catch exceptions so that the users can see the traceback
    error_string = "YOUR FUNCTION DOES NOT SEEM RIGHT, PLEASE TRY TO FIX IT"
    ok_string = "YOUR FUNCTION SEEMS TO BE CORRECT!! CONGRATULATIONS!"
    
    test_table = []
    last_exception = None
    type_warning = False
    
    check_function_output.clear_output(wait=True)
    with check_function_output:
        user_function = code_widget.get_function_object() 

        failed_tests = []
        for test_vals in itertools.product(*test_values_dict.values()):
            input_dict = {k:v for k,v in zip(test_values_dict.keys(),test_vals)}
            np.random.seed(10)
            correct_value = np.asarray(reference_func(**input_dict))
            # error = np.abs(user_value - correct_value).max()
            try:
                np.random.seed(10)
                user_value = np.asarray(user_function(**input_dict))
                try:
                    error = np.abs(user_value - correct_value).max()
                except Exception:
                    type_warning = True
                    error = 1. # Large value so it triggers a failed test
            except Exception as exc:
                last_exception = exc
                test_table.append(list(test_vals)+[correct_value, "ERROR", False])
            else:
                if error > 1.e-6:
                    test_table.append(list(test_vals)+[str(correct_value), str(user_value), False])
                    failed_tests.append(test_table[-1])
                else:
                    test_table.append(list(test_vals)+[str(correct_value), str(user_value), True])

        num_tests = len(test_table)
        num_passed_tests = num_tests - len(failed_tests)

        
        MAX_FAILED_TESTS = 5
        if num_passed_tests < num_tests:
            html_table = HTML("<style>tbody tr:nth-child(odd) { background-color: #e2f7ff; } th { background-color: #94cae0; min-width: 100px; } td { font-family: monospace; } td, th { padding-right: 3px; padding-left: 3px; } </style>" + 
                             tabulate.tabulate(
                                 failed_tests[:MAX_FAILED_TESTS], 
                                 tablefmt='html',
                                 headers=list(test_values_dict.keys()) + ["Expected value", "Your value"]
                             ))
                
        if num_passed_tests < num_tests:
            print("Your function does not seem correct; only {}/{} tests passed".format(num_passed_tests, num_tests))
            print("Printing up to {} failed tests:".format(MAX_FAILED_TESTS))
            display(html_table)
        else:
            print("Your function is correct! Very good! All {} tests passed".format(num_tests))
        
        if type_warning:
            print("WARNING! in at least one case, your function did not return a valid float number, please double check!".format(num_tests))
    
        # Raise the last exception obtained
        if last_exception is not None:
            print("I obtained at least one exception")
            raise last_exception from None
                        
def get_user_value(code_widget, check_function_output, sliders_dict, **kwargs):
    """
    This function returns the value computed by the user's
    function for the current sliders' value, or None if there is an exception
    """
    kwargs.update({k:slider.value for k,slider in sliders_dict.items()})
    with check_function_output:
        user_function = code_widget.get_function_object() 
        try:
            user_values = user_function(**kwargs)
        except Exception as exc:
            return None
    return user_values        

