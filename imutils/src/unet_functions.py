#imports
import cv2
import numpy as np
import tifffile as tiff
import glob
# unet model is here (too)
import skimage.io as io
import skimage.transform as trans
from imutils.scopedatamanager import microscope_data_reader
from skimage import img_as_ubyte
import dask.array as da
import pandas as pd
from natsort import natsorted
import matplotlib.image as mpimg
import os
import matplotlib.pyplot as plt

import time

from sklearn.metrics import accuracy_score
from sklearn.metrics import jaccard_score
from sklearn.metrics import f1_score

from imutils.src.model import unet


def unet_segmentation(img, model):
    """
    Segment an image based on the model loaded.
    Not sure if reshape and resize should be commented.

    :param img: image
    :param model: unet model
    :return: segmented_img
    """
    h, w = img.shape
    # run U-Net network:
    img = cv2.resize(img, (256, 256))
    img = np.reshape(img, img.shape + (1,))
    img = np.reshape(img, (1,) + img.shape)

    img = img / 255
    results = model.predict(img)
    #print(results.shape)
    # reshape results
    results_reshaped = results.reshape((256,256))
    #print(results_reshaped.shape)
    # resize results
    results = cv2.resize(results_reshaped, (w, h)) # cv2 expects w, h in this order
    #TODO: Test if it is okay to multiply the result by *255, like in unet_segment_cntours_with_children, which produces a normal stack (not too heavy)
    return results


