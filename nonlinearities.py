from math import exp

#predefine some nonlinearities for people to use
#remember derivatives are based on outputs - so y=sigmoid(x) -> dy/dx = y*(1-y)

def sigmoid(x): return 1/(1+exp(-x))
def dsigmoid(y): return y*(1-y)

from math import tanh
def dtanh(y): return 1 - y**2

def linear(x): return x
def dlinear(y): return 1

def rectified_linear(x): return max(0, x)
def drectified_linear(y): return int(y != 0)

possible_nonlinearities = {
    'sigmoid': (sigmoid, dsigmoid),
    'tanh': (tanh, dtanh),
    'linear': (linear, dlinear),
    'rectified_linear': (rectified_linear, drectified_linear)
    }
