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

from math import log

from rlgraph import get_backend
from rlgraph.utils.util import SMALL_NUMBER
from rlgraph.components.component import Component
from rlgraph.components.layers.nn.dense_layer import DenseLayer
from rlgraph.components.layers.preprocessing.reshape import ReShape
from rlgraph.spaces import Space, IntBox, FloatBox, ContainerSpace
from rlgraph.spaces.space_utils import sanity_check_space
from rlgraph.utils.ops import DataOpTuple

if get_backend() == "tf":
    import tensorflow as tf


class ActionAdapter(Component):
    """
    A Component that cleans up a neural network's flat output and gets it ready for parameterizing a
    Distribution Component.
    Processing steps include:
    - Sending the raw, flattened NN output through a Dense layer whose number of units matches the flattened
        action space.
    - Reshaping (according to the action Space).
    - Translating the reshaped outputs into logits (raw), probabilities and log-probabilities.

    API:
        get_action_layer_output(nn_output) (SingleDataOp): The raw, non-reshaped output of the action-layer
            (DenseLayer) after passing through it the raw nn_output (coming from the previous Component).
        get_logits_parameters_log_probs(nn_output) (Tuple[SingleDataOp x 3]):
            1) raw nn_output, BUT reshaped
            2) probabilities (softmaxed (1))
            3) log(probabilities)
    """
    def __init__(self, action_space, add_units=0, units=None, weights_spec=None, biases_spec=None, activation=None,
                 scope="action-adapter", **kwargs):
        """
        Args:
            action_space (Space): The action Space within which this Component will create actions.
            add_units (Optional[int]): An optional number of units to add to the auto-calculated number of action-
                layer nodes. Can be negative to subtract units from the auto-calculated value.
                NOTE: Only one of either `add_units` or `units` must be provided.
            units (Optional[int]): An optional number of units to use for the action-layer. If None, will calculate
                the number of units automatically from the given action_space.
                NOTE: Only one of either `add_units` or `units` must be provided.
            weights_spec (Optional[any]): An optional RLGraph Initializer spec that will be used to initialize the
                weights of `self.action layer`. Default: None (use default initializer).
            biases_spec (Optional[any]): An optional RLGraph Initializer spec that will be used to initialize the
                biases of `self.action layer`. Default: None (use default initializer, which is usually 0.0).
            activation (Optional[str]): The activation function to use for `self.action_layer`.
                Default: None (=linear).
        """
        super(ActionAdapter, self).__init__(scope=scope, **kwargs)

        self.action_space = action_space.with_batch_rank()
        self.weights_spec = weights_spec
        self.biases_spec = biases_spec
        self.activation = activation

        # Our (dense) action layer representing the flattened action space.
        self.action_layer = None

        # Calculate the number of nodes in the action layer (DenseLayer object) depending on our action Space
        # or using a given fixed number (`units`).
        # Also generate the ReShape sub-Component and give it the new_shape.
        if isinstance(self.action_space, IntBox):
            if units is None:
                units = add_units + self.action_space.flat_dim_with_categories
            self.reshape = ReShape(
                new_shape=self.action_space.get_shape(with_category_rank=True),
                flatten_categories=False
            )
        else:
            if units is None:
                units = add_units + 2 * self.action_space.flat_dim  # Those two dimensions are the mean and log sd
            # Manually add moments after batch/time ranks.
            new_shape = tuple([2] + list(self.action_space.shape))
            self.reshape = ReShape(new_shape=new_shape)

        assert units > 0, "ERROR: Number of nodes for action-layer calculated as {}! Must be larger 0.".format(units)

        # Create the action-layer and add it to this component.
        self.action_layer = DenseLayer(
            units=units,
            activation=self.activation,
            weights_spec=self.weights_spec,
            biases_spec=self.biases_spec,
            scope="action-layer"
        )

        self.add_components(self.action_layer, self.reshape)

    def check_input_spaces(self, input_spaces, action_space=None):
        # Check the input Space.
        last_nn_layer_space = input_spaces["nn_output"]  # type: Space
        sanity_check_space(last_nn_layer_space, non_allowed_types=[ContainerSpace])

        # Check the action Space.
        sanity_check_space(self.action_space, must_have_batch_rank=True)
        if isinstance(self.action_space, IntBox):
            sanity_check_space(self.action_space, must_have_categories=True)
        else:
            # Fixme: Are there other restraints on continuous action spaces? E.g. no dueling layers?
            pass

    def get_action_layer_output(self, nn_output):
        """
        Args:
            nn_output (DataOpRecord): The NN output of the preceding neural network.

        Returns:
            DataOpRecord: The output of the action layer (a DenseLayer) after passing `nn_output` through it.
        """
        return self.call(self.action_layer.apply, nn_output)

    def get_logits_parameters_log_probs(self, nn_output):
        """
        Args:
            nn_output (DataOpRecord): The NN output of the preceding neural network.

        Returns:
            tuple (3x DataOpRecord):
                - The output of the action layer (a DenseLayer) after passing `nn_output` through it.
        """
        action_layer_output = self.call(self.get_action_layer_output, nn_output)
        action_layer_output_reshaped = self.call(self.reshape.apply, action_layer_output)
        probs_and_log_probs = self.call(self._graph_fn_get_parameters_log_probs, action_layer_output_reshaped)
        return (action_layer_output_reshaped,) + probs_and_log_probs

    # TODO: Use a SoftMax Component instead (uses the same code as the one below).
    def _graph_fn_get_parameters_log_probs(self, logits):
        """
        Creates properties/parameters and log-probs from some reshaped output.

        Args:
            logits (SingleDataOp): The output of some layer that is already reshaped
                according to our action Space.

        Returns:
            tuple (2x SingleDataOp):
                parameters (DataOp): The parameters, ready to be passed to a Distribution object's
                    get_distribution API-method (usually some probabilities or loc/scale pairs).
                log_probs (DataOp): Simply the log(parameters).
        """
        if get_backend() == "tf":
            if isinstance(self.action_space, IntBox):
                # Discrete actions.
                parameters = tf.maximum(x=tf.nn.softmax(logits=logits, axis=-1), y=SMALL_NUMBER)
                # Log probs.
                log_probs = tf.log(x=parameters)
            elif isinstance(self.action_space, FloatBox):
                # Continuous actions.
                mean, log_sd = tf.split(value=logits, num_or_size_splits=2, axis=1)
                # Remove moments rank.
                mean = tf.squeeze(input=mean, axis=1)
                log_sd = tf.squeeze(input=log_sd, axis=1)

                # Clip log_sd. log(SMALL_NUMBER) is negative.
                log_sd = tf.clip_by_value(t=log_sd, clip_value_min=log(SMALL_NUMBER), clip_value_max=-log(SMALL_NUMBER))

                # Turn log sd into sd.
                sd = tf.exp(x=log_sd)

                parameters = DataOpTuple(mean, sd)
                log_probs = DataOpTuple(tf.log(x=mean), log_sd)
            else:
                raise NotImplementedError

            return parameters, log_probs
