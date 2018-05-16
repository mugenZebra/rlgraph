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

import random
import numpy as np

from yarl.spaces import Discrete


class Bool(Discrete):
    """
    A Bool space is a special case of Discrete where n = 2, the possible values are True or False,
    and the flattened representation is a 1D vector of dim = 1 (not 2!) ([0]=False or [1]=True)
    """
    def __init__(self, add_batch_rank=False):
        super(Bool, self).__init__(n=2, add_batch_rank=add_batch_rank)

    @property
    def shape(self):
        return ()

    @property
    def shape_with_batch_rank(self):
        return self.batch_rank_tuple

    @property
    def flat_dim(self):
        return 1

    @property
    def dtype(self):
        return "bool"

    def __repr__(self):
        return "Bool({})".format("+batch" if self.add_batch_rank else "")

    def sample(self, size=None, seed=None):
        size = self._check_size(size=size, batch_rank_required=self.add_batch_rank)
        if seed is not None:
            random.seed(seed)
        return np.random.choice(a=[False, True], size=size)

    def contains(self, sample):
        return isinstance(sample, bool)
