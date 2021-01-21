# -*- coding: utf-8 -*-
"""
.. module:: skimpy
   :platform: Unix, Windows
   :synopsis: Simple Kinetic Models in Python

.. moduleauthor:: SKiMPy team

[---------]

Copyright 2020 Laboratory of Computational Systems Biotechnology (LCSB),
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
from pytfa.io.json import load_json_model

import numpy as np
import pandas as pd
from skimpy.core.modifiers import *
from skimpy.io.yaml import load_yaml_model
from skimpy.core.reactor import Reactor
from skimpy.analysis.oracle.load_pytfa_solution import load_concentrations
from skimpy.viz.plotting import timetrace_plot


CONCENTRATION_SCALING = 1e6 # 1 mol to 1 mmuol
TIME_SCALING = 1 # 1hr to 1min
# Parameters of the Yeast cell
DENSITY = 1200 # g/L
GDW_GWW_RATIO = 0.3 # Assumes 70% Water

#Load TFA model
path_to_tmodel = './../../models/tfa_varma.json'
tmodel = load_json_model(path_to_tmodel)

# Note that the models for strain_1 and strain_2 have parameters sets
# saved with in the model
kmodel_1 = load_yaml_model('./../../models/varma_strain_1.yml')
kmodel_2 = load_yaml_model('./../../models/varma_strain_2.yml')

reference_solutions = pd.read_csv('./../../data/tfa_reference_strains.csv', index_col=0)
ref_concentrations_strain_1 = load_concentrations(reference_solutions.loc['strain_1'], tmodel, kmodel_1,
                                                  concentration_scaling=CONCENTRATION_SCALING)

ref_concentrations_strain_2 = load_concentrations(reference_solutions.loc['strain_2'], tmodel, kmodel_2,
                                                   concentration_scaling=CONCENTRATION_SCALING)


# Scale vmax of growth reaction back to original units in the fba model i.e. 1gDW/1gDW/1hr
# TODO find a good solution todo this more consistently

flux_scaling_factor = 1e-3 / (GDW_GWW_RATIO / DENSITY) \
                      * CONCENTRATION_SCALING \
                      / TIME_SCALING

# LMPD_biomass_c_17_462/1e3 = GROWTH_RATE
biomass_scaling = {'strain_1': flux_scaling_factor/1000,
                   'strain_2': flux_scaling_factor/1000,
                   }

# define the volumes
kmodel_1.parameters.volume_c.value = 1.0 # 1muL
kmodel_2.parameters.volume_c.value = 1.0 # 1muL

# 1 L reactor
kmodel_1.parameters.volume_e.value = 1e15
kmodel_2.parameters.volume_e.value = 1e15


biomass_reactions = {'strain_1': kmodel_1.reactions.LMPD_biomass_c_17_462,
                     'strain_2': kmodel_2.reactions.LMPD_biomass_c_17_462
                     }

reactor = Reactor([kmodel_1, kmodel_2], biomass_reactions, biomass_scaling)

# Fix aerobic conditions i.e. constant oxygen supply
BC_o2_e = ConstantConcentration(reactor.variables.o2_e)
reactor.boundary_conditions['BC_o2_e'] = BC_o2_e
# # TODO THIS IS A STUPID HOT FIX FIND A SOULTION!!!!!
reactor.variables.o2_e.type = VARIABLE

# Fix aerobic conditions i.e. constant oxygen supply
BC_co2_e = ConstantConcentration(reactor.variables.co2_e)
reactor.boundary_conditions['BC_co2_e'] = BC_co2_e
# # TODO THIS IS A STUPID HOT FIX FIND A SOULTION!!!!!
reactor.variables.co2_e.type = VARIABLE

reactor.compile_ode(add_dilution=False)

# Biomass currently in numbers! TODO consistent and usefull scaling
reactor.initial_conditions['biomass_strain_1'] = 0.5e12
reactor.initial_conditions['biomass_strain_2'] = 0.5e12

reactor.initial_conditions['glc_D_e'] = 2.5*0.056*CONCENTRATION_SCALING #25g/l
reactor.initial_conditions['pi_e'] = 250*1e-3*CONCENTRATION_SCALING
reactor.initial_conditions['co2_e'] = 1e-7*CONCENTRATION_SCALING
reactor.initial_conditions['o2_e'] = 8e-3*0.062*CONCENTRATION_SCALING # 8 mg/L 1g = 0.062 mol
reactor.initial_conditions['h_e'] = 1e-7*CONCENTRATION_SCALING


# Get reference for
for r in ref_concentrations_strain_1.index:
    try:
        reactor.initial_conditions['strain_1_' + r] = ref_concentrations_strain_1[r]
    except KeyError:
        pass


for r in ref_concentrations_strain_2.index:
    try:
        reactor.initial_conditions['strain_2_' + r] = ref_concentrations_strain_2[r]
    except KeyError:
        pass



sol = reactor.solve_ode(np.linspace(0, 20.0, 1000),
                        solver_type='cvode',
                        rtol=1e-9,
                        atol=1e-9,
                        max_steps=1e9,
                        )

species = [s for s in sol.concentrations.columns if not s in ['biomass_strain_1', 'biomass_strain_2']]
timetrace_plot(sol.time, sol.concentrations[species].values/CONCENTRATION_SCALING,
               filename='output/time_response.html',
               legend=species,
               x_label='time [h]',
               y_label='concentrations [M]',)

MASS_PER_CELL = 1e-12 #[g]
species = ['biomass_strain_1', 'biomass_strain_2']
timetrace_plot(sol.time, sol.concentrations[species].values*MASS_PER_CELL,
               filename='output/time_response_biomass.html',
               legend=species,
               x_label='time [h]',
               y_label='biomass [g]')



species = ['biomass_strain_1', 'biomass_strain_2']
delta_x =  (sol.concentrations[species].values[1:,:] -  sol.concentrations[species].values[:-1,:])
delta_t = np.array(  [(sol.time[1:] -  sol.time[:-1])]*2).T
x = sol.concentrations[species].values[:-1,:]
mu = delta_x/delta_t/x
timetrace_plot(sol.time[:-1], mu,
               filename='output/time_response_growth.html',
               legend=species,
               x_label='time [h]',
               y_label='growth rate [1/h]',
               )

#Strain 1

species = ['strain_1_g6p_c','strain_1_f6p_c','strain_1_fdp_c', 'strain_1_g3p_c', 'strain_1_dhap_c', 'strain_1_atp_c', 'strain_1_adp_c']
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_glyc_strain_1.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')

species = ['strain_1_q8h2_c', 'strain_1_q8_c', 'strain_1_nad_c', 'strain_1_nadh_c']
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_etc_strain_1.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')


species = [ str(r.symbol) for r in reactor.models.strain_1.reactions.LMPD_biomass_c_17_462.reactants.values()]
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_biomass_precursors_strain_1.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')


#Strain 2
species = ['strain_2_g6p_c','strain_2_f6p_c','strain_2_fdp_c', 'strain_2_g3p_c', 'strain_2_dhap_c', 'strain_2_atp_c', 'strain_2_adp_c']
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_glyc_strain_2.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')

species = ['strain_2_q8h2_c', 'strain_2_q8_c', 'strain_2_nad_c', 'strain_2_nadh_c']
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_etc_strain_2.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')

species = [ str(r.symbol) for r in reactor.models.strain_2.reactions.LMPD_biomass_c_17_462.reactants.values()]
timetrace_plot(sol.time, (sol.concentrations[species]/sol.concentrations[species].loc[0]).values,
               filename='output/time_response_biomass_precursors_strain_2.html',
               legend=species,
               x_label='time [h]',
               y_label='relative concentration X/X_0 ')

# Medium
species = list(reactor.medium.keys())
timetrace_plot(sol.time, sol.concentrations[species].values/CONCENTRATION_SCALING,
               filename='output/time_response.html',
               legend=species,
               x_label='time [h]',
               y_label='concentrations [M]',)
