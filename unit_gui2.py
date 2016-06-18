from tkinter import *
from units import Unit
from units import Connection

SIZE = 10

def value_to_color(val):
    return val
v_to_c = value_to_color

class GConnection(Connection):
    def __init__(self, canvas, startpos, endpos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas = canvas
        self.id = self.canvas.create_line(*startpos, *endpos, fill='black')
    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.canvas.config(self.id, fill=v_to_c(self.value))

class GUnit(Unit):
    def __init__(self, canvas, position, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas = canvas
        self.id = self.canvas.create_rectangle(*position, position[0]+SIZE, position[1]+SIZE, fill="black", anchor='S')
        self.position = position
    @property
    def position(self):
        return self.canvas.coords(self.id)
    @position.setter
    def position(self, newposition):
        self.canvas.coords(self.id, *newposition)
    ##now extend things that change unit properties to change gunit properties

class OutputWindow(Canvas):
    def __init__(self, master):
        super().__init__(master)

if __name__ == '__main__':
    print("HI")
