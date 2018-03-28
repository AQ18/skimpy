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
WITHOUT WARRANTIE CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from abc import ABC, abstractmethod
from collections import namedtuple

import numpy as np
from numpy.random import sample
from scipy.sparse.linalg import eigs as eigenvalues
from sympy import sympify


class ParameterSampler(ABC):
    def __init__(self, parameters=None):
        """

        :param parameters:
        """
        self.parameters = parameters

    @property
    @abstractmethod
    def Parameters(self):
        """
        Parameter type specified for the parameters samples
        :return:
        """

    @abstractmethod
    def sample(self):
        """

        :return:
        """


class SimpleParameterSampler(ParameterSampler):
    """
    A simple parameter sampler that samples stable model parameters
    with respect to a steady state flux and concentration state
    """

    Parameters = namedtuple('Parameters', ['n_samples'])
    # TODO Talk to Pierre / Misko about simple sampler parameters
    # if parameters are not defined put default values
    Parameters.__new__.__defaults__ = (None,) * len(Parameters._fields)

    def sample(self, compiled_model, flux_dict, concentration_dict):

        parameter_population = []

        # Unpack fluxes and concentration into arrays consitent with the
        # compiled functions

        fluxes = [flux_dict[this_reaction.name] for this_reaction in
                  compiled_model.reactions.values()]
        concentrations = np.array([concentration_dict[this_variable] for
                  this_variable in compiled_model.variables.keys()])

        trials = 0
        while (len(
                parameter_population) < self.parameters.n_samples) or trials > 1e6:


            try:

                parameter_sample = self._sample_saturations_step(compiled_model,
                                                                 concentration_dict,
                                                                 flux_dict)
            except ValueError:
                continue


            # Check stability: real part of all eigenvalues of the jacobian is <= 0

            this_jacobian = compiled_model.jacobian_fun(fluxes, concentrations,
                                                        parameter_sample)
            largest_eigenvalue = eigenvalues(this_jacobian, k=1, which='LR',
                                             return_eigenvectors=False)
            is_stable = largest_eigenvalue <= 0

            compiled_model.logger.info('Model is stable? {} '
                                       '(max real part eigv: {}'.
                                       format(is_stable,largest_eigenvalue))

            if is_stable:
                parameter_population.append(parameter_sample)

            # Count the trials
            trials += 1

        return parameter_population

    def _sample_saturations_step(self, compiled_model, concentration_dict,
                                 flux_dict):
        parameter_sample = compiled_model.parameters.copy()
        # Sample parameters for every reaction
        for this_reaction in compiled_model.reactions.values():

            keq_param = this_reaction.parameters.k_equilibrium
            vmax_param = this_reaction.parameters.vmax_forward

            this_parameters = {
                keq_param.symbol: keq_param.value,
                vmax_param.symbol: 1.0}

            # Loop over the named tuple
            for this_p_name, this_parameter in this_reaction.parameters.items():
                # Sample a saturation
                # The parameters that have to be sampled are attached to
                # reactants. hence, their .hook attribute shall not be None

                if this_parameter.hook is not None:
                    this_saturation = sample()
                    # TODO THIS IS A HOT FIX AND REALLY STUPID REMOVE ASAP
                    # TODO - OK, removed.
                    this_reactant = this_parameter.hook.name
                    this_concentration = concentration_dict[this_reactant]
                    this_param_symbol = this_parameter.symbol
                    this_parameters[this_param_symbol] = \
                        ((1.0 - this_saturation) * this_concentration) / this_saturation

            # Calculate the vmax
            this_net_reaction_rate = this_reaction.mechanism.reaction_rates[
                'v_net']
            this_parameter_subs = concentration_dict.copy()
            this_parameter_subs.update(this_parameters.copy())

            normed_net_reaction_rate = this_net_reaction_rate.evalf(
                subs=this_parameter_subs)
            this_vmax = flux_dict[this_reaction.name] / normed_net_reaction_rate
            if 1:#this_vmax < 0:
                msg = 'Vmax for reaction {} is negative {}'.format(this_reaction.name,
                                                          this_vmax)
                compiled_model.logger.error(msg)
                # raise ValueError(msg)
            # print('Vmax of %s is %0.1f',this_reaction.name,this_vmax)
            this_parameters[vmax_param.symbol] = this_vmax

            # Update the dict with explicit model parameters
            parameter_sample.update(this_parameters)
        return parameter_sample
