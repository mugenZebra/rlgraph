# Copyright 2018 The YARL-Project, All Rights Reserved.
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

from yarl.components.memories.memory import Memory
import tensorflow as tf


class ReplayMemory(Memory):
    """
    Implements a standard replay memory to sample randomized batches.
    """

    def __init__(
        self,
        record_space,
        capacity=1000,
        name="",
        scope="replay-memory",
        sub_indexes=None,
        next_states=True
    ):
        super(ReplayMemory, self).__init__(record_space, capacity, name, scope, sub_indexes)

        # Variables.
        self.index = None
        self.size = None
        self.states = None
        self.next_states = next_states

        # Add Sockets and Computations.
        self.define_inputs("records")
        self.define_outputs("insert")
        self.add_computation("records", "insert", "insert")

    def create_variables(self):
        super(ReplayMemory, self).create_variables()

        # Main buffer index.
        self.index = self.get_variable(name="index", dtype=int, trainable=False, initializer=0)
        # Number of elements present.
        self.size = self.get_variable(name="size", dtype=int, trainable=False, initializer=0)
        if self.next_states:
            # Next states are not represented as explicit keys in the registry
            # as this would cause extra memory overhead.
            self.states = self.record_space["states"].keys()

    def _computation_insert(self, records):
        num_records = tf.shape(records.keys()[0])
        index = self.read_variable(self.index)
        update_indices = tf.range(start=index, stop=index + num_records) % self.capacity

        # Updates all the necessary sub-variables in the record.
        record_updates = self.record_space.flatten(mapping=lambda key, primitive: self.scatter_update_variable(
            variable=self.record_registry[key],
            indices=update_indices,
            updates=records[key]
        ))

        # Update indices and size.
        with tf.control_dependencies(control_inputs=list(record_updates.values())):
            index_updates = list()
            index_updates.append(self.assign_variable(variable=self.index, value=(index + num_records) % self.capacity))
            update_size = tf.minimum(x=(self.read_variable(self.size) + num_records), y=self.capacity)
            index_updates.append(self.assign_variable(self.size, value=update_size))

        # Nothing to return.
        with tf.control_dependencies(control_inputs=index_updates):
            return tf.no_op()

    def read_records(self, indices):
        """
        Obtains record values for the provided indices.

        Args:
            indices Union[ndarray, tf.Tensor]: Indices to read. Assumed to be not contiguous.

        Returns:
             dict: Record value dict.
        """

        records = dict()
        for name, variable in self.record_registry:
            records[name] = self.read_variable(variable, indices)
        if self.next_states:
            next_indices = (indices + 1) % self.capacity
            next_states = dict()
            # Next states are read via index shift from state variables.
            for state_name in self.states:
                next_states = self.read_variable(self.record_registry[state_name], next_indices)
            records["next_states"] = next_states

        return records

    def _computation_get_records(self, num_records):
        indices = tf.range(start=0, limit=self.read_variable(self.size))
        if self.next_states:
            # Valid indices are non-terminal indices.
            terminal_indices = self.read_variable(self.record_registry['terminal'])
            indices = tf.boolean_mask(tensor=indices, mask=tf.logical_not(x=terminal_indices))
        # Choose with uniform probability from all valid indices.
        samples = tf.multinomial(tf.ones_like(indices), num_samples=num_records)

        # Slice sampled indices from all indices.
        sampled_indices = indices[tf.cast(samples[0][0], tf.int32)]

        return self.read_records(indices=sampled_indices)