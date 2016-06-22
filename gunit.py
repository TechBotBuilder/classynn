from tkinter import *
from units import Unit, InputUnit, OutputUnit
from units import Connection

MAXVAL = Connection.max_magnitude

#predefine some nonlinearities for people to use:
#remember derivatives are based on outputs - so y=sigmoid(x) -> dy/dx = y*(1-y)
from math import exp
def sigmoid(x): return 1/(1+exp(-x))
def dsigmoid(y): return y*(1-y)

from math import tanh
def dtanh(y): return 1 - y**2

def linear(x): return x
def dlinear(y): return 1

def rectified_linear(x): return max(0, x)
def drectified_linear(y): return int(y != 0)

possible_nonlinearities = {'sigmoid': (sigmoid, dsigmoid), 'tanh': (tanh, dtanh),
    'linear': (linear, dlinear), 'rectified_linear': (rectified_linear, drectified_linear)}


#help from http://stackoverflow.com/a/24943263
def edit_frame(frame, option, value):
    for child in frame.winfo_children():
        if 'class' in child.config() and child['class'] == 'Frame':
            edit_frame(child, option, value)
        else:
            child[option]=value

def disable_frame(frame):
    edit_frame(frame, 'state', 'disabled')
def enable_frame(frame):
    edit_frame(frame, 'state', 'normal')

def take_care_of_lists(value):
    if hasattr(value, "__iter__"): #acts like a list
        if value: value = value[-1]
        else: value = 0
    elif hasattr(value, '__call__'):
        value = value.__name__
    return value

def value_to_color(val, minval=-MAXVAL, maxval=MAXVAL):
    if minval is None: minval = -MAXVAL
    if maxval is None: maxval = MAXVAL
    val = take_care_of_lists(val)
    hue, saturation, lightness = 360*(val-minval)/(maxval-minval), 0.6, 0.5
    chroma = (1-abs(2*lightness-1))*saturation
    hue_prime = hue / 60
    x = chroma * (1 - abs((hue_prime % 2.0)-1))
    r,g,b = 0,0,0
    if 0 <= hue_prime < 1:   r,g,b=chroma,x,0
    elif 1 <= hue_prime < 2: r,g,b=x,chroma,0
    elif 2 <= hue_prime < 3: r,g,b=0,chroma,x
    elif 3 <= hue_prime < 4: r,g,b=0,x,chroma
    elif 4 <= hue_prime < 5: r,g,b=x,0,chroma
    elif 5 <= hue_prime < 6: r,g,b=chroma,0,x
    m = lightness - chroma/2
    r,g,b = r+m, g+m, b+m
    r,g,b = 256*r, 256*g, 256*b
    return "#{:02x}{:02x}{:02x}".format(int(r),int(g),int(b))
tocolor = value_to_color

class Watchable:
    def __setattr__(self, name, value):
        if not 'watcher' in self.__dict__:
            super().__setattr__('watcher', None)
        super().__setattr__(name, value)
        if name == 'watcher':
            if 'graphic' in self.__dict__:
                if value is None:
                    self.dehighlight()
                else:
                    self.highlight()
        elif self.watcher and name in self.watcher.parts: #if we're being watched
            if name in ('nonlinearity', 'nonlinearity_deriv'):
                if self.watcher.parts[name].get() != value.__name__:
                    self.watcher.parts[name].set(value.__name__)
            else:
                if self.watcher.parts[name].get() != value:#if it doesn't already know what's happening
                    self.watcher.parts[name].set(value)#let the watcher know what's happening
    def highlight(self):
        pass
    def dehighlight(self):
        pass

class ConnectionGraphic:
    def __init__(self, con, canvas, startpos, endpos):
        self.con = con
        self.canvas = canvas
        self.ids = {'value': self.canvas.create_line(*startpos, *endpos, fill='black', width=4)}
        for part in self.ids:
            self.canvas.tag_bind(self.ids[part], "<Button-1>", self.canvas.master.configconnection(self.con))
    def recolor(self, what, value, minval=None, maxval=None):
        self.canvas.itemconfig(self.ids[what], fill=tocolor(value, minval, maxval))