def unet_segmentation_stack(input_filepath, output_filepath, weights_path):
    """"
    runs the unet_segmentation function for the stack
    """

    #load model and weights
    model=unet()
    print('loading weights..')
    model.load_weights(weights_path)
    reader_obj = MicroscopeDataReader(input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    tif = da.squeeze(reader_obj.dask_array)

    with tiff.TiffWriter(output_filepath, bigtiff=True) as tif_writer:
        start = time.time()
        for i, img in enumerate(tif):
            #run network
            segmented_img = unet_segmentation(np.array(img), model)
            segmented_img = segmented_img*255
            segmented_img = segmented_img.astype('uint8')
            # write
            tif_writer.write(segmented_img, contiguous=True)
        end = time.time()
        total_time = end - start
        print('total time: ', total_time)


def testGenerator(test_path, target_size = (256,256),flag_multi_class = False, as_gray = True):
    """this function is duplicated from unet-master/data.py"""


    for i in natsorted(os.listdir(test_path)):
        print(i)
        img = io.imread(os.path.join(test_path, i),as_gray = as_gray)
        img = img / 255
        img = trans.resize(img,target_size)
        img = np.reshape(img,img.shape+(1,)) if (not flag_multi_class) else img
        img = np.reshape(img,(1,)+img.shape)
        yield img

def labelVisualize(num_class,color_dict,img):
    """this function is duplicated from unet-master/data.py"""
    img = img[:,:,0] if len(img.shape) == 3 else img
    img_out = np.zeros(img.shape + (3,))
    for i in range(num_class):
        img_out[img == i,:] = color_dict[i]
    return img_out / 255

def saveResult(save_path,npyfile,flag_multi_class = False,num_class = 2):
    """this function is duplicated from unet-master/data.py"""
    for i,item in enumerate(npyfile):
        img = labelVisualize(num_class,COLOR_DICT,item) if flag_multi_class else item[:,:,0]
        io.imsave(os.path.join(save_path,"%d_predict.png"%i),img_as_ubyte(img))


def predict_test_images(test_path, weights_path, save_path):
    """
    Creates the predictions for the images in the test_path based on the weights file
    Probably I could use the unet_segmentation() instead
    Args:
        test_path:
        weights_path:
        save_path:

    Returns:

    """
    model = unet()
    #generate test generator
    testGene = testGenerator(test_path=test_path)

    number_of_predictions = len(glob.glob(os.path.join(test_path, '*.tif*')))

    model.load_weights(weights_path)
    results = model.predict_generator(testGene,number_of_predictions,verbose=1)

    # save_path=os.path.join(project_path, test_folder+'_predictions')
    #print(save_path)
    try: os.mkdir(save_path)
    except: print('folder already exists')

    saveResult(save_path, results)

    # return results

def training_results_figure(training_folder):
    fig, (ax1, ax2, ax3) = plt.subplots(figsize=(20, 5), nrows=1, ncols=3)
    fig.subplots_adjust(wspace=0.5, hspace=0)
    try:
        df = pd.read_csv(os.path.join(training_folder, 'history.csv'))
        df = df.iloc[:, 1:]
        min_val_loss = round(df['val_loss'].min(), 3)
        max_val_accuracy = round(df['val_accuracy'].max(), 3)

        df[['val_loss', 'loss']].plot(ax=ax1)
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Min val loss: ' + str(min_val_loss))
        ax1.set_ylim(0, 1)
        # plt.show()
        df[['val_accuracy', 'accuracy']].plot(ax=ax2)
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy')
        ax2.set_title('Max val accuracy: ' + str(max_val_accuracy))
    except:
        print('no history file for this model: ', training_folder)

    # plt.show()
    try:
        img = mpimg.imread(os.path.join(training_folder, 'test_predictions', '15_predict.png'))
        ax3.imshow(img)
        ax3.set_axis_off()
    except: print("could not read image 15_predict.png in test predictions folder")

    return fig, (ax1, ax2, ax3)


def compare_images_metrics(img_ground_truth_list, img_predicted_test_list, threshold):
    """
    return a dataframe of accuracy metrics (accuracy_score, jaccard_score and f1_score) for the list of images.

    :param ground_truth_images:
    :param test_images:
    :return:
    """
    metrics_list = ['accuracy_score', 'jaccard_score', 'f1_score']

    img_ground_truth_list = natsorted(img_ground_truth_list)
    img_predicted_test_list = natsorted(img_predicted_test_list)

    df = pd.DataFrame()
    for metric in metrics_list:
        print(metric)
        score_list = []
        for i, element in enumerate(img_ground_truth_list):
            print(i, ' element in ground truth image list')
            print(element)
            ground_truth_img = tiff.imread(element)
            test_predicted_img = tiff.imread(img_predicted_test_list[i])
            #threshold = 0.1
            test_predicted_img[test_predicted_img < threshold] = 0
            test_predicted_img[test_predicted_img >= threshold] = 255
            # Convert images to binary (0 and 1)
            ground_truth_img_binary = (ground_truth_img == 255).astype(int)
            test_predicted_img_binary = (test_predicted_img == 255).astype(int)

            tiff.imwrite(img_predicted_test_list[i].replace('.tif', '_binary.tif'), test_predicted_img)

            if metric == 'accuracy_score':
                print('Calculating score with metric:', metric)
                score = accuracy_score(ground_truth_img_binary.flatten(), test_predicted_img_binary.flatten())
            elif metric == 'jaccard_score':
                print('Calculating score with metric:', metric)
                score = jaccard_score(ground_truth_img_binary.flatten(), test_predicted_img_binary.flatten(),
                                      average='binary')
            elif metric == 'f1_score':
                print('Calculating score with metric:', metric)
                score = f1_score(ground_truth_img_binary.flatten(), test_predicted_img_binary.flatten(),
                                 average='binary')

            score_list.append(score)
            print('score list is ', score_list)
        df[metric] = score_list
    return df


def fetch_files_to_compare(ground_truth_path, predicted_test_path):
    """
    TODO: Should this be done in bash? or does it need a function at all?
    :param ground_truth_path:
    :param predicted_test_path:
    :return:
    """
    img_ground_truth_list = natsorted(glob.glob(ground_truth_path + '*.tif*'))
    img_predicted_test_list = natsorted(glob.glob(predicted_test_path + '*.tif*'))

    return img_ground_truth_list, img_predicted_test_list


if __name__ == "__main__":

    training_results_path="/Volumes/scratch/neurobiology/zimmer/ulises/code/unet-master/data/2023_worm_coiled_segmentation/training_results/*"

    training_folders=glob.glob(training_results_path)

    for training_folder in natsorted(training_folders):
        fig, (ax1, ax2, ax3) = training_results_figure(training_folder)
        fig.suptitle(os.path.basename(training_folder))
        plt.show()

    # test_path='/Volumes/scratch/neurobiology/zimmer/ulises/code/unet-master/data/2022_04_24_worm_segmentation_all_worms_good_background/test/'
    # img_name='2022-02-16_12-58-16_worm1-channel-0-behaviour-bigtiff_AVG_background_substracted_img049512.tif'
    #
    # img=tiff.imread(os.path.join(test_path, img_name))
    #
    # for training_folder in natsorted(training_folders):
    #     fig, axes = plt.subplots(figsize=(10, 5), nrows=1, ncols=2)
    #     #fig.subplots_adjust(wspace=0.5, hspace=0)
    #     axes[0].imshow(img)
    #     img_result = mpimg.imread(os.path.join(training_folder, 'test_predictions', '37_predict.png'))
    #     axes[1].imshow(img_result)
    #     for ax in axes:
    #         ax.set_axis_off()
    #     figure_name = os.path.join(training_folder, 'comparison_figure.png')
    #     print(figure_name)
    #     #plt.savefig(figure_name)
    #     plt.show()


    # input_filepath='/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20220127/data/worm6/2022-01-27_22-09-19_worm6-channel-0-behaviour-/2022-01-27_22-09-19_worm6-channel-0-behaviour-bigtiff_AVG_background_substracted.btf'
    # output_filepath='/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/20220127/data/worm6/2022-01-27_22-09-19_worm6-channel-0-behaviour-/2022-01-27_22-09-19_worm6-channel-0-behaviour-bigtiff_AVG_background_substracted_unet_segmented.btf'
    # weights_path='/Volumes/scratch/neurobiology/zimmer/ulises/code/unet-master/data/2022_04_24_worm_segmentation_all_worms_good_background/training_results/2626248_1_w_validation_2batchsize_500steps_100epochs_patience/unet_master.hdf5'
    # unet_segmentation_stack(input_filepath, output_filepath, weights_path)