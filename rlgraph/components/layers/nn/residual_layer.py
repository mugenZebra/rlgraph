# Copyright 2018 The RLgraph authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from rlgraph import get_backend
from rlgraph.components.layers.nn.activation_functions import get_activation_function
from rlgraph.components.layers.nn.nn_layer import NNLayer
from rlgraph.utils.util import get_rank

if get_backend() == "tf":
    import tensorflow as tf


class ResidualLayer(NNLayer):
    """
    A residual layer that adds the input value to some calculation. Based on:

    [1] Identity Mappings in Deep Residual Networks - He, Zhang, Ren and Sun (Microsoft) 2016
    (https://arxiv.org/pdf/1603.05027.pdf)

    API:
        apply(input_) ->
    """
    def __init__(self, residual_unit, repeats=2, scope="residual-layer", **kwargs):
        """
        Args:
            residual_unit (NeuralNetwork):
            repeats (int): The number of times that the residual unit should be repeated before applying the addition
                with the original input and the activation function.
        """
        super(ResidualLayer, self).__init__(scope=scope, **kwargs)

        self.repeats = repeats
        self.residual_units = [residual_unit] + [
            residual_unit.copy(scope=residual_unit.scope+"-rep"+str(i+1)) for i in range(repeats - 1)
        ]
        self.add_components(*self.residual_units)

    def _graph_fn_apply(self, inputs):
        """
        Args:
            inputs (SingleDataOp): The flattened inputs to this layer.

        Returns:
            SingleDataOp: The output after passing the input through n times the residual function, then the
                activation function.
        """
        if get_backend() == "tf":
            results = inputs
            # Apply the residual unit n times to the input.
            for i in range(self.repeats):
                results = self.call(self.residual_units[i].apply, results)

            # Then activate and add up.
            added_with_input = results + inputs
            activation_function = get_activation_function(self.activation, self.activation_params)
            if activation_function is not None:
                return activation_function(added_with_input)
            else:
                return added_with_input