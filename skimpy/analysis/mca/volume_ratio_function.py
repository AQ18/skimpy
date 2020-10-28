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

from numpy import array, double, zeros
from numpy import append as append_array

from sympy import symbols

from skimpy.utils.tabdict import TabDict
from skimpy.utils.compile_sympy import make_cython_function

class VolumeRatioFunction:
    def __init__(self, model, variables,  parameters, pool=None):
        """
        Constructor for a precompiled function to compute elasticities
        numerically
        :param variables: a list of strings denoting
                                      the independent variables names
        :param expressions: dict of  non-zero sympy expressions for the rate of
                            change of a variable indexed by a tuple of the matrix position
                            e.g: (1,1)
        :param parameters:  list of parameter names
        :param shape: Tuple defining the over all matrix size e.g (10,30)

        """
        self.variables = variables
        self.parameters = parameters

        # Unpacking is needed as ufuncify only take ArrayTypes
        parameters = [x for x in self.parameters]
        variables = [x for x in variables]

        sym_vars = list(symbols(variables+parameters))

        # Derive expression
        expr_dict = TabDict([(k,v.compartment.parameters.cell_volume.symbol/
                            v.compartment.parameters.volume.symbol )
                           for k,v in model.reactants.items()])

        expressions= [expr_dict[v] for v in variables]

        self.expressions = expressions

        # Awsome sympy magic
        # TODO problem with typs if any parameter ot variables is interpreted as interger
        # Make a function to compute every non zero entry in the matrix

        self.function = make_cython_function(sym_vars, expressions, pool=pool, simplify=True)

    def __call__(self, variables, parameters):
        """
        Return a sparse matrix type with elasticity values
        """
        parameter_values = array([parameters[x.symbol] for x in
                                  self.parameters.values()], dtype=double)

        input_vars = append_array(variables , parameter_values)

        values = array(zeros(len(self.expressions)),dtype=double)

        self.function(input_vars, values)


        return values

