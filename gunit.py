from tkinter import *
from units import Unit, InputUnit, OutputUnit
from units import Connection
import weakref
import nonlinearities as nl

MAXVAL = Connection.max_magnitude

def disable_frame(frame):
    frame.pack_forget()
def enable_frame(frame):
    frame.pack()

def take_care_of_lists(value):
    if hasattr(value, "__iter__"): #acts like a list
        if value: value = value[-1]
        else: value = 0
    elif hasattr(value, '__call__'): #acts like a function
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

class MessageDisplay:
    @classmethod
    def start(cls):
        cls.message = StringVar()
    @classmethod
    def set(cls, newmessage):
        cls.message.set(newmessage)

class Watchable:
    def __setattr__(self, name, value):
        if not 'watcher' in self.__dict__:
            super().__setattr__('watcher', None)
        if name != 'watcher':
            super().__setattr__(name, value)
        if name == 'watcher':
            if value:
                super().__setattr__('watcher', weakref.ref(value))
            else:
                super().__setattr__('watcher', None)
            if 'graphic' in self.__dict__:
                if value is None:
                    self.dehighlight()
                else:
                    self.highlight()
        elif self.watcher and name in self.watcher().parts: #if we're being watched
            if name in ('nonlinearity', 'nonlinearity_deriv'):
                if self.watcher().parts[name].get() != value.__name__:
                    self.watcher().parts[name].set(value.__name__)
                    self.watcher().recalc_bounds()
            else:
                if self.watcher().parts[name].get() != value: #if it doesn't already know what's happening
                    self.watcher().parts[name].set(value) #let the watcher know what's happening
    def highlight(self):
        pass
    def dehighlight(self):
        pass
    def remove(self):
        MessageDisplay.set("Deleting {}".format(self))
        if self.watcher and self.watcher():
            self.watcher().clear()
        self.graphic.remove()

class ConnectionGraphic(Frame):
    def __init__(self, con, canvas, startpos, endpos):
        self._c = con #create a circular reference so we don't get garbage collected
        self.canvas = canvas
        self.ids = {'value': self.canvas.create_line(*startpos, *endpos, fill='black', width=5, stipple='gray25')}
        for part in self.ids:
            self.canvas.tag_bind(self.ids[part], "<Button-1>", self.canvas.master.configconnection(weakref.ref(con)))
    def recolor(self, what, value, minval=None, maxval=None):
        self.canvas.itemconfig(self.ids[what], fill=tocolor(value, minval, maxval))
    def remove(self):
        for part in self.ids:
            self.canvas.delete(self.ids[part])
        del self._c #remove circular reference, so we can be garbage collected

class GConnection(Connection, Watchable):
    def __init__(self, canvas, startunit, endunit, *args, **kwargs):
        if 'startpos' not in kwargs:
            startpos = (startunit.position[0]+UnitGraphic.bigsize+2*UnitGraphic.smallsize, startunit.position[1])
        else:
            startpos = kwargs['startpos']
            del kwargs['startpos']
        if 'endpos' not in kwargs:
            endpos = endunit.position
        else:
            endpos = kwargs['endpos']
            del kwargs['endpos']
        MessageDisplay.set("Creating connection from {} to {}.".format(startpos, endpos))
        self.graphic = ConnectionGraphic(self, canvas, startpos, endpos)
        self.canvas = canvas
        super().__init__(*args, **kwargs)
        self.startunit = startunit
        self.endunit = endunit
    @property
    def value(self):
        return super().value
    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.graphic.recolor('value', self.value)
    def highlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], width=8, stipple='gray50')
    def dehighlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], width=5, stipple='gray25')
    def delete(self):
        self.startunit.remove_outgoing_weight(self)
        self.remove()

class UnitGraphic(Frame):
    bigsize = 20
    smallsize = 10
    def __init__(self, unit, canvas, position):
        self._u = unit #create a circular reference so unit objects are not deleted
        self.unit = weakref.ref(unit)
        self.canvas = canvas
        self.positions = {}
        self.find_bounds(position)
        self.gen_graphic()
        self.canvas.addtag_withtag('unit', self.ids['_derivative'])
        for piece in self.ids:
            self.canvas.tag_bind(self.ids[piece], "<Button-1>", self.canvas.master.addconnection(self.unit))
        super().__init__(master=canvas, width=0, height=0)
        self.checktags()
    def find_bounds(self, mainposition):
        mp = mainposition
        self.positions['logit'] = (*mp, mp[0]+self.smallsize, mp[1]+self.bigsize)
        self.positions['activation'] = (mp[0]+self.smallsize, mp[1], mp[0]+self.bigsize+2*self.smallsize, mp[1]+self.bigsize)
        self.positions['indelta'] = (mp[0], mp[1]+self.bigsize, mp[0]+self.smallsize, mp[1]+self.bigsize+self.smallsize)
        self.positions['_derivative'] = (mp[0]+self.smallsize, mp[1]+self.bigsize, mp[0]+self.smallsize+self.bigsize, mp[1]+self.bigsize+self.smallsize)
        self.positions['outdelta'] = (mp[0]+self.smallsize+self.bigsize, mp[1]+self.bigsize, mp[0]+2*self.smallsize+self.bigsize, mp[1]+self.bigsize+self.smallsize)
        if isinstance(self.unit(), OutputUnit):
            self.positions['target'] = (mp[0]+self.bigsize+2*self.smallsize, mp[1], mp[0]+self.bigsize+3*self.smallsize, mp[1]+self.bigsize+self.smallsize)
            self.positions['cost_val'] = (mp[0], mp[1]+self.smallsize+self.bigsize, mp[0]+self.bigsize+3*self.smallsize, mp[1]+self.bigsize+2*self.smallsize)
        if isinstance(self.unit(), InputUnit):
            self.positions['logit'] = (
                    mp[0]-self.smallsize, mp[1],
                    mp[0]+self.smallsize, mp[1],
                    mp[0]+self.smallsize, mp[1]+self.bigsize,
                    mp[0], mp[1]+self.bigsize,
                    mp[0], mp[1]+self.bigsize+self.smallsize,
                    mp[0]-self.smallsize, mp[1]+self.bigsize+self.smallsize)
    def gen_graphic(self):
        self.ids = {}
        for key in self.positions.keys():
            if key=='logit' and isinstance(self.unit(), InputUnit):
                self.ids['logit'] = self.canvas.create_polygon(*self.positions['logit'], fill=tocolor(0,0,1), outline='black', width=1)
            else:
                self.ids[key] = self.canvas.create_rectangle(*(self.positions[key]), fill=tocolor(0, 0, 1))
    @property
    def position(self):
        pos = self.canvas.bbox(self.ids['logit'])[:2]
        if isinstance(self.unit(), InputUnit):
            return (pos[0]+self.smallsize, pos[1])
        else:
            return pos
    @position.setter
    def position(self, newposition):
        self.find_bounds(newposition)
        for key, item in self.ids.items():
            self.canvas.coords(item, *self.positions[key])
    def recolor(self, what, value, minval=None, maxval=None):
        self.canvas.itemconfig(self.ids[what], fill=tocolor(value, minval, maxval))
    def checktags(self):
        tags = self.canvas.itemcget(self.ids['_derivative'], 'tags')
        if 'forward' in tags and 'forward_done' not in tags:
            self.unit().go()
            self.canvas.addtag_withtag('forward_done', self.ids['_derivative'])
        if 'backprop' in tags and 'backprop_done' not in tags:
            self.unit().backprop()
            self.canvas.addtag_withtag('backprop_done', self.ids['_derivative'])
        if 'reset' in tags:
            self.unit().reset()
            self.cleartags()
        if 'remove' in tags:
            self._u.delete()
        self.after(20, self.checktags)
    def cleartags(self):
        self.canvas.itemconfig(self.ids['_derivative'], tags='unit')
    def remove(self):
        for part in self.ids:
            self.canvas.delete(self.ids[part])
        del self._u #remove final reference to this object in the program

