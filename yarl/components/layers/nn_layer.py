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

"""
TODO: this may still be needed as a superclass for NN-specific stuff.
class NNLayer(LayerComponent):
    ""
    A neural-net layer wrapper class that can incorporate a backend-specific layer object.
    ""
    def __init__(self, *sub_components, **kwargs):
        ""
        Keyword Args:
            class (class): The wrapped tf.layers class to use.
            seed (Optional[int]): The seed to use to make this class non-deterministic.
            **kwargs (any): Kwargs to be passed to the native backend's layers's constructor.
        ""
        assert class_, "ERROR: class_ parameter needs to be given as kwarg in c'tor of NNLayer!"

        super(NNLayer, self).__init__(*sub_components, **kwargs)
        # Generate the wrapped layer object.
        self.layer = class_(**kwargs, ini)

    def _computation_apply(self, *inputs):
        ""
        Only can make_template from this function after(!) we know what the "output"?? socket's shape will be.
        ""
        # TODO: wrap pytorch's torch.nn classes
        if backend() == "tf":
            return self.layer.apply(inputs)


# Create some fixtures for all layer types for simplicity (w/o the need to add any code).
if backend() == "tf":
    import tensorflow as tf

    DenseLayer = partial(NNLayer, class_=tf.layers.Dense)
    Conv1DLayer = partial(NNLayer, class_=tf.layers.Conv1D)
    Conv2DLayer = partial(NNLayer, class_=tf.layers.Conv2D)
    Conv2DTransposeLayer = partial(NNLayer, class_=tf.layers.Conv2DTranspose)
    Conv3DLayer = partial(NNLayer, class_=tf.layers.Conv3D)
    Conv3DTransposeLayer = partial(NNLayer, class_=tf.layers.Conv3DTranspose)
    AveragePooling1DLayer = partial(NNLayer, class_=tf.layers.AveragePooling1D)
    AveragePooling2DLayer = partial(NNLayer, class_=tf.layers.AveragePooling2D)
    AveragePooling3DLayer = partial(NNLayer, class_=tf.layers.AveragePooling3D)
    BatchNormalizationLayer = partial(NNLayer, class_=tf.layers.BatchNormalization)
    DropoutLayer = partial(NNLayer, class_=tf.layers.Dropout)
    FlattenLayer = partial(NNLayer, class_=tf.layers.Flatten)
    MaxPooling1DLayer = partial(NNLayer, class_=tf.layers.MaxPooling1D)
    MaxPooling2DLayer = partial(NNLayer, class_=tf.layers.MaxPooling2D)
    MaxPooling3DLayer = partial(NNLayer, class_=tf.layers.MaxPooling3D)

"""