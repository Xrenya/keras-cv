# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import tensorflow as tf

from keras_cv.layers import preprocessing
from keras_cv.tests.test_case import TestCase


class RandomSharpnessTest(TestCase):
    def test_random_sharpness_preserves_output_shape(self):
        img_shape = (50, 50, 3)
        xs = tf.stack(
            [2 * tf.ones(img_shape), tf.ones(img_shape)],
            axis=0,
        )

        layer = preprocessing.RandomSharpness(0.0, value_range=(0, 255))
        ys = layer(xs)

        self.assertEqual(xs.shape, ys.shape)
        self.assertAllClose(xs, ys)

    def test_random_sharpness_blur_effect_single_channel(self):
        xs = tf.expand_dims(
            tf.constant(
                [
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 1, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ]
            ),
            axis=-1,
        )
        xs = tf.expand_dims(xs, axis=0)

        layer = preprocessing.RandomSharpness((1.0, 1.0), value_range=(0, 255))
        ys = layer(xs)

        self.assertEqual(xs.shape, ys.shape)

        result = tf.expand_dims(
            tf.constant(
                [
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1 / 13, 1 / 13, 1 / 13, 0, 0],
                    [0, 0, 1 / 13, 5 / 13, 1 / 13, 0, 0],
                    [0, 0, 1 / 13, 1 / 13, 1 / 13, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0],
                ]
            ),
            axis=-1,
        )
        result = tf.expand_dims(result, axis=0)

        self.assertAllClose(ys, result)

    def test_random_sharpness_on_batched_images_independently(self):
        image = tf.random.uniform((100, 100, 3), minval=0, maxval=255)
        batched_images = tf.stack((image, image), axis=0)
        layer = preprocessing.RandomSharpness(value_range=(0, 255), factor=0.9)

        results = layer(batched_images)

        self.assertNotAllClose(results[0], results[1])
