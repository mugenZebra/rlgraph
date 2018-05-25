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

from spaces.space import Space
import numpy as np
from cached_property import cached_property


class Discrete(Space):
    """
    A discrete space with n possible values represented by integers: {0,1,...,n-1}.
    """
    def __init__(self, n=None, num_actions=None, add_batch_rank=False, dtype="int32"):
        """
        Args:
            n (int): The number of discrete values.
            num_actions (int): Obsolete (use `n` instead!) The number of discrete values.
            dtype (str): The underlying data-type of this Space.
        """
        super(Discrete, self).__init__(add_batch_rank=add_batch_rank)
        self._dtype = dtype
        if num_actions is not None:
            n = num_actions
        self.n = n or 2

    @cached_property
    def shape(self):
        return ()

    @cached_property
    def shape_with_batch_rank(self):
        return self.batch_rank_tuple

    @cached_property
    def flat_dim(self):
        return self.n

    @cached_property
    def dtype(self):
        return self._dtype

    def __repr__(self):
        return "Discrete({}{})".format(self.n, "; +batch" if self.has_batch_rank else "")

    def __eq__(self, other):
        if not isinstance(other, Discrete):
            return False
        return self.n == other.n

    def sample(self, size=None, seed=None):
        shape = self._get_np_shape(num_samples=size)
        if seed is not None:
            np.random.seed(seed)
        return np.random.randint(self.n, size=shape)

    def contains(self, sample):
        sample = np.asarray(sample)
        return sample.shape == () and sample.dtype.kind == 'i' and 0 <= sample < self.n