class GUnit(Unit, Watchable):
    def __init__(self, canvas, position, *args, **kwargs):
        MessageDisplay.set("Creating {} unit at {}".format(str(type(self).__name__), position))
        self.canvas = canvas
        self.graphic = UnitGraphic(self, canvas, position)
        self.position = position
        super().__init__(*args, **kwargs)
    @property
    def position(self):
        return self.graphic.position
    @position.setter
    def position(self, newposition):
        self.graphic.position = newposition
    #use __setattr__ to so that changes to unit properties update the graphic's colors
    def __setattr__(self, name, val):
        super().__setattr__(name, val)
        if name in ('logit', 'frozenlogit'):
            self.graphic.recolor('logit', self.frozenlogit if self.frozen else self.logit)
        elif name == 'output':
            self.graphic.recolor('activation', self.output)
        elif name == 'delta':
            self.graphic.recolor('indelta', self.delta)
        elif name in ('_derivative', 'outdelta', 'target', 'cost_val'):
            self.graphic.recolor(name, val)
        elif name == 'recurrent':
            if bool(val): #if we're making it recurrent
                if not self in self.outputs: #make sure we aren't already
                    self.add_output(self, GConnection(self.canvas, self, self))
            else: #if we're taking away recurrency / init saying we don't have it
                self.remove_output(self)
    def highlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], outline='yellow', width=3)
    def dehighlight(self):
        for part in self.graphic.ids:
            self.canvas.itemconfig(self.graphic.ids[part], outline='black', width=1)
    def add_output(self, output, weight=None, weight_val=None):
        if weight is None or not isinstance(weight, GConnection):
            weight = GConnection(self.canvas, self, output)
        if weight_val is not None:
            weight.value = weight_val
        super().add_output(output, weight)
    def delete(self):
        while len(self.incoming_weights) > 0:
            weight = self.incoming_weights[0]
            weight.delete()
        while len(self.weights) > 0:
            weight = self.weights[0]
            weight.delete()
        self.remove()

class GInputUnit(GUnit, InputUnit):
    def __init__(self, canvas, position, *args, **kwargs):
        GUnit.__init__(self, canvas, position)
        InputUnit.__init__(self, *args, **kwargs)
    def reset(self):
        logit = self.logit
        super().reset()
        self.logit = logit
    def forward(self):
        logit = self.logit
        super().forward()
        self.logit = logit

class GOutputUnit(GUnit, OutputUnit):
    def __init__(self, canvas, position, *args, **kwargs):
        GUnit.__init__(self, canvas, position)
        OutputUnit.__init__(self, *args, **kwargs)
        self.target = 0
        self.cost_val = 0
    def backprop(self):
        self.cost_val = super().cost(self.target)
    def reset(self):
        target = self.target
        super().reset()
        self.cost_val = 0
        self.target = target

