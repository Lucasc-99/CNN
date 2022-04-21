from typing import Union
import numpy as np
import itertools


class Tensor:
    """
    Matrix with differentiable operations

    supports: +, -, *, /, **, log, exp, relu, sigmoid

    Refactored from https://github.com/karpathy/micrograd/blob/master/micrograd/engine.py
    """

    unique_id = itertools.count()

    def __init__(
        self,
        data: Union[np.ndarray, int, float, list],
        _children: tuple = (),
        _op: str = "None",
    ):
        self.data = Tensor._validate_init_input(data)
        self.id = next(self.unique_id)
        self._children = _children
        self.grad = np.zeros_like(self.data)
        self._prev = set(_children)
        self._backward = lambda: None
        self._op = _op

    def __add__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(np.add(self.data, other.data), (self, other), _op="+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward

        return out

    def __mul__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(np.multiply(self.data, other.data), (self, other), _op="*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward

        return out

    def __pow__(self, other):

        other: Tensor = Tensor._validate_input(other)

        out = Tensor(
            self.data**other.data, (self,), _op="pow"
        )  # Add other to children when below is fixed

        def _backward():
            self.grad += (other.data * self.data ** (other.data - 1)) * out.grad

            # TODO: fix this, exp grad not implemented as of now
            """
            if np.any(other.data):
                temp = other.grad + (
                    (self.data ** other.data)
                    * np.ma.log(np.abs(other.data))
                    * out.grad
                )
                other.grad = temp
            """

        out._backward = _backward

        return out

    def __rpow__(self, other):
        other: Tensor = Tensor._validate_input(other)

        return other**self

    def log(self):
        out = Tensor(np.log(self.data), (self,), _op="log")

        def _backward():
            self.grad += (1 / self.data) * out.grad

        out._backward = _backward

        return out

    def sigmoid(self):
        out = Tensor(
            np.exp(self.data) / (np.exp(self.data) + 1), (self,), _op="sigmoid"
        )

        def _backward():
            self.grad += (
                np.exp(self.data)
                / ((np.exp(self.data) + 1) * (np.exp(self.data) + 1))
                * out.grad
            )

        out._backward = _backward

        return out

    def relu(self):
        out = Tensor(self.data * (self.data > 0), (self,), _op="relu")

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

    def __hash__(self):
        return self.id

    def __getitem__(self, key):
        raise NotImplementedError("Tensor indexing not implemented")

    @staticmethod
    def mat_vec_mul(mat, vec):
        """
        Multiply matrix with vector using np.matmul
        Note: transform not needed for vec, as it is done automatically by numpy
        """
        mat = Tensor._validate_input(mat)
        vec = Tensor._validate_input(vec)

        out = Tensor(np.matmul(mat.data, vec.data), (mat, vec), _op="mat_vec_mul")

        def _backward():
            mat.grad += np.outer(out.grad.T, vec.data)
            vec.grad += np.matmul(mat.data.T, out.grad)

        out._backward = _backward
        return out

    @staticmethod
    def sum1d(tensor_in):
        """
        Sum across all values in a 1d tensor in 1 operation,
        mitigating graph blowup
        """
        assert len(tensor_in.data.shape) == 1, "Input tensor must be 1d"

        out = Tensor(np.longdouble([np.sum(tensor_in.data)]), (tensor_in,), _op="sum1d")

        def _backward():
            tensor_in.grad += np.full_like(tensor_in.grad, out.grad)

        out._backward = _backward

        return out

    @staticmethod
    def cat1d(tensors: list):
        """
        Concatenate a list of 1 dimensional Tensors along first axis

        """
        out = Tensor(
            np.concatenate([t.data for t in tensors], axis=0),
            tuple(tensors),
            _op="cat1d",
        )

        def _backward():
            for i in range(len(tensors)):
                tensors[i].grad += out.grad[i]

        out._backward = _backward

        return out

    @staticmethod
    def _validate_init_input(input):
        assert isinstance(input, (np.ndarray, int, float, list)), f"{type(input)}"

        if isinstance(input, int):
            return np.longdouble([float(input)])

        elif isinstance(input, float):
            return np.longdouble([input])

        elif isinstance(input, list):
            return np.longdouble([float(d) for d in input])

        elif isinstance(input, np.ndarray):
            assert input.dtype in (
                np.longdouble,
                np.float,
                np.single,
                np.double,
            ), "dtype must be float"
            return input

    @staticmethod
    def _validate_input(input):

        if isinstance(input, np.ndarray):
            return Tensor(input, ())

        elif isinstance(input, Tensor):
            return input

        elif isinstance(input, (int, float, list)):
            return Tensor(input, ())

        else:
            raise NotImplementedError(
                f"Tensor operations for {type(input)} not implemented"
            )
