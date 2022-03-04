from typing import Tuple, Union
import numpy as np


class Tensor:
    """
    Matrix with differentiable operations

    supports: +, -, *, /, **, log, exp, relu, sigmoid

    Refactored from https://github.com/karpathy/micrograd/blob/master/micrograd/engine.py
    """

    def __init__(
        self, data: Union[np.ndarray, int, float, list], _children: Tuple = ()
    ):
        assert isinstance(data, (np.ndarray, int, float, list))
        self.data = data if isinstance(data, np.ndarray) else np.array(data)


        self._children = _children
        self.grad = np.zeros_like(data)

        self.backward = None

    def __add__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(self.data + other.data, (self, other))

        def _backward():
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward

        return out

    def __mul__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(self.data * other.data, (self, other))

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward

        return out

    def __pow__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(self.data**other.data, (self, other))

        def _backward():
            self.grad += (other.data * self.data ** (other.data - 1)) * out.grad

            # may cause log(0) err
            if np.any(other.data):
                mask = other.data > 0
                other.grad[mask] += (
                    (self.data[mask] ** other.data[mask])
                    * np.log(np.abs(other.data[mask]))
                    * out.grad[mask]
                )

        out._backward = _backward

        return out

    def __rpow__(self, other):
        other: Tensor = Tensor._validate_input(other)

        return other**self

    def log(self):
        out = Tensor(np.log(self.data), (self,), f"log")

        def _backward():
            self.grad += (1 / self.data) * out.grad

        out._backward = _backward

        return out


    def sigmoid(self):

        out = Tensor(np.exp(self.data) / (np.exp(self.data) + 1), (self,))

        def _backward():
            self.grad += (
                np.exp(self.data) / ((np.exp + 1) * (np.exp(self.data) + 1)) * out.grad
            )

        out._backward = _backward

        return out

    def relu(self):
        out = Tensor(self.data * (self.data > 0), (self,))

        def _backward():
            self.grad += (out.data > 0) * out.grad

        out._backward = _backward

        return out

    def __gt__(self, other):
        return self.data > Tensor._validate_input(other).data

    def __lt__(self, other):
        return self.data < Tensor._validate_input(other).data

    def __ge__(self, other):
        return self.data >= Tensor._validate_input(other).data

    def __eq__(self, other):
        return self.data == Tensor._validate_input(other).data

    def __neg__(self):  # -self
        return self * -1

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return self * other**-1

    def __rtruediv__(self, other):
        return other * self**-1

    def backward(self):
        nodes = []
        visited = set()

        def topological_sort(v):
            if v not in visited:
                visited.add(v)
                for child in set(v._children):
                    topological_sort(child)
                nodes.append(v)

        topological_sort(self)

        self.grad = np.ones_like(self.grad)
        for v in reversed(nodes):
            v._backward()

    def __repr__(self):
        return f"Tensor with val {self.data} and grad {self.grad}"

    def __getitem__(self, key):
        raise NotImplementedError("Tensor indexing not implemented")

    @staticmethod
    def cat(tensors):
        """
        Concatenate a list of Tensors along first axis
        """
        data_tuple = tuple([t.data for t in tensors])
        out = Tensor(np.concatenate(data_tuple, axis=0), tuple(tensors))

        def _backward():
            for i in range(len(tensors)):
                tensors[i].grad += out.grad[i]
        
        out._backward = _backward
        
        return out

    @staticmethod
    def _validate_input(input):

        if isinstance(input, np.ndarray):
            return Tensor(input, ())

        elif isinstance(input, Tensor):
            return input

        elif isinstance(input, (int, float, list)):
            return Tensor(np.array(input), ())

        else:
            raise NotImplementedError(
                f"Tensor operations for {type(input)} not implemented"
            )
