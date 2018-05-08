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

import numpy as np

import pytfa
from pytfa.io import import_matlab_model, load_thermoDB

from skimpy.core import *
from skimpy.mechanisms import *
from skimpy.utils.namespace import *

from skimpy.sampling import SimpleParameterSampler
from skimpy.core.solution import ODESolutionPopulation
from skimpy.io.generate_from_pytfa import FromPyTFA


this_cobra_model = import_matlab_model('../models/toy_model.mat','ToyModel_DP')

""" Make tfa analysis of the model """

thermo_data = load_thermoDB('../data/thermo_data.thermodb')
this_pytfa_model = pytfa.ThermoModel(thermo_data, this_cobra_model)

GLPK = 'optlang-glpk'
this_pytfa_model.solver = GLPK

## TFA conversion
this_pytfa_model.prepare()
this_pytfa_model.convert(add_displacement=True)
solution = this_pytfa_model.optimize()

""" Sample flux an concentration values"""



""" Get a Kinetic Model """
# Generate the KineticModel
model_gen = FromPyTFA(water='h_2o')
this_skimpy_model = model_gen.import_model(this_pytfa_model)

# Compile MCA functions
this_skimpy_model.compile_mca(sim_type=QSSA)

# Initialize parameter sampleer
sampling_parameters = SimpleParameterSampler.Parameters(n_samples=100)
sampler = SimpleParameterSampler(sampling_parameters)

#parameter_population = sampler.sample(this_skimpy_model, flux_dict, concentration_dict)

#this_model.compile_ode(sim_type = 'QSSA')

