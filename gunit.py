from tkinter import *
from units import Unit
from units import Connection

MAXVAL = Connection.max_magnitude

def value_to_color(val, minval = -MAXVAL, maxval = MAXVAL):
    #val is a float, which should be in [-maxval, maxval]
    #but that clipping will already be taken care of in Connection class
    if minval is None: minval = -MAXVAL
    if maxval is None: maxval = MAXVAL
    color = (val - minval) / (maxval - minval)
    color *= 16**6 #like a html color code
    color = max(0, min(int(color), 16**6-1))
    color = "#{:06x}".format(color)
    return color
tocolor = value_to_color


class GConnection(Connection):
    def __init__(self, canvas, startpos, endpos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas = canvas
        self.id = self.canvas.create_line(*startpos, *endpos, fill='black')
    @property
    def value(self):
        return super().value
    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.canvas.itemconfig(self.id, fill=tocolor(self.value))

class Graphic:
    def __init__(self, canvas, position):
        self.canvas = canvas
        self.positions = {}
        self.find_bounds(position)
        self.gen_graphic(position)
    def find_bounds(self, mainposition):
        mp = mainposition
        bigsize = 10
        smallsize = 5
        self.positions['logit'] = (*mp, mp[0]+smallsize, mp[1]+bigsize)
        self.positions['activation'] = (*mp, mp[0]+bigsize+2*smallsize, mp[1]+bigsize+smallsize)
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
        for key, item in self.ids:
            self.canvas.coords(item, *self.positions[key])
    def recolor(self, what, value, minval=None, maxval=None):
        self.canvas.itemconfig(self.ids[what], fill=tocolor(value, minval, maxval))

class GUnit(Unit):
    def __init__(self, canvas, position, *args, **kwargs):
        self.canvas = canvas
        self.graphic = Graphic(canvas, position)
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


class App(Canvas):
    def __init__(self, master=None):
        #if master not init'd, will use current root window or create one automatically I think
        super().__init__(master)
        self.pack()
        self.config(cursor='cross')
        self.bind("<Button-1>", self.addunit)
        self.master.bind("q", lambda e: self.master.destroy())
    def addunit(self, event):
        print("HE")
        GUnit(self, (event.x, event.y), [])


if __name__ == '__main__':
    print("HI")
    root = Tk()
    root.title("Neural Network Simulation")
    app = App(root)
    root.mainloop()

#end
