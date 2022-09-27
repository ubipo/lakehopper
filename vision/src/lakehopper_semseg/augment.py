import tensorflow as tf
import tensorflow.image as tf_img
import tensorflow.random as tf_rand


def augment_image(image, is_color: bool, seed: tf.int64):
    seeds = tf_rand.experimental.stateless_split(seed, num=6)
    rotation = tf_rand.stateless_uniform(
        shape=[], seed=seeds[0], minval=0, maxval=4, dtype=tf.int32
    )
    image = tf_img.rot90(image, k=rotation)
    image = tf_img.stateless_random_flip_left_right(image, seeds[1])
    image = tf_img.stateless_random_flip_up_down(image, seeds[2])
    if is_color:
        image = tf_img.stateless_random_brightness(image, max_delta=0.5, seed=seeds[3])
        image = tf_img.stateless_random_hue(image, max_delta=0.1, seed=seeds[4])
        image = tf_img.stateless_random_contrast(
            image, lower=0.4, upper=1.2, seed=seeds[5]
        )

    return image


class Augment(tf.keras.layers.Layer):
    def __init__(self):
        super().__init__()
        self.rng = tf_rand.Generator.from_seed(42, alg="philox")

    @tf.function
    def call(self, image, labels, weights=None):
        seed = self.rng.make_seeds(2)[0]
        image_aug = augment_image(image, is_color=True, seed=seed)
        labels_aug = augment_image(labels, is_color=False, seed=seed)
        if weights is not None:
            weights_aug = augment_image(weights, is_color=False, seed=seed)
            return image_aug, labels_aug, weights_aug
        return image_aug, labels_aug
