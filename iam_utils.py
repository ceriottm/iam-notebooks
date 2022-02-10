import numpy as np
import matplotlib as mpl
import json
import matplotlib.pyplot as plt
from collections.abc import Iterable
from IPython.display import clear_output
from ipywidgets import (Output, FloatSlider, IntSlider,
                        Box, HBox, VBox, Layout, Checkbox,
                        Button, HTML, Text)
import traitlets

global_variable = 1.0

def float_make_canonical(key, default, minval=None, maxval=None, step=None, desc=None, *args):
    # gets the (possibly incomplete) options for a float value, and completes as needed
    if minval is None:
        minval = min(default, 0)
    if maxval is None:
        maxval = max(default, 100)
    if step is None:
        step = (maxval-minval)/100
    if desc is None:
        desc = key
    if len(args)>0:
        raise ValueError("Too many options for a float parameter")
    return default, minval, maxval, step, desc

def int_make_canonical(key, default, minval=None, maxval=None, step=None, desc=None, *args):
    # gets the (possibly incomplete) options for a int value, and completes as needed    
    if minval is None:
        minval = min(default, 0)
    if maxval is None:
        maxval = max(default, 10)
    if step is None:
        step = 1
    if desc is None:
        desc = key
    if len(args)>0:
        raise ValueError("Too many options for a int parameter")
    if type(minval) is not int or  type(maxval) is not int or type(step) is not int:
        raise ValueError("Float option for an int parameter")
    return default, minval, maxval, step, desc

def bool_make_canonical(key, default, desc=None, *args):
    # gets the (possibly incomplete) options for a bool value, and completes as needed
    if desc is None:
        desc = key
    if len(args)>0:
        raise ValueError("Too many options for a bool parameter")
    return default, desc

class WidgetParbox(VBox):
    """ Parameter box widget.
        
        Creates a container that manipulates several parameters at the same time, and that can be
        linked to another object to trigger its update whenever any of the parameters is changed.
        
        Parameters
        ----------
        kwargs: dict
            The widget can be initialized with a list of named parameters, that correspond to the names of 
            the variables it controls. Each can be initialized with a tuple 
            `(initial value, [min, max, step], [label])`
            The type of `initial_value` determines the control shown:
            float: FloatSlider
            bool: Checkbox
            TODO: add more
            Alternatively, one can pass any control widget that contains a value, e.g.
            `parameter = FloatSlider( ... )`

        Attributes
        ----------
        value: dict
            Dictionary containing parameter = value pairs, that is dynamically linked to the controls
        
        Examples
        --------
        >>> parbox = ParameterBox( par_1 = (0.1, 0, 1, 0.01, "parameter 1"), 
                                   par_2 = (True, "parameter 2) )
        >>> parbox.parameters()
        { par_1 : 0.1, par_2 : True }        
        
    """
    
    value = traitlets.Dict({}, sync=True)
    
    def __init__(self, onchange=None, **kwargs):
        self._controls = {}
        for k, v in kwargs.items():
            if k == "onchange":
                continue
            if type(v) is tuple:
                if type(v[0]) is float:
                    val, min, max, step, desc = float_make_canonical(k, *v)
                    self._controls[k] = FloatSlider( value=val, min=min, max=max, step=step,
                                                    description=desc, continuous_update=False, 
                                                    style={'description_width': 'initial'}, 
                                                    layout=Layout(width='50%', min_width='5in'))   
                elif type(v[0]) is int:
                    val, min, max, step, desc = int_make_canonical(k, *v)                    
                    self._controls[k] = IntSlider( value=val, min=min, max=max, step=step,
                                                    description=desc, continuous_update=False, 
                                                    style={'description_width': 'initial'}, 
                                                    layout=Layout(width='50%', min_width='5in'))   
                elif type(v[0]) is bool:
                    val, desc = bool_make_canonical(k, *v)
                    self._controls[k] = Checkbox(value = val, description=desc, continuous_update=False, 
                                                  style={'description_width': 'initial'}, 
                                                  layout=Layout(width='50%', min_width='5in')
                                                )
                else:
                    raise ValueError("Unsupported parameter type")
            else:
                # assumes an explicit control has been passed
                self._controls[k] = v

        super(WidgetParbox, self).__init__()
        self.children =[control for control in self._controls.values()]
        
        # links changes to the controls to the value dict
        for k in self._controls:
            self._controls[k].observe(self._parameter_handler(k), 'value')
            self.value[k] = self._controls[k].value
        if onchange is not None:
            self.observe(onchange)
        
    def _parameter_handler(self, k):
        def _update_parameter(change):
            # traitlets.Dict cannot track updates, only assignment
            dict_copy = self.value.copy()
            dict_copy[k] = self._controls[k].value
            self.value = dict_copy
        return _update_parameter            
            