class GConnection(Connection, Watchable):
    def __init__(self, canvas, startpos, endpos, *args, **kwargs):
        self.watcher = None
        print("Adding connection from {} to {}.".format(startpos, endpos))
        self.graphic = ConnectionGraphic(self, canvas, startpos, endpos)
        self.canvas = canvas
        super().__init__(*args, **kwargs)
    @property
    def value(self):
        return super().value
    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.graphic.recolor('value', self.value)
    def highlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], width=8)
    def dehighlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], width=4)

class UnitGraphic:
    def __init__(self, unit, canvas, position):
        self.canvas = canvas
        self.positions = {}
        self.find_bounds(position)
        self.gen_graphic(position)
        for piece in self.ids:
            self.canvas.tag_bind(self.ids[piece], "<Button-1>", self.canvas.master.addconnection(unit))
    def find_bounds(self, mainposition):
        mp = mainposition
        bigsize = 20
        smallsize = 10
        self.positions['logit'] = (*mp, mp[0]+smallsize, mp[1]+bigsize)
        self.positions['activation'] = (mp[0]+smallsize, mp[1], mp[0]+bigsize+2*smallsize, mp[1]+bigsize)
        self.positions['indelta'] = (mp[0], mp[1]+bigsize, mp[0]+smallsize, mp[1]+bigsize+smallsize)
        self.positions['derivative'] = (mp[0]+smallsize, mp[1]+bigsize, mp[0]+smallsize+bigsize, mp[1]+bigsize+smallsize)
        self.positions['outdelta'] = (mp[0]+smallsize+bigsize, mp[1]+bigsize, mp[0]+2*smallsize+bigsize, mp[1]+bigsize+smallsize)
    def gen_graphic(self, position):
        self.ids = dict([(key, self.canvas.create_rectangle(*(self.positions[key]), fill=tocolor(0, 0, 1))) for key in self.positions.keys()])
    @property
    def position(self):
        return self.canvas.bbox(self.ids['activation'])[:2]
    @position.setter
    def position(self, newposition):
        self.find_bounds(newposition)
        for key, item in self.ids.items():
            self.canvas.coords(item, *self.positions[key])
    def recolor(self, what, value, minval=None, maxval=None):
        self.canvas.itemconfig(self.ids[what], fill=tocolor(value, minval, maxval))

class GUnit(Unit, Watchable):
    def __init__(self, canvas, position, *args, **kwargs):
        print("Adding {} unit at {}, {}".format(str(type(self)), *position))
        self.canvas = canvas
        self.graphic = UnitGraphic(self, canvas, position)
        super().__init__(*args, **kwargs)
        self.position = position
        self.weights = [GConnection() for weight in self.weights]
    @property
    def position(self):
        return self.graphic.position
    @position.setter
    def position(self, newposition):
        self.graphic.position = newposition
    ##now extend things that change unit properties to update the gunit colors
    def __setattr__(self, name, val):
        super().__setattr__(name, val)
        if name in ('logit', 'frozenlogit'):
            self.graphic.recolor('logit', self.frozenlogit if self.frozen else self.logit)
        elif name == 'output':
            self.graphic.recolor('activation', self.output)
        elif name == 'delta':
            self.graphic.recolor('indelta', self.delta)
        elif name in ('derivative', 'outdelta'):
            self.graphic.recolor(name, val)
    def highlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], outline='yellow')
    def dehighlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], outline='black')

class GInputUnit(GUnit, InputUnit):
    def __init__(self, canvas, position, *args, **kwargs):
        GUnit.__init__(self, canvas, position)
        InputUnit.__init__(self, *args, **kwargs)

class GOutputUnit(GUnit, OutputUnit):
    def __init__(self, canvas, position, *args, **kwargs):
        GUnit.__init__(self, canvas, position)
        OutputUnit.__init__(self, *args, **kwargs)

