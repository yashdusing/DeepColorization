import pickle
import sys
import os

sys.path.append(os.getcwd()[:os.getcwd().index('implementations')])

from implementations.support_scripts.common import h5_vgg_generator_let_there, image_check_with_vgg
# from implementations.support_scripts.metrics import root_mean_squared_error, mean_squared_error

from keras.applications import VGG16
from keras.engine import Model

from keras import backend as K, Input
from keras import optimizers
from keras.layers import Conv2D, UpSampling2D, Lambda, Dense, Merge, merge, concatenate, regularizers, Add, add, \
    Conv2DTranspose, MaxPooling2D

os.environ["CUDA_VISIBLE_DEVICES"] = "1"

b_size = 32

input_shape = (224, 224, 1)

# main network
main_input = Input(shape=input_shape, name='image_part_input')

x = Conv2D(64, (3, 3), padding="same", activation="relu",
           kernel_regularizer=regularizers.l2(0.01))(main_input)
x = MaxPooling2D((2, 2), strides=(2, 2))(x)
x1 = Conv2D(128, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = Conv2D(128, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x1)
x = Conv2D(128, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = add([x, x1])

x = Conv2D(128, (3, 3), padding="same", activation="relu",
           kernel_regularizer=regularizers.l2(0.01))(x)
x = MaxPooling2D((2, 2), strides=(2, 2))(x)
x1 = Conv2D(256, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = Conv2D(256, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x1)
x = Conv2D(256, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = add([x, x1])

x = Conv2D(256, (3, 3), padding="same", activation="relu",
           kernel_regularizer=regularizers.l2(0.01))(x)
x = MaxPooling2D((2, 2), strides=(2, 2))(x)
x1 = Conv2D(512, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = Conv2D(512, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x1)
x = Conv2D(512, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
x = add([x, x1])

x = Conv2D(512, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(x)
main_output = Conv2D(256, (3, 3), padding="same", activation="relu",
                     kernel_regularizer=regularizers.l2(0.01))(x)

# VGG
vgg16 = VGG16(weights="imagenet", include_top=True)
vgg_output = Dense(256, activation='relu', name='predictions')(vgg16.layers[-2].output)

def repeat_output(input):
    shape = K.shape(x)
    return K.reshape(K.repeat(input, 28 * 28), (shape[0], 28, 28, 256))

vgg_output = Lambda(repeat_output)(vgg_output)

# freeze vgg16
for layer in vgg16.layers:
    layer.trainable = False

# concatenated net
merged = concatenate([vgg_output, main_output], axis=3)

last = Conv2D(128, (3, 3), padding="same")(merged)

last = Conv2DTranspose(64, (3, 3), strides=(2, 2), padding="same", activation="relu",
                       kernel_regularizer=regularizers.l2(0.01))(last)
last = Conv2D(64, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(last)
last = Conv2D(64, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(last)

last = Conv2DTranspose(64, (3, 3), strides=(2, 2), padding="same", activation="relu",
                       kernel_regularizer=regularizers.l2(0.01))(last)
last = Conv2D(32, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(last)
last = Conv2D(2, (3, 3), padding="same", activation="relu", kernel_regularizer=regularizers.l2(0.01))(last)


def resize_image(x):
    return K.resize_images(x, 2, 2, "channels_last")


def unormalise(x):
    # outputs in range [0, 1] resized to range [-100, 100]
    return (x * 200) - 100


last = Lambda(resize_image)(last)
last = Lambda(unormalise)(last)


def custom_mse(y_true, y_pred):
    return K.mean(K.square(y_pred - y_true), axis=[1, 2, 3])


model = Model(inputs=[main_input, vgg16.input], output=last)
opt = optimizers.Adam(lr=1E-4, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
model.compile(optimizer=opt, loss=custom_mse)

model.summary()

start_from = 0
save_every_n_epoch = 1
n_epochs = 30
# model.load_weights("../weights/implementation9-wsm-9.h5")

# start image downloader

g = h5_vgg_generator_let_there(b_size, "../data/h5_small_train", None)
gval = h5_vgg_generator_let_there(b_size, "../data/h5_small_validation", None)


for i in range(start_from // save_every_n_epoch, n_epochs // save_every_n_epoch):
    print("START", i * save_every_n_epoch, "/", n_epochs)
    history = model.fit_generator(g, steps_per_epoch=100000//b_size, epochs=save_every_n_epoch,
                                  validation_data=gval, validation_steps=(10000//b_size))
    model.save_weights("../weights/implementation9-full-" + str(i * save_every_n_epoch) + ".h5")

    # save sample images
    image_check_with_vgg(model, 80, "imp9-full-" + str(i * save_every_n_epoch) + "-")

    # save history
    output = open('../history/imp9-full-{:0=4d}.pkl'.format(i * save_every_n_epoch), 'wb')
    pickle.dump(history.history, output)
    output.close()

# image_error_small_vgg(model, "imp09-full-test-100")
