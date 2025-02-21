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
import os

import pytest
import tensorflow as tf

from keras_cv.tests.test_case import TestCase

try:
    from keras_cv.datasets.waymo import load
    from keras_cv.datasets.waymo import transformer
except ImportError:
    # Waymo Open Dataset dependency may be missing, in which case we expect
    # these tests will be skipped based on the TEST_WAYMO_DEPS environment var.
    pass


class WaymoOpenDatasetTransformerTest(TestCase):
    def setUp(self):
        super().setUp()
        self.test_data_path = os.path.abspath(
            os.path.join(os.path.abspath(__file__), os.path.pardir, "test_data")
        )

    @pytest.mark.skipif(
        "TEST_WAYMO_DEPS" not in os.environ
        or os.environ["TEST_WAYMO_DEPS"] != "true",
        reason="Requires Waymo Open Dataset package",
    )
    def test_load_and_transform(self):
        tf_dataset = load(self.test_data_path)

        # Extract records into a list.
        dataset = list(tf_dataset)
        self.assertEqual(len(dataset), 1)
        lidar_tensors = next(iter(dataset))
        num_boxes = lidar_tensors["label_box"].shape[0]
        self.assertEqual(num_boxes, 16)
        self.assertNotEqual(lidar_tensors["frame_id"], 0)
        self.assertNotEqual(lidar_tensors["timestamp_micros"], 0)
        self.assertEqual(lidar_tensors["timestamp_offset"], 0)
        self.assertGreater(lidar_tensors["timestamp_micros"], 0)
        self.assertAllEqual(
            lidar_tensors["label_box_detection_difficulty"],
            tf.zeros(num_boxes, dtype=tf.int32),
        )

        # Laser points.
        point_xyz_mean = tf.reduce_mean(lidar_tensors["point_xyz"], axis=0)
        self.assertAllClose(
            point_xyz_mean, lidar_tensors["pose"][:3, 3], atol=100
        )
        point_feature_mean = tf.reduce_mean(
            lidar_tensors["point_feature"], axis=0
        )
        self.assertAllGreater(point_feature_mean[0], 0)
        self.assertAllGreater(tf.abs(point_feature_mean[1]), 1e-6)
        self.assertAllGreater(point_feature_mean[2:4], 0)
        self.assertTrue(tf.math.reduce_all(lidar_tensors["point_mask"]))

        # Laser labels.
        self.assertEqual(lidar_tensors["label_box_id"].shape[0], num_boxes)
        self.assertEqual(lidar_tensors["label_box_meta"].shape[0], num_boxes)
        self.assertEqual(lidar_tensors["label_box_class"].shape[0], num_boxes)
        self.assertEqual(lidar_tensors["label_box_density"].shape[0], num_boxes)
        self.assertTrue(tf.math.reduce_all(lidar_tensors["label_box_mask"]))
        self.assertAllGreater(
            tf.math.reduce_max(lidar_tensors["label_point_class"]), 0
        )

        # Multi-frame tensors for augmentation.
        augmented_example = next(
            iter(tf_dataset.map(transformer.build_tensors_for_augmentation))
        )
        self.assertEqual(augmented_example["point_clouds"].shape, [183142, 8])
        self.assertEqual(augmented_example["bounding_boxes"].shape, [16, 11])

    @pytest.mark.skipif(
        "TEST_WAYMO_DEPS" not in os.environ
        or os.environ["TEST_WAYMO_DEPS"] != "true",
        reason="Requires Waymo Open Dataset package",
    )
    def test_pad_and_transform_to_vehicle(self):
        dataset = load(self.test_data_path)
        dataset = dataset.map(
            lambda x: (
                transformer.pad_or_trim_tensors(
                    transformer.transform_to_vehicle_frame(x)
                )
            )
        )
        example = next(iter(dataset))

        # Laser points.
        self.assertEqual(example["point_xyz"].shape, [199600, 3])
        self.assertEqual(example["point_feature"].shape, [199600, 4])
        self.assertEqual(example["point_mask"].shape, [199600])
        point_xyz_mean = tf.reduce_mean(example["point_xyz"], axis=0)
        self.assertAllClose(point_xyz_mean, example["pose"][:3, 3], atol=100)
        point_feature_mean = tf.reduce_mean(example["point_feature"], axis=0)
        self.assertAllGreater(point_feature_mean[0], 0)
        self.assertAllGreater(tf.abs(point_feature_mean[1]), 1e-6)
        self.assertAllGreater(point_feature_mean[2:4], 0)
        self.assertTrue(tf.math.reduce_any(example["point_mask"]))

        # Laser labels.
        self.assertEqual(example["label_box_id"].shape[0], 1000)
        self.assertEqual(example["label_box_meta"].shape[0], 1000)
        self.assertEqual(example["label_box_class"].shape[0], 1000)
        self.assertEqual(example["label_box_density"].shape[0], 1000)
        self.assertEqual(example["label_box_mask"].shape, [1000])
        self.assertTrue(tf.math.reduce_any(example["label_box_mask"]))
        self.assertAllGreater(
            tf.math.reduce_max(example["label_point_class"]), 0
        )

    @pytest.mark.skipif(
        "TEST_WAYMO_DEPS" not in os.environ
        or os.environ["TEST_WAYMO_DEPS"] != "true",
        reason="Requires Waymo Open Dataset package",
    )
    def test_convert_to_center_pillar_inputs(self):
        dataset = load(self.test_data_path)
        dataset = dataset.map(
            lambda x: (
                transformer.convert_to_center_pillar_inputs(
                    transformer.pad_or_trim_tensors(
                        transformer.transform_to_vehicle_frame(x)
                    )
                )
            )
        )
        example = next(iter(dataset))

        # Laser points.
        point_clouds = example["point_clouds"]
        self.assertEqual(point_clouds["point_xyz"].shape, [199600, 3])
        self.assertEqual(point_clouds["point_feature"].shape, [199600, 4])
        self.assertEqual(point_clouds["point_mask"].shape, [199600])
        point_feature_mean = tf.reduce_mean(
            point_clouds["point_feature"], axis=0
        )
        self.assertAllGreater(point_feature_mean[0], 0)
        self.assertAllGreater(tf.abs(point_feature_mean[1]), 1e-6)
        self.assertAllGreater(point_feature_mean[2:4], 0)
        self.assertTrue(tf.math.reduce_any(point_clouds["point_mask"]))

        # Laser labels.
        boxes = example["3d_boxes"]
        self.assertEqual(boxes["boxes"].shape[0], 1000)
        self.assertEqual(boxes["classes"].shape[0], 1000)
        self.assertEqual(boxes["difficulty"].shape[0], 1000)
        self.assertEqual(boxes["mask"].shape, [1000])
        self.assertTrue(tf.math.reduce_any(boxes["mask"]))
        self.assertAllGreater(tf.math.reduce_max(boxes["classes"]), 0)