class OptionsFrame(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(side=LEFT)
        self._unit_type = StringVar()
        self._unit_type.set('hidden')
        Radiobutton(self, text='Input Unit', variable=self._unit_type, value='input', indicatoron=0).pack(anchor=W)
        Radiobutton(self, text='Hidden Unit', variable=self._unit_type, value='hidden', indicatoron=0).pack(anchor=W)
        Radiobutton(self, text='Output Unit', variable=self._unit_type, value='output', indicatoron=0).pack(anchor=W)
    @property
    def unit_type(self):
        return self._unit_type.get()

class Watcher:
    def __init__(self):
        self.watched_item = None
    def show(self, newWatched):
        self.clear()
        self.watched_item = newWatched
        self.watched_item.watcher = self #tell new watched item that it is being watched
        enable_frame(self)
        for part in self.parts:
            self.parts[part].set(take_care_of_lists(self.watched_item.__getattribute__(part))) #load in this item's settings
    def update_display(self, name):
        def f(*args):
            if len(args) == 0:
                val = self.parts[name].get() #in case command callback doesn't give us any new value info
            else: val = args[0]
            self._update_display(name, val)
            if name == 'frozen': #(un)freezing changes which should be displayed;
                #updating both lets them figure out who it should be
                self.update_display('logit')()
                self.update_display('frozenlogit')()
        return f
    def _update_display(self, name, value):
        if self.watched_item:
            if name == 'nonlinearity':
                setattr(self.watched_item, name, possible_nonlinearities[value][0])
                setattr(self.watched_item, 'nonlinearity_deriv', possible_nonlinearities[value][1])
            else: setattr(self.watched_item, name, float(value))
    def clear(self):
        if self.watched_item:
            self.watched_item.watcher = None #tell previous item that it is no longer being watched
            self.watched_item = None
        disable_frame(self)

class Checkerybutton(Checkbutton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable = kwargs['variable']
    def get(self):
        return self.variable.get()
    def set(self, newval):
        self.variable.set(newval)

class UnitConfigFrame(Frame, Watcher):
    def __init__(self, master):
        Watcher.__init__(self)
        super().__init__(master)
        self.pack(side=LEFT, fill=X, expand=True)
        self.parts = {}
        numberparts = ['logit', 'frozenlogit', 'delta', 'output', 'outdelta', 'derivative']#, 'hidden_state']
        booleanparts = ['frozen', 'recurrent']
        self.parts['dropout'] = Scale(master=self, from_=0, to=1)
        for part in numberparts:
            self.parts[part] = Scale(master=self, from_=-MAXVAL, to=MAXVAL)
        for part in self.parts: self.parts[part].config(resolution=-1, label=part, orient=HORIZONTAL, digits=4)
        for part in booleanparts:
            self.parts[part] = Checkerybutton(master=self, text=part, variable=IntVar())
        self.functions_holder = Frame(self)
        nonlin_selected = StringVar()
        for nl in possible_nonlinearities:
            Radiobutton(self.functions_holder, text=nl, variable=nonlin_selected, value=nl, command=self.update_display('nonlinearity')).pack()
        for part in self.parts:
            self.parts[part].config(command=self.update_display(part))
        
        self.parts['nonlinearity'] = nonlin_selected
        
        #Label(self, textvariable=self.parts['nonlinearity']).grid()
        self.parts['dropout'].grid(row=0)
        self.parts['frozen'].grid(row=1)
        self.parts['recurrent'].grid(row=2)
        
        self.functions_holder.grid(column=1, row=0, rowspan=3)
        
        self.parts['logit'].grid(column=2, row=0)
        self.parts['frozenlogit'].grid(column=2, row=1)
        #self.parts['hidden_state'].grid(column=2, row=2)
        self.parts['output'].grid(column=2, row=2)
        
        self.parts['delta'].grid(column=3, row=0)
        self.parts['derivative'].grid(column=3, row=1)
        self.parts['outdelta'].grid(column=3, row=2)
        

class ConnectionConfigFrame(Frame, Watcher):
    def __init__(self, master):
        Watcher.__init__(self)
        super().__init__(master, width=1)
        self.pack(side=LEFT, fill=X, expand=True)
        typeaparts = ['value', 'moment', 'delta_accumulator', 'previous_delta']
        typebparts = ['plasticity', 'momentum', 'decay']
        self.parts = {}
        for part in typeaparts:
            self.parts[part] = Scale(master=self, from_=-MAXVAL, to=MAXVAL)
        for part in typebparts:
            self.parts[part] = Scale(master=self, from_=0, to=1)
        for part in self.parts:
            self.parts[part].config(resolution=-1, label=part, orient=HORIZONTAL, digits=4, command=self.update_display(part))
        self.parts['value'].grid(row=0, columnspan=2)
        self.parts['plasticity'].grid(row=1)
        self.parts['momentum'].grid(row=2)
        self.parts['decay'].grid(row=3)
        self.parts['moment'].grid(row=1, column=1)
        self.parts['delta_accumulator'].grid(row=2, column=1)
        self.parts['previous_delta'].grid(row=3, column=1)


"""
need button to start/stop forward/backward
need slider to change speed of forward/backward
"""
class RunFrame(Frame):
    pass

class App(Frame):
    def __init__(self, master=None):
        #if master not init'd, will use current root window or create one automatically I think
        super().__init__(master)
        self.master.minsize(height=600, width=1000)
        self.master.title("Neural Network Simulation")
        self.pack(fill=BOTH, expand=True)
        
        
        
        self.config(cursor='cross')
        self.canvas = Canvas(self, bg='white')
        self.canvas.pack(side=TOP, fill=BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.addunit)
        self.master.bind("q", lambda e: self.master.destroy())
        
        self.configbar = Frame(master=self)
        self.configbar.pack(side=TOP, fill=X)
        
        self.options = OptionsFrame(self.configbar)
        
        self.connectionconfig = ConnectionConfigFrame(self.configbar)
        
        self.unitconfig = UnitConfigFrame(self.configbar)
        
        self.message = StringVar()
        Label(master=self, height=0, justify=LEFT, anchor=W, textvariable=self.message, bg='gray').pack(side=BOTTOM, fill=X)
        self.message.set("Starting...")
        
        #default internal values
        self.startunit = None
        self.clicked_on_a_unit = False #See http://stackoverflow.com/a/14480311 - both canvas and unit callbacks were firing
        self.clicked_on_a_connection = False
    def addunit(self, event): #fires when we click on any area of the canvas
        if self.clicked_on_a_unit:
            self.connectionconfig.clear()
            self.clicked_on_a_unit = False
            return #get out of here if we have clicked inside a unit
        if self.clicked_on_a_connection:
            self.unitconfig.clear()
            self.clicked_on_a_connection = False
            return
        if self.startunit: #we're not trying to add a connection
            #the above test wasn't called, but we still have a unit ready to be added
            self.connectionconfig.clear()
            self.unitconfig.clear()
            self.startunit = None #reset our selection if we click on an empty area of the canvas
        else:
            if self.options.unit_type == 'hidden':
                GUnit(self.canvas, (event.x, event.y), [])
            elif self.options.unit_type == 'input':
                GInputUnit(self.canvas, (event.x, event.y), [])
            elif self.options.unit_type == 'output':
                GOutputUnit(self.canvas, (event.x, event.y))
    def addconnection(self, unit): #creates a method bound to each specific unit
        return lambda event: self._addconnection(unit, event)
    def _addconnection(self, targetunit, event): #fires when we click on a unit on the canvas
        if self.clicked_on_a_connection:
            return
        self.clicked_on_a_unit = True
        self.unitconfig.show(targetunit)
        if self.startunit: #we already have a unit to start with
            self.startunit.add_output(targetunit, GConnection(self.canvas, self.startunit.position, targetunit.position))
            self.startunit = None
        self.startunit = targetunit
    def configconnection(self, connection):
        return lambda event: self._configconnection(connection, event)
    def _configconnection(self, connection, event):
        self.clicked_on_a_connection = True
        self.connectionconfig.show(connection)



if __name__ == '__main__':
    print("Starting simulation...")
    root = Tk()
    app = App(root)
    root.mainloop()

#end