class OptionsFrame(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(side=LEFT)
        self._unit_type = StringVar()
        self._unit_type.set('hidden')
        Radiobutton(self, text='Input Unit', variable=self._unit_type, value='input',
                    indicatoron=0, command=lambda: MessageDisplay.set("New units will be input units")).pack(anchor=W)
        Radiobutton(self, text='Hidden Unit', variable=self._unit_type, value='hidden',
                    indicatoron=0, command=lambda: MessageDisplay.set("New units will be hidden units")).pack(anchor=W)
        Radiobutton(self, text='Output Unit', variable=self._unit_type, value='output',
                    indicatoron=0, command=lambda: MessageDisplay.set("New units will be output units")).pack(anchor=W)
    @property
    def unit_type(self):
        return self._unit_type.get()

class Watcher:
    def __init__(self):
        self.watched_item = None
        self.deletebutton = Button(master=self, text="Delete this item", command=self.delete)
    def show(self, newWatched):
        self.clear()
        MessageDisplay.set("Now viewing/editing {}".format(newWatched))
        self.watched_item = newWatched
        self.watched_item.watcher = self #tell new watched item that it is being watched
        enable_frame(self)
        if isinstance(self.watched_item, Unit):
            if isinstance(self.watched_item, OutputUnit):
                self.parts['target'].grid()
                self.parts['cost_val'].grid()
            else:
                self.parts['target'].grid_remove()
                self.parts['cost_val'].grid_remove()
        for part in self.parts:
            if part in ('target', 'cost_val') and not isinstance(self.watched_item, OutputUnit): continue
            self.parts[part].set(take_care_of_lists(self.watched_item.__getattribute__(part)))#load in this item's settings/values
        self.recalc_bounds()
    def update_display(self, name):
        def f(*args):
            if len(args) == 0:
                val = self.parts[name].get() #in case command callback doesn't give us any new value info, get it
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
                new_nonlin = nl.possible_nonlinearities[value]
                setattr(self.watched_item, name, new_nonlin[0])
                setattr(self.watched_item, 'nonlinearity_deriv', new_nonlin[1])
                self.recalc_bounds()
            else: setattr(self.watched_item, name, float(value))
    def clear(self):
        if self.watched_item:
            self.watched_item.watcher = None #tell previous item that it is no longer being watched
        self.watched_item = None
        disable_frame(self)
    def delete(self):
        MessageDisplay.set("Deleting...")
        #remove all references to watched_item so it can be garbage collected
        if self.watched_item:
            self.watched_item.canvas.master.startunit = None
            self.watched_item.canvas.master.clicked_on_a_unit = False
            self.watched_item.delete()
            self.clear()

class Checkerybutton(Checkbutton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable = kwargs['variable']
    def get(self):
        return self.variable.get()
    def set(self, newval):
        self.variable.set(int(newval))
        if self.get(): self.select()
        else: self.deselect()

class UnitConfigFrame(Frame, Watcher):
    def __init__(self, master):
        super().__init__(master)
        Watcher.__init__(self)
        self.pack(side=LEFT, fill=X, expand=True)
        self.parts = {}
        numberparts = ['logit', 'frozenlogit', 'delta', 'output', 'outdelta', '_derivative', 'target', 'cost_val']
        booleanparts = ['frozen', 'recurrent']
        self.parts['dropout'] = Scale(master=self, from_=0, to=1)
        for part in numberparts:
            self.parts[part] = Scale(master=self, from_=-MAXVAL, to=MAXVAL)
        for part in self.parts: self.parts[part].config(resolution=-1, label=part, orient=HORIZONTAL, digits=4)
        for part in booleanparts:
            self.parts[part] = Checkerybutton(master=self, text=part, variable=IntVar())
        self.functions_holder = Frame(self)
        nonlin_selected = StringVar()
        for functionname in nl.possible_nonlinearities:
            Radiobutton(self.functions_holder, text=functionname, variable=nonlin_selected,
                        value=functionname, command=self.update_display('nonlinearity')).pack()
        for part in self.parts:
            self.parts[part].config(command=self.update_display(part))
        
        self.parts['nonlinearity'] = nonlin_selected
        
        self.parts['dropout'].grid(row=0)
        self.parts['frozen'].grid(row=1)
        self.parts['recurrent'].grid(row=2)
        
        self.functions_holder.grid(column=1, row=0, rowspan=3)
        
        self.parts['logit'].grid(column=2, row=0)
        self.parts['frozenlogit'].grid(column=2, row=1)
        self.parts['output'].grid(column=2, row=2)
        
        self.parts['delta'].grid(column=3, row=0)
        self.parts['_derivative'].grid(column=3, row=1)
        self.parts['outdelta'].grid(column=3, row=2)
        
        self.parts['target'].grid(column=4, row=0)
        self.parts['cost_val'].grid(column=4, row=1)
        self.deletebutton.grid(column=4, row=2)
    def recalc_bounds(self):
        new_nonlin = nl.possible_nonlinearities[self.parts['nonlinearity'].get()]
        low = new_nonlin[2]
        if low==None: low = -MAXVAL
        high = new_nonlin[3]
        if high==None: high = MAXVAL
        self.parts['output'].config(from_=low, to=high)
        self.parts['target'].config(from_=low, to=high)

class ConnectionConfigFrame(Frame, Watcher):
    def __init__(self, master):
        super().__init__(master, width=1)
        Watcher.__init__(self)
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
        self.deletebutton.grid(column=2, row=0, rowspan=3)

class RunFrame(Frame):
    time_delta = 10 #in milliseconds
    def __init__(self, master, canvas):
        super().__init__(master)
        self.canvas = canvas
        self.line = self.canvas.create_line(0, 0, 0, self.canvas.winfo_height(), width=10, stipple='gray12', dash=(1,2,2,1))
        self.canvas.bind("<Configure>", self.resize_line)
        buttons = ['forward', 'pause', 'backprop']
        self.selected = StringVar()
        for button in buttons:
            Radiobutton(self, text=button, variable=self.selected, value=button).pack(side=LEFT)
        self.selected.set('pause')
        self.speed = IntVar() #speeds in pixels per second
        Scale(master=self, label='Speed (px/s)', orient=HORIZONTAL, resolution=10, variable=self.speed,
            from_=10, to=1000, width=20).pack(side=LEFT)
        self.speed.set(500)
        Button(master=self, text='Reset all units', command=self.reset).pack(side=LEFT)
        self.autoreset = Checkerybutton(master=self, text='Auto reset units', variable=IntVar())
        self.autoreset.set(True)
        self.autoreset.pack(side=LEFT)
        self.pack(side=TOP, fill=X)
        self.previous_command=self.selected.get()
        self.update_position()
    def resize_line(self, event):
        oldcoords = self.canvas.coords(self.line)
        self.canvas.coords(self.line, oldcoords[0], 0, oldcoords[2], event.height)
    def update_position(self):
        command = self.selected.get()
        if command != self.previous_command:
            MessageDisplay.set("Now {}ing".format(command))
            self.previous_command = command
        if command == 'pause':
            self.after(200, self.update_position)
            return
        deltax = (self.time_delta * 0.001) * self.speed.get() #seconds*(pixels/second)
        maxposition = self.canvas.winfo_width()
        minposition = 0
        if command == 'pause':
            deltax = 0
        elif command == 'backprop':
            deltax *= -1
        oldcoords = self.canvas.coords(self.line)
        newx = max(minposition, min(oldcoords[0]+deltax, maxposition))
        deltax = newx - oldcoords[0]
        self.canvas.move(self.line, deltax, 0)
        
        for unit in self.find_intersecting():
            self.canvas.addtag_withtag(command, unit)
        
        if ((oldcoords[0] == maxposition and command == 'forward')
            or (oldcoords[0] == minposition and command == 'backprop')):
                self.selected.set('pause')
                if self.autoreset.get() and command=='backprop': self.reset()
        self.after(self.time_delta, self.update_position)
    def find_intersecting(self):
        if self.selected.get() in ('forward', 'backprop'):
            overlap=set(self.canvas.find_overlapping(*self.canvas.bbox(self.line)))
            units = set(self.canvas.find_withtag('unit'))
            already=set(self.canvas.find_withtag(self.selected.get() + '_done'))
            chosen_units = (overlap & units) - already
        else:
            chosen_units = set()
        return chosen_units
    def reset(self):
        self.selected.set("pause")
        self.canvas.move(self.line, -self.canvas.coords(self.line)[0], 0)
        self.canvas.addtag_withtag("reset", "unit")
        MessageDisplay.set("Reset units")

class App(Frame):
    def __init__(self, master=None):
        #if master not init'd, will use current root window or create one automatically I think
        super().__init__(master)
        self.master.minsize(height=600, width=800)
        self.master.title("Neural Network Simulation")
        self.config(cursor='cross')
        self.pack(fill=BOTH, expand=True)
        
        self.canvas = Canvas(self, bg='white')
        self.runner = RunFrame(self, self.canvas)
        
        self.canvas.pack(side=TOP, fill=BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.addunit)
        self.master.bind("q", lambda e: self.master.destroy())
        
        self.configbar = Frame(master=self, height=300)
        self.configbar.pack(side=TOP, fill=X)
        
        self.options = OptionsFrame(self.configbar)
        
        self.connectionconfig = ConnectionConfigFrame(self.configbar)
        disable_frame(self.connectionconfig)
        
        self.unitconfig = UnitConfigFrame(self.configbar)
        disable_frame(self.unitconfig)
        
        MessageDisplay.start()
        Label(master=self, height=0, justify=LEFT, anchor=W, textvariable=MessageDisplay.message, bg='gray', relief=SUNKEN).pack(side=BOTTOM, fill=X)
        MessageDisplay.set("Starting...")
        
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
        #If we get to this point, we should reset our selection because we clicked on an empty area of the canvas
        if self.startunit:
            self.unitconfig.clear()
            self.startunit = None
        elif self.connectionconfig.watched_item:
            self.connectionconfig.clear()
        else:
            if self.options.unit_type == 'hidden':
                GUnit(self.canvas, (event.x, event.y), [])
            elif self.options.unit_type == 'input':
                GInputUnit(self.canvas, (event.x, event.y), [])
            elif self.options.unit_type == 'output':
                GOutputUnit(self.canvas, (event.x, event.y))
    def addconnection(self, unitref): #creates a method bound to each specific unit
        return lambda event: self._addconnection(unitref, event)
    def _addconnection(self, targetunitref, event): #fires when we click on a unit on the canvas
        if self.clicked_on_a_connection:
            return
        self.clicked_on_a_unit = True
        self.unitconfig.show(targetunitref())
        if self.startunit: #we already have a unit to start with
            if self.startunit is targetunitref(): self.startunit.recurrent=not self.startunit.recurrent
            else: self.startunit.add_output(targetunitref(), GConnection(self.canvas, self.startunit, targetunitref()))
            self.startunit = None
        self.startunit = targetunitref()
    def configconnection(self, connectionref):
        return lambda event: self._configconnection(connectionref, event)
    def _configconnection(self, connectionref, event):
        self.startunit = None #cancel any ideas we had before about linking units
        self.clicked_on_a_connection = True
        self.connectionconfig.show(connectionref())



if __name__ == '__main__':
    root = Tk()
    app = App(root)
    root.mainloop()

