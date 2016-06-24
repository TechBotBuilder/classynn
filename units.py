import numpy as np
#from scipy.special import expit as sigmoid
from math import exp
def sigmoid(x): return 1/(1+exp(-x))

def linear(x): return x
def dlinear(y): return 1

class Connection:
    max_magnitude = 10
    def __init__(self, value=np.random.randn, plasticity=0.01, momentum=0.6, decay=0):
        if hasattr(value, '__call__'):
            self.value = value()
        else:
            self.value = value
        self.momentum = momentum
        self.plasticity = plasticity
        self.moment = 0.0
        self.decay = decay
        self.delta_accumulator = 0.0
        self.previous_delta = 0
    def update(self, delta, commit = True, momentum = True, prop = False, adaptive_learning_rate = False, clip=True):
        self.delta_accumulator += delta
        if clip:
            self.delta_accumulator = np.clip(self.delta_accumulator, -10, 10)
        if commit:
            if adaptive_learning_rate:
                reduce = np.sign(self.previous_delta) != np.sign(self.previous_delta)
                if reduce:
                    self.plasticity *= 0.95
                else:
                    self.plasticity += 0.05
                self.plasticity = np.clip(self.plasticity, -1, 1)
            if momentum:
                self.value -= self.plasticity * (self.moment + self.delta_accumulator + self.decay * self.value)
                self.moment += self.delta_accumulator
                self.moment *= self.momentum
            elif prop:
                self.value -= self.plasticity * np.sign(self.delta_accumulator)
            else:
                self.value -= self.plasticity * self.delta_accumulator
            self.previous_delta = self.delta_accumulator
            self.delta_accumulator = 0
            self.value = np.clip(self.value, -self.max_magnitude, self.max_magnitude)
    def commit(self):
        self.update(0)
    def nesterov(self):
        self.value -= self.plasticity * self.moment
        self.moment *= self.momentum
    def get(self):
        return self.value
    def __mul__(self, other):
        return self.value * other
    def __str__(self):
        return "Weight " + str(self.value)
    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, newvalue):
        self._value = newvalue

def dsigmoid(x, fromLogit=False):
    if fromLogit:
        x = sigmoid(x)
    return x * (1.0-x)

class Unit:
    """
    - Unit constructor
    """
    def __init__(self, outputs=[], nonlinearity=sigmoid, nonlinearity_deriv=dsigmoid, dropout=0.0, recurrent=False):
        self.outputs = outputs
        self.dropout = dropout
        self.nonlinearity = nonlinearity
        self.nonlinearity_deriv = nonlinearity_deriv
        self.frozen = False
        self.logit = 0
        self.frozenlogit = 0
        self.hidden_state = []
        self.derivative = []
        self._derivative = 0
        self.recurrent = recurrent
        self.weights = [Connection() for output in self.outputs]
        if self.recurrent:
            self.outputs.append(self)
            self.weights.append(Connection())
        self.delta = 0
        self.output = 0
        self.outdelta = 0
    
    """Move current output value along weights"""
    def send(self, target=None):
        if target:
            self.outputs[target].recieve(self.weights[target] * self.output)
        else:
            for output, weight in zip(self.outputs, self.weights):
                output.recieve(weight * self.output)
    
    """Update own input state when other unit sends data in"""
    def recieve(self, data):
        if self.frozen:
            self.frozenlogit += data
        else:
            self.logit += data
    
    """Push own input state through """
    def forward(self):
        self.output = self.nonlinearity(self.logit)
        self.hidden_state.append(self.output)
        self._derivative = self.nonlinearity_deriv(self.logit)
        self.derivative.append(self._derivative)
        self.logit = 0
    
    """This is what people should call."""
    def go(self):
        self.forward()
        self.send()
    
    """If you want to make recurrent stuff, it might be a good idea to use this.
    It keeps the logit from updating until it is unfrozen."""
    def freeze(self):
        self.frozen = True
    def thaw(self):
        self.logit = self.frozenlogit
        self.frozenlogit = 0
        self.frozen = False
    
    def reset(self):
        self.logit = 0
        self.frozenlogit = 0
        self.hidden_state = []
        self.frozen = False
        self.outdelta = 0
        self.delta = 0
        self.output = 0
        self._derivative = 0
        self.derivative = []
    
    def backprop(self, commit = True):
        delta = 0
        stuff = self.hidden_state.pop()
        for output, weight in zip(self.outputs, self.weights):
            delta += weight * output.delta
            weight.update(output.delta * stuff, commit)
        self.outdelta = delta
        self.delta = delta * self.derivative.pop()
        if self.derivative: self._derivative = self.derivative[-1]
        else: self._derivative = 0
    
    def add_output(self, output, weight=None):
        self.outputs.append(output)
        new_weight = Connection()
        self.weights.append(new_weight)
        if not weight is None:
            if isinstance(weight, Connection):
                self.weights[-1] = weight
            else:
                new_weight.value = weight
    
    def __str__(self):
        return "Unit: logit {},\thidden state: {}".format(self.logit, self.output)

