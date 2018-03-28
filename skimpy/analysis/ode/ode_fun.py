# -*- coding: utf-8 -*-
"""
.. module:: skimpy
   :platform: Unix, Windows
   :synopsis: Simple Kinetic Models in Python

.. moduleauthor:: SKiMPy team

[---------]

Copyright 2017 Laboratory of Computational Systems Biotechnology (LCSB),
Ecole Polytechnique Federale de Lausanne (EPFL), Switzerland

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from numpy import array, double
from sympy import symbols
from sympy.utilities.autowrap import ufuncify


class ODEFunction:
    def __init__(self, variables, expr, parameters):
        """
        Constructor for a precompiled function to solve the ode epxressions
        numerically
        :param variables: a list of strings with variables names
        :param expr: dict of sympy expressions for the rate of
                     change of a variable indexed by the variable name
        :param parameters: dict of parameters with parameter values

        """
        self.variables = variables
        self.expr = expr
        self.parameters = parameters
        self._parameter_values = []

        # Unpacking is needed as ufuncify only take ArrayTypes
        the_param_keys = [x for x in self.parameters]
        the_variable_keys = [x for x in variables]
        sym_vars = list(symbols(the_variable_keys+the_param_keys))

        # Sort the expressions
        the_expressions = [self.expr[x] for x in self.variables.values()]

        # Awsome sympy magic
        self.function = []
        for exp in the_expressions:
           self.function.append(ufuncify(tuple(sym_vars),
                                         exp,
                                         backend='Cython'))

    @property
    def parameter_values(self):
        if not self._parameter_values:
            raise ArgumentError('No parameters have been set')
        else:
            return self._parameter_values

    @parameter_values.setter
    def parameter_values(self,value):
        """
        Would-be optimization hack to avoid looking up thr whole dict at each
        iteration step in __call__

        :param value:
        :return:
        """
        #self._parameters = value
        self._parameter_values = [value[x] for x in self.parameters.values()]


    def __call__(self,t,y):
        input_vars = list(y)+self.parameter_values
        #result = self.functin
        array_input = [array([input_var], dtype=double) for input_var in  input_vars  ]
        results = [f(*array_input)[0] for f in self.function ]
        return array(results)
