import tensorflow as tf
import numpy as np
import os
from functools import partial

NUM_CLASSES = 100
NUM_TRAIN_IMAGES = 50000
NUM_TEST_IMAGES = 10000

HEIGHT = 32
WIDTH = 32
DEPTH = 3

NEW_HEIGHT = 32
NEW_WIDTH = 32

cifar100_mean = [129.304, 124.070, 112.434]
cifar100_std = [68.170, 65.392, 70.418]


def get_filename(data_dir, train_mode):
    """Returns the filename of binary data based on 'mode'."""
    data_dir = os.path.join(data_dir, 'cifar-100-binary')

    if train_mode:
        return os.path.join(data_dir, 'train.bin')
    else:
        return os.path.join(data_dir, 'test.bin')

def train_preprocess_fn(image, label, augment):
    if augment:
        image = tf.image.resize_image_with_crop_or_pad(image, NEW_HEIGHT+4, NEW_WIDTH+4)
        image = tf.random_crop(image, [NEW_HEIGHT, NEW_WIDTH, 3])
        image = tf.image.random_flip_left_right(image)
    # image = tf.image.per_image_standardization(image)
    # image = (image - cifar100_mean) / cifar100_std
    return image, label

def test_preprocess_fn(image, label, augment):
    if augment:
        image = tf.image.resize_image_with_crop_or_pad(image, NEW_HEIGHT+4, NEW_WIDTH+4)
        image = tf.random_crop(image, [NEW_HEIGHT, NEW_WIDTH, 3])
        image = tf.image.random_flip_left_right(image)
    # image = tf.image.per_image_standardization(image)
    # image = (image - cifar100_mean) / cifar100_std
    return image, label

def read_bin_file(bin_fpath):
    """ Read CIFAR-10 .bin file returns images and labels """
    with open(bin_fpath, 'rb') as fd:
        bstr = fd.read()

    coarse_label_byte = 1
    label_byte = 1
    image_byte = HEIGHT * WIDTH * DEPTH

    array = np.frombuffer(bstr, dtype=np.uint8).reshape((-1, coarse_label_byte + label_byte + image_byte))
    coarse_labels = array[:,:(coarse_label_byte)].flatten().astype(np.int32)
    labels = array[:,coarse_label_byte:(coarse_label_byte+label_byte)].flatten().astype(np.int32)
    images = array[:,(coarse_label_byte+label_byte):].reshape((-1, DEPTH, HEIGHT, WIDTH)).transpose((0, 2, 3, 1))

    return images, labels

def input_fn(data_dir, batch_size, train_mode, augment=None, num_threads=8):
    # Read CIFAR-100 dataset
    images_arr, labels_arr = read_bin_file(get_filename(data_dir, train_mode))
    images_arr = (images_arr - cifar100_mean)/cifar100_std
    images_arr = images_arr.astype(np.float32)
    dataset = tf.data.Dataset.from_tensor_slices((images_arr, labels_arr))

    if augment is None:
        augment = train_mode

    if train_mode:
        buffer_size = int(50000 * 0.4) + 3 * batch_size
        dataset = dataset.apply(tf.contrib.data.shuffle_and_repeat(buffer_size))
        dataset = dataset.apply(tf.contrib.data.map_and_batch(partial(train_preprocess_fn, augment=augment),
                                                              batch_size, num_threads))
    else:
        dataset = dataset.repeat()
        dataset = dataset.apply(tf.contrib.data.map_and_batch(partial(test_preprocess_fn, augment=augment),
                                                              batch_size, num_threads))

    # check TF version >= 1.8
    ver = tf.__version__
    if float(ver[:ver.rfind('.')]) >= 1.8:
        dataset = dataset.apply(tf.contrib.data.prefetch_to_device('/GPU:0'))
    else:
        dataset = dataset.prefetch(10)
    iterator = dataset.make_one_shot_iterator()
    images, labels = iterator.get_next()
    images.set_shape((batch_size, NEW_WIDTH, NEW_HEIGHT, DEPTH))
    labels.set_shape((batch_size, ))

    return images, labels