class Group:
    def __init__(self, size, outputs, nonlinearity=sigmoid, nonlinearity_deriv=dsigmoid, dropout=0.0, self_recurrent=False, recurrent_interconnected=False):
        self.units = []
        for unitID in range(size):
            self.units.append(Unit(outputs, nonlinearity, nonlinearity_deriv, dropout, self_recurrent))
        if recurrent_interconnected:
            for unit in self.units:
                for unit2 in self.units:
                    if unit != unit2:
                        unit.outputs.append(unit2)
                        unit.weights.append(Connection())
    def freeze(self):
        for unit in self.units:
            unit.freeze()
    def thaw(self):
        for unit in self.units:
            unit.thaw()
    
    def go(self):
        self.freeze()
        for unit in self.units:
            unit.go()
        self.thaw()
    
    def reset(self):
        for unit in self.units:
            unit.reset()
    
    def backprop(self):
        for unit in self.units:
            unit.backprop()

    def __str__(self):
        result = ""
        for unit in self.units:
            result += str(unit) + "\n"
            for weight in unit.weights:
                result += str(weight) + "\n"
        return result

class InputUnit(Unit):
    def __init__(self, outputs=[], *args, **kwargs):
        super().__init__(outputs, linear, dlinear, *args, **kwargs)
    def update(self, value):
        self.logit = value

class InputGroup(Group):
    def __init__(self, size, outputs, dropout=0):
        self.units = []
        for unitID in range(size):
            self.units.append(InputUnit(outputs, dropout))
    def update(self, values):
        for unit, value in zip(self.units, values):
            unit.update(value)

class OutputUnit(Unit):
    def __init__(self, cost_function=lambda y,t: (y-t)**2, cost_derivative=lambda y,t: y-t, *args, **kwargs):
        super().__init__([], *args, **kwargs)
        self.cost_function = cost_function
        self.cost_derivative = cost_derivative
    def cost(self, target):
        output = self.hidden_state.pop()
        internal_deriv = self.derivative.pop()
        if self.outputs:
            #re-add internal hidden state and derivative because backprop re-removes them
            self.hidden_state.append(output)
            self.derivative.append(internal_deriv)
            self.backprop()
        cost_val = self.cost_function(output, target)
        dcost = self.cost_derivative(output, target)
        self.outdelta = dcost
        self.delta = dcost * internal_deriv
        if self.derivative: self._derivative = self.derivative[-1]
        else: self._derivative = 0
        return cost_val

class OutputGroup(Group):
    def __init__(self, size, nonlinearity, nonlinearity_deriv, cost_function, cost_derivative, dropout=0):
        self.units = []
        for unitID in range(size):
            self.units.append(OutputUnit(nonlinearity, nonlinearity_deriv, cost_function, cost_derivative, dropout))
    def cost(self, targets):
        cost_val = 0
        for unit, target in zip(self.units, targets):
            cost_val += unit.cost(target)
        return (cost_val / len(self.units))

if __name__ == "__main__":
    from sys import argv as runtime_args

"""if __name__ == "__main__":
    print("Beginning. Enter a nonnumber to quit.")
    outputs = Group(1, [])
    hiddens = Group(2, outputs.units)
    inputs = InputGroup(1, hiddens.units)
    layers = [inputs, hiddens, outputs]
    for layer in layers:
        print(layer)
    while True:
        data = input("Enter a number >")
        try:
            data = float(data)
        except:
            break
        inputs.update([data])
        for layer in layers:
            layer.go()
        print("Output given {}: {}".format(data, outputs.units[0].hidden_state))
    print("Done.")
"""

"""if __name__ == "__main__":
    print("Starting...")
    outputs = OutputGroup(1, lambda x: x, lambda x: 1, lambda x, t: (x-t)**2, lambda x, t: x-t)
    inputs = InputGroup(1, outputs.units)
    print(inputs)
    print(outputs)
    while True:
        x = input("Input: ")
        y = input("Output: ")
        try:
            x, y = float(x), float(y)
        except:
            break
        inputs.update([x])
        inputs.go()
        outputs.go()
        print("Output given {}: {}".format(x, outputs.units[0].hidden_state))
        print("Cost: " + str(outputs.cost([y])))
        print(inputs.units[0].weights[0])
        inputs.backprop()
    print("Done!")"""

if __name__ == "__main__":
    print("starting")
    xs = [-1, 1]
    ys = [1, -1]
    runs = 10000
    inputU = InputUnit([])
    inputU.add_output(inputU)
    if len(runtime_args) > 1:
        inputU.weights[0].value = float(runtime_args[1])
    for _a in range(runs+1):
        data_index = _a % len(xs)
        #if _a % (runs // 10) == 0:
        #    print("Weight started at {}".format(inputU.weights[0].value))
        inputU.update(xs[data_index])
        for _ in range(3):
            inputU.go()
        inputU.forward()
        dcost = inputU.hidden_state.pop() - ys[data_index]
        inputU.delta = dcost * inputU.derivative.pop()
        for _ in range(3):
            inputU.backprop(False)
        inputU.weights[0].commit()
        inputU.reset()
        if _a % (runs // 10) == 0:
            print("Weight is now {}".format(inputU.weights[0].value))

"""if __name__ == "__main__":
    print("starting")
    thing = 2
    weights = [a/10 for a in range(-10, 11)]
    input = InputUnit([])
    input.add_output(input)
    for _a in range(len(weights)):
        input.weights[0].value = weights[_a]
        print("Weight of {}".format(weights[_a]))
        input.update(thing)
        for _ in range(3):
            input.go()
        input.forward()
        cost = (input.hidden_state - (-thing)) ** 2
        print("Gives a cost of {}\n".format(cost))"""
