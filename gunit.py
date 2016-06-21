from tkinter import *
from units import Unit, InputUnit, OutputUnit
from units import Connection

MAXVAL = Connection.max_magnitude

def value_to_color(val, minval = -MAXVAL, maxval = MAXVAL):
    #val is a float, which should be in [-maxval, maxval]
    #but that clipping will already be taken care of in Connection class
    if minval is None: minval = -MAXVAL
    if maxval is None: maxval = MAXVAL
    ###Need to handle case where val is a list - just use last item in list
    if hasattr(val, "__iter__"): #acts like a list
        if val: val = val[-1]
        else: val = 0
    color = (val - minval) / (maxval - minval)
    color *= 16**6 #like a html color code
    color = max(0, min(int(color), 16**6-1))
    color = "#{:06x}".format(color)
    return color
tocolor = value_to_color


class GConnection(Connection):
    def __init__(self, canvas, startpos, endpos, *args, **kwargs):
        print("Adding connection from {} to {}.".format(startpos, endpos))
        self.canvas = canvas
        self.id = self.canvas.create_line(*startpos, *endpos, fill='black', width=4)
        super().__init__(*args, **kwargs)
    @property
    def value(self):
        return super().value
    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.canvas.itemconfig(self.id, fill=tocolor(self.value))

class Graphic:
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

class GUnit(Unit):
    def __init__(self, canvas, position, *args, **kwargs):
        print("Adding {} unit at {}, {}".format(str(type(self)), *position))
        self.canvas = canvas
        self.graphic = Graphic(self, canvas, position)
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
        self.pack()
        self._unit_type = StringVar()
        self._unit_type.set('hidden')
        Radiobutton(self, text='Input Unit', variable=self._unit_type, value='input', indicatoron=0).pack(anchor=W)
        Radiobutton(self, text='Hidden Unit', variable=self._unit_type, value='hidden', indicatoron=0).pack(anchor=W)
        Radiobutton(self, text='Output Unit', variable=self._unit_type, value='output', indicatoron=0).pack(anchor=W)
    @property
    def unit_type(self):
        return self._unit_type.get()

class App(Frame):
    def __init__(self, master=None):
        #if master not init'd, will use current root window or create one automatically I think
        super().__init__(master)
        self.pack()
        self.config(cursor='cross')
        self.canvas = Canvas(self)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.addunit)
        self.master.bind("q", lambda e: self.master.destroy())
        
        #default internal values
        self.options = OptionsFrame(self)
        self.startunit = None
        self.clicked_on_a_unit = False #See http://stackoverflow.com/a/14480311 - both canvas and unit callbacks were firing
    def addunit(self, event): #fires when we click on any area of the canvas
        if self.clicked_on_a_unit:
            self.clicked_on_a_unit = False
            return #get out of here if we have clicked inside a unit
        if self.startunit: #we're not trying to add a connection
            #the above test wasn't called, but we still have a unit ready to be added
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
        self.clicked_on_a_unit = True
        if self.startunit: #we already have a unit to start with
            self.startunit.add_output(targetunit, GConnection(self.canvas, self.startunit.position, targetunit.position))
            self.startunit = None
        else: #we don't have a unit to start with, so set this as the starting unit.
            self.startunit = targetunit


if __name__ == '__main__':
    print("Starting simulation...")
    root = Tk()
    root.title("Neural Network Simulation")
    app = App(root)
    root.mainloop()

#end
