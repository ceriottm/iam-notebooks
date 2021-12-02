import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from ipywidgets import (Output, FloatSlider, Box, HBox, VBox, Layout, Checkbox,
                        Button, HTML)
import traitlets

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
    
    def __init__(self, **kwargs):
        self._controls = {}
        for k, v in kwargs.items():
            if type(v) is tuple:
                if type(v[0]) is float:
                    val, min, max, step, desc = float_make_canonical(k, *v)
                    self._controls[k] = FloatSlider( value=val, min=min, max=max, step=step,
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
        with self._plot:
            if fig_ax is not None:
                self._fig, self.ax_ = fig_ax
            else:
                self._fig, self._ax = plt.subplots(1, 1, figsize=(4,3), tight_layout=True)                        
            self._fig.canvas.toolbar_visible = False
            self._fig.canvas.header_visible = False
            self._fig.canvas.footer_visible = False            
            plt.show(self._fig)            

        super(WidgetPlot, self).__init__()        
        # TODO: handle notebook backend or widgets, so that this shows correctly in appmode and in jupyterlab
        if mpl.get_backend() == 'nbAgg':
            self.children = [self._pars, self._plot]
        else:
            self.children = [self._pars, self._plot]
        self._pars.observe(self.update)
        self.update()
            
    def update(self, change={'type': 'change'}):
        self._ax.clear()
        self._plotter(self._ax, **self._pars.value, **self._args)
        self._fig.canvas.draw()
        
        
class WidgetCodeCheck(VBox):
    def __init__(self, wci, ref_values, demo=None):        
        
        self._wci = wci
        self._demo = demo
        if demo is not None:
            self._button = Button(description="Check & update")
        else:
            self._button = Button(description="Check")
            
        self._button.on_click(self.update)
        self._validation_text = HTML(value="")
        self._ref_values = ref_values

        super(WidgetCodeCheck, self).__init__()
        
        self.children = [wci, HBox([self._button, self._validation_text], layout=Layout(align_items='center'))]
        if demo is not None:
            self.children += (demo,)                
            
    def check(self):        
        user_fun = self._wci.get_function_object()
        nfail = 0
        allx = ()
        for x, y in self._ref_values.items():
            allx += x
            if not np.allclose(y, user_fun(*x)):
                nfail += 1         
                
        self._validation_text.value = "&nbsp;"*4
        if nfail==0:
            self._validation_text.value += f"<span style='color:green'> All tests passed!   Exercise code: { hash(allx)} </style>" 
        else:
            self._validation_text.value += f"   {nfail} out of {len(self._ref_values)} tests failed."
        
    def update(self, change={'type': 'change'}):
        self.check()
        if self._demo is not None:
            self._demo.update()          