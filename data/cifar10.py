import tensorflow as tf
import numpy as np
import os

NUM_CLASSES = 10
INIT_LRN_RATE = 1e-2
MIN_LRN_RATE = 1e-4
WEIGHT_DECAY_RATE = 1e-4
RELU_LEAKINESS = 0.1
NUM_TRAIN_IMAGES = 50000

HEIGHT = 32
WIDTH = 32
DEPTH = 3

NEW_HEIGHT = 32
NEW_WIDTH = 32

cifar10_mean = [125.3, 123.0, 113.9]
cifar10_std = [63.0, 62.1, 66.7]


def get_filenames(data_dir, train_mode):
    """Returns a list of filenames based on 'mode'."""
    data_dir = os.path.join(data_dir, 'cifar-10-batches-bin')

    if train_mode:
        return [
            os.path.join(data_dir, 'data_batch_%d.bin' % i)
            for i in range(1, 6)
        ]
    else:
        return [os.path.join(data_dir, 'test_batch.bin')]

def train_preprocess_fn(image, label):
    image = tf.image.resize_image_with_crop_or_pad(image, NEW_HEIGHT+4, NEW_WIDTH+4)
    image = tf.random_crop(image, [NEW_HEIGHT, NEW_WIDTH, 3])
    image = tf.image.random_flip_left_right(image)
    # image = tf.image.per_image_standardization(image)
    image = (tf.cast(image, tf.float32) - cifar10_mean) / cifar10_std
    return image, label

def test_preprocess_fn(image, label):
    # image = tf.image.resize_image_with_crop_or_pad(image, NEW_HEIGHT+4, NEW_WIDTH+4)
    # image = tf.random_crop(image, [NEW_HEIGHT, NEW_WIDTH, 3])
    # image = tf.image.per_image_standardization(image)
    image = (tf.cast(image, tf.float32) - cifar10_mean) / cifar10_std
    return image, label

def read_bin_file(bin_fpath):
    """ Read CIFAR-10 .bin file returns images and labels """
    with open(bin_fpath, 'rb') as fd:
        bstr = fd.read()

    label_byte = 1
    image_byte = HEIGHT * WIDTH * DEPTH

    array = np.frombuffer(bstr, dtype=np.uint8).reshape((-1, label_byte + image_byte))
    labels = array[:,:label_byte].flatten().astype(np.int32)
    images = array[:,label_byte:].reshape((-1, DEPTH, HEIGHT, WIDTH)).transpose((0, 2, 3, 1))

    return images, labels

def input_fn(data_dir, batch_size, train_mode, num_threads=8):
    # Read CIFAR-10 dataset
    images_list, labels_list = zip(*[read_bin_file(bin_fpath) for bin_fpath in get_filenames(data_dir, train_mode)])
    images = np.concatenate(images_list)
    labels = np.concatenate(labels_list)
    dataset = tf.data.Dataset.from_tensor_slices((images, labels))

    if train_mode:
        buffer_size = int(50000 * 0.4) + 3 * batch_size
        dataset = dataset.apply(tf.contrib.data.shuffle_and_repeat(buffer_size))
        dataset = dataset.apply(tf.contrib.data.map_and_batch(train_preprocess_fn, batch_size, num_threads))
    else:
        dataset = dataset.repeat()
        dataset = dataset.apply(tf.contrib.data.map_and_batch(test_preprocess_fn, batch_size, num_threads))

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