class WidgetPlot(VBox):
    """ Matplotlib interactive plot widget
    
    Creates a standard plot widget that takes a plotting function, and a parameter widget
    and returns an interactive plot generated by calling the plotter with the specified parameters. 
                
    Parameters
    ----------
    plotter: function    
        A function that takes an Axes object, and a list of named parameters, and populates the ax
        with a drawing generated based on the parameters
        
    parbox: WidgetParbox
        A WidgetParbox widget containing the parameters for manipulating the plot
    
    fixed_args: dict
        Parameters that are passed to plotter() without being associated to an interactive widgtet        
    """
    
    def __init__(self, plotter, parbox, fixed_args={}, fig_ax = None):
        
        self._args = fixed_args
        self._pars = parbox
        self._plotter = plotter
        self._plot = Output()
        
        super(WidgetPlot, self).__init__([self._pars, self._plot])
        
        with self._plot:                               
            if fig_ax is not None:
                self._fig, self._ax = fig_ax
            else:
                self._fig, self._ax = plt.subplots(1, 1, figsize=(4,3), tight_layout=True)                
            self._fig.canvas.toolbar_visible = True            
            self._fig.canvas.header_visible = False
            self._fig.canvas.footer_visible = False                            
            plt.show(self._fig.canvas)        
                
        self._pars.observe(self.update)
        self.update()                    
            
    def update(self, change={'type': 'change'}):
        if isinstance(self._ax, Iterable):
            axes = self._ax
        else:
            axes = [self._ax]
        for ax in axes:
            if ax.has_data() or len(ax.artists)>0:
                ax.clear()

        self._plotter(self._ax, **self._pars.value, **self._args)
        #self._fig.canvas.draw()
        #self._fig.canvas.flush_events()
        
        
class WidgetCodeCheck(VBox):
    def __init__(self, wci, ref_values, demo=None, ref_match=np.allclose):        
        
        self._wci = wci
        self._demo = demo
        if demo is not None:
            self._button = Button(description="Check & update")
        else:
            self._button = Button(description="Check")
            
        self._button.on_click(self.update)
        self._validation_text = HTML(value="")
        self._ref_values = ref_values
        self._ref_match = ref_match
        
        self._err = Output(layout=Layout(width='100%', height='100%'))
        super(WidgetCodeCheck, self).__init__([wci, 
                                               HBox([self._button, self._validation_text],
                                                    layout=Layout(align_items='center')),
                                               self._err
                                              ])
        
        if demo is not None:
            self.children += (demo,)                
            
    def check(self):
        self._err.clear_output()
        nfail = 0
        allx = ()
        f_error = False
        with self._err:            
            user_fun = self._wci.get_function_object()
            try:
                for x, y in self._ref_values.items():
                    allx += x
                    if not self._ref_match(y, user_fun(*x)):
                        nfail += 1         
            except:
                f_error = True
                raise

        self._validation_text.value = "&nbsp;"*4
        if nfail==0:
            self._validation_text.value += f"<span style='color:green'> All tests passed!   Exercise code: { hash(allx)} </style>" 
        else:
            self._validation_text.value += f"   {nfail} out of {len(self._ref_values)} tests failed."
        return f_error
        
    def update(self, change={'type': 'change'}):        
        if self.check() is True:
            # don't trigger further errors if the check failed
            return
        if self._demo is not None:
            self._demo.update()     

class WidgetUpdater(Output):
    """Mini-wrapper to provide an output space that gets updated by calling a function, 
    e.g. to print some output or reload a widget. """
    
    def __init__(self, updater, **kwargs):
        self._updater = updater
        super(WidgetUpdater, self).__init__()
        
    def update(self):
        self.clear_output()
        with self:
            self._updater()       

class WidgetDataDumper(HBox):
    """
    A widget to enter the name of the learner, and to save the state of selected  
    widgets to a .json file, and load them back afterwards.    
    """
    
    def _save_all(self, change=""):
        js = dict()
        for f_id, f_val in self._fields.items():
            js[f_id] = getattr(f_val[0], f_val[1])
        jsname = self._prefix+"-"+self._sname.value.replace(" ","")+".json"
        json.dump(js, open(jsname, "w"))

    def _load_all(self, change=""):
        jsname = self._prefix+"-"+self._sname.value.replace(" ","")+".json"        
        js = json.load(open(jsname, "r"))
        for f_id, f_val in js.items():
            if not f_id in self._fields:
                raise ValueError(f"Field ID {f_id} in the data dump is not registered.")
            setattr(self._fields[f_id][0], self._fields[f_id][1], f_val)

    def __init__(self, prefix="dump"):
        self._prefix = prefix
        
        self._bsave = Button(description="Save all")
        self._bload = Button(description="Load all")
        self._sname = Text(description="Name")
        super(WidgetDataDumper, self).__init__([self._sname, self._bsave, self._bload])
        self._bsave.on_click(self._save_all)
        self._bload.on_click(self._load_all)
        self._fields = {}
    
    def register_field(self, field_id, widget, trait):
        self._fields[field_id] = (widget, trait)
