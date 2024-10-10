import os
import re

import cv2
import numpy as np
import pandas as pd
import tifffile as tiff
from natsort import natsorted

from imutils.scopedatamanager import microscope_data_reader
import dask.array as da
from skimage.morphology import binary_erosion


def tiff2avi(tiff_path, avi_path, fourcc, fps):
    """
    Convert tiff file into avi file with the specified fourcc codec and fps
    The isColor parameter of the writer is harcoded set to False.

    Update: Lukas Reader: Function can now also receive a source folder path with Lukas reader and directly convert
    NDTif to Avi

    Parameters:
    -----------
    tiff_path: str,
        Path to the tiff file
    avi_path: str
        Path to the output file
    fourcc: str, fourcc code
        0 means no coompression, other codecs will have some compression
        To learn more visit: https://www.fourcc.org/
    fps: float (should it be int?)
        Number of frames per second at which the recording was acquired

    To improve:
    ----------
    Write Multifile as option, so it can be set to True

    """

    # corrects fourcc nomenclature
    if fourcc == '0':
        fourcc = 0
    else:
        fourcc = cv2.VideoWriter_fourcc(*fourcc)

    # make fps a float
    fps = float(fps)
    print('Path:', tiff_path)

    tiff_path = os.path.normpath(tiff_path)
    print('Path resolved:', tiff_path)

    tiff_path = os.path.abspath(tiff_path)
    print('Path absolute:', tiff_path)

    if os.path.isdir(tiff_path):
        # Initialize for directory
        reader_obj = MicroscopeDataReader(tiff_path)
    elif os.path.isfile(tiff_path):
        # Initialize for a file (any file, not limited to .btf)
        reader_obj = MicroscopeDataReader(tiff_path, as_raw_tiff=True, raw_tiff_num_slices=1)
    else:
        raise ValueError("Invalid input file path. Please provide a valid directory or file.")

    tif = da.squeeze(reader_obj.dask_array)
    frame_size_unknown_len = tif[0].shape

    print(frame_size_unknown_len)
    # if image has channels get height and width (ignore 3rd output)

    print(f"Opening video writer with frame size {frame_size_unknown_len}")
    if len(frame_size_unknown_len) == 3:
        # Time should be first
        _, frame_height, frame_width = frame_size_unknown_len
    elif len(frame_size_unknown_len) == 2:
        frame_height, frame_width = frame_size_unknown_len
    else:
        raise ValueError(f"Invalid frame size, expected 2 or 3 dimensions, got {frame_size_unknown_len}")

    video_out = cv2.VideoWriter(avi_path, apiPreference=0, fourcc=fourcc, fps=fps,
                                frameSize=(frame_width, frame_height), isColor=False)

    for i, img in enumerate(tif):
        # img=cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
        video_out.write(cv2.convertScaleAbs(np.array(img)))  # if img is uint16 it can't save it
        # if i>20: break
    video_out.release()
    print(f'Finished! Video saved at: {avi_path}')


def ometiff2bigtiff(path, output_filename=None):
    """
    List all ome.tiff in a directory and make them one bigtiff
    Somehow it gives an error for the last ome tiff, but resulting .btf is fine.

    IMPORTANT: This ometiff2big tiff removes the Z-Stack information in a recording with Z stacks!
    At least if the number of Z Stacks is inconsistent, which is the case for the current writer in ome.tiff. While recording, the microscope saves the ome.tiff file even before the z-stack is finished.

    Parameters:
    -----------
    path: str,
        Path to the directory containing the several ome tiff files.
    output_filename: str,
    if not defined it will be generated based on the path name.
    """
    print(path)
    # find number of files in path that end with "ome.tif"
    num_files = len([name for name in os.listdir(path) if name.endswith("ome.tif")])
    if num_files == 0:
        print("Aborted because no ome.tiff files found in path, therefore no bigtiff was created.")
        return
    if output_filename is None:
        if path.endswith('/'):
            output_filename = path + re.split('/', path)[-2] + 'bigtiff.btf'
        else:
            output_filename = path + '/' + re.split('/', path)[-1] + 'bigtiff.btf'

    with tiff.TiffWriter(output_filename, bigtiff=True) as output_tif:
        # print(f'list of files is {os.listdir(path)}')
        for file in natsorted(os.listdir(path)):
            # print(os.path.join(path, file))
            if file.endswith('ome.tif'):
                # print(os.path.join(path, file))
                with tiff.TiffFile(os.path.join(path, file)) as tif:
                    print('length of pages is: ', len(tif.pages))
                    # print('length of series is: ', len(tif.series))
                    for idx, page in enumerate(tif.pages):
                        # print(idx)
                        img = page.asarray()
                        output_tif.write(img, photometric='minisblack',
                                         contiguous=True)  # , description=omexmlMetadataString)
# path='/Users/ulises.rey/local_data/2022-02-23_11-28_immobilised_1_Ch0'
# ometiff2bigtiff(path)

def ometiff2bigtiffZ(path, output_dir=None, actually_write=True, num_slices=None):
    """
    This function was copied from video_conversions/Python/bigtiff/
    """
    if output_dir is None:
        output_dir = path
    if path.endswith('/'):
        output_filename = output_dir + re.split('/', path)[-2] + 'bigtiff.btf'
    else:
        output_filename = output_dir + '/' + re.split('/', path)[-1] + 'bigtiff.btf'

    print(f"File will be written that is divisible by {num_slices}")
    print(f"And written to filename {output_filename}")
    total_num_frames = 0
    buffer = []

    reader_obj = MicroscopeDataReader(path, as_raw_tiff=True, raw_tiff_num_slices=1)
    tif = da.squeeze(reader_obj.dask_array)
    with tiff.TiffWriter(output_filename, bigtiff=True) as output_tif:
        '''
        for i_file, file in enumerate(natsorted(os.listdir(path))):
            if not file.endswith('ome.tif') or 'bg' in file:
                continue
            this_ome_tiff = os.path.join(path, file)
            print("Currently reading: ")
            print(this_ome_tiff)
            with tiff.TiffFile(this_ome_tiff) as tif:
        '''
        for i, page in enumerate(tif):
            #print(f'Page {i}/{len(tif.pages)} in file {i_file}')
            # Bottleneck line
            #img = page.asarray()
            img = np.array(page)
            # Convert to proper format, and write single frame
            # img = (alpha*img).astype('uint8')
            total_num_frames += 1
            if num_slices is None:
                if actually_write:
                    output_tif.write(img, photometric='minisblack')
            else:
                buffer.append(img)
                if len(buffer) >= num_slices:
                    print(f"Writing {num_slices} frames from buffer...")
                    for img in buffer:
                        if actually_write:
                            output_tif.write(img, photometric='minisblack', contiguous=True)
                    buffer = []
            if len(buffer) > 0:
                print(f"{len(buffer)} frames not written")

                # if num_frames is not None and i > num_frames: break


def max_projection_3d(input_filepath, output_filepath, fold_increase=3, nplanes=24, flip=False):
    """
    Create a visualization image of a volume, with the 3 max projections possible.
    To improve: Make another function that does the same but in a figure. Then the fold increase would not have to be int.
    Parameters:
    ------------
    input_filepath: str,

    output_filepath: str,

    fold_increase: int, (it can't be float, so the ratio dimensions xyz are not exactly real)
        Expands the z dimension so that the image has crrect dimensions. Depends on the ratio between xy pixel size and z-step size.
    nplanes: int,

    """
    with tiff.TiffWriter(output_filepath, bigtiff=True) as output_tif:
        with tiff.TiffFile(input_filepath) as tif:
            for idx, page in enumerate(tif.pages):
                img = page.asarray()
                # if it is the first plane of the volume create an empty img_stack shape=(w, h, z)
                if idx % nplanes == 0:
                    # print('index is ',idx)
                    img_stack = np.full(shape=(img.shape[0], img.shape[1], nplanes), fill_value=np.nan, dtype=np.uint16)

                # fill the idx plane with the img
                img_stack[:, :, idx % nplanes] = img

                # if it is the last plane on the volume do max projection on the three axis and concatenate them
                if idx % nplanes == nplanes - 1:
                    max0 = np.max(img_stack, axis=0)
                    max1 = np.max(img_stack, axis=1)
                    max2 = np.max(img_stack, axis=2)

                    # extends the YZ and XZ max projection for better visualization based on input fold_increase variable
                    max0 = np.repeat(max0, fold_increase, axis=1)
                    # rotates max0
                    max0 = np.transpose(max0)
                    max1 = np.repeat(max1, fold_increase, axis=1)

                    # defines corner array dimensions and fill value of the corner matrix
                    fill_value = 100
                    corner_matrix = np.full((fold_increase * img_stack.shape[2], fold_increase * img_stack.shape[2]),
                                            fill_value, dtype='uint16')

                    # flip if needed (for Green Channel, since the image is mirrored compared to red channel)
                    if flip is True:
                        max2 = cv2.flip(max2, 1)
                        max0 = cv2.flip(max0, 1)
                    # concatenate the different max projections into one image

                    vert_conc_1 = cv2.hconcat([max2, max1])
                    vert_conc2 = cv2.hconcat([max0, corner_matrix])
                    final_img = cv2.vconcat([vert_conc_1, vert_conc2])

                    # save the 3 max projection image
                    output_tif.write(final_img, photometric='minisblack', contiguous=True)


def stack_subtract_background(input_filepath, output_filepath, background_img_filepath, invert=True):
    """
    Subtract the background image from a btf stack
    its parser in imutils_parser.py might not work due to being it boolean
    Parameters:
    ----------
    input_filepath, str
    input path to the tiff file
    output_filepath, str
    path to where the file will be written
    background_img_filepath, str
    path to the background image
    inverse, bool
    It is default True because the function before did not have this parameter and was doing the inverse by default
    Returns:
    ----------
    """
    print("Do not use this function with a parser unless you are sure it works (See docstring)")

    # load background image
    reader_obj_background = MicroscopeDataReader(background_img_filepath, as_raw_tiff=True, raw_tiff_is_2d=True)
    bg_img = np.array(da.squeeze(reader_obj_background.dask_array))
    try:
        # Try to read the input file as a .btf
        reader_obj_video = MicroscopeDataReader(input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    except TypeError:
        # Try to read as an ndtiff (input_filepath should be a folder)
        reader_obj_video = MicroscopeDataReader(input_filepath, as_raw_tiff=False)

    tif = da.squeeze(reader_obj_video.dask_array)

    if invert:
        bg_img = cv2.bitwise_not(bg_img) # .astype(dtype=np.uint8)
        print("inverting background image")
    else:
        print("using background as it is")

    with tiff.TiffWriter(output_filepath, bigtiff=True) as tif_writer:
        for i, img in enumerate(tif):
            img = np.array(img)
            if invert:
                img = cv2.bitwise_not(img)
            new_img = cv2.subtract(img, bg_img)
            tif_writer.write(new_img, photometric='minisblack',  contiguous=True)


def stack_make_binary(stack_input_filepath: str, stack_output_filepath: str, threshold: float,
                      max_value: float):
    """
    write a binary stack based on lower and higher threshold
    Parameters:
    -------------
    stack_input_filepath, str
    stack_output_filepath, str
    lower_threshold, float
    max_val, float
    Returns:
    -------------
    None
    """
    reader_obj = MicroscopeDataReader(stack_input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    tif = da.squeeze(reader_obj.dask_array)
    with tiff.TiffWriter(stack_output_filepath, bigtiff=True) as tif_writer:
        for i, img in enumerate(tif):
            img = np.array(img)
            # apply threshold
            ret, new_img = cv2.threshold(img, threshold, max_value, cv2.THRESH_BINARY)
            #convert matrix to np.uint
            #new_img = new_img * 255
            new_img = new_img.astype(np.uint8)
            tif_writer.write(new_img, contiguous=True)

def stack_normalise(stack_input_filepath: str, stack_output_filepath: str, alpha: float,
                      beta: float):
    """
    Normalise the stack
    Parameters:
    -------------
    stack_input_filepath, str
    stack_output_filepath, str
    alpha, float
    beta, float
    Returns:
    -------------
    None
    """
    reader_obj = MicroscopeDataReader(stack_input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    tif = da.squeeze(reader_obj.dask_array)
    with tiff.TiffWriter(stack_output_filepath, bigtiff=True) as tif_writer:
        for i, img in enumerate(tif):
            normalised_img = cv2.normalize(np.array(img), None, alpha=alpha, beta=beta, norm_type=cv2.NORM_MINMAX)
            tif_writer.write(normalised_img, contiguous=True)


def stack_subsample(stack_input_filepath, stack_output_filepath, range):
    """Subsample the stack based on the given range

    """
    with tiff.TiffWriter(stack_output_filepath, bigtiff=True) as tif_writer:
        with tiff.TiffFile(stack_input_filepath) as tif:
            for i, page in enumerate(tif.pages[range]):
                # loads the first frame
                img = page.asarray()
                tif_writer.write(img, contiguous=True)


def make_contour_based_binary(stack_input_filepath, stack_output_filepath, median_blur, threshold,
                              max_value, contour_size, tolerance, inner_contour_area_to_fill, gaussian_blur=0, substract_background=1):

    """
    Produce a binary image based on contour and inner contour sizes, by calling draw_some_contours()
    better than the make_binary before which was on centerline package
    TODO: Split into several functions. stack_binary already exists. From that oen could have the fill inner contours
    Parameters:
    -----------
    :param stack_input_filepath:
    :param stack_output_filepath:
    :param median_blur: (needs an odd number)
    :param threshold:
    :param max_value:
    :param contour_size:
    :param tolerance: contour sizes will be considered between contour_size*-tolerance and cotnour_size*tolerance
    :param inner_contour_area_to_fill: all inner contours below this value will be filled (will be part of the worm)
    :return:
    Returns:
    --------
    """
    with tiff.TiffWriter(stack_output_filepath, bigtiff=True) as tif_writer:
        with tiff.TiffFile(stack_input_filepath) as tif:
            for i, page in enumerate(tif.pages):
                # loads the first frame
                img = page.asarray()

                if substract_background != 1:
                    img = 255 - img

                # median Blur
                if gaussian_blur != 0:
                    img = cv2.GaussianBlur(img, (gaussian_blur, gaussian_blur), 0)

                if median_blur != 0:
                    img = cv2.medianBlur(img, median_blur)

                # apply threshold
                ret, new_img = cv2.threshold(img, threshold, max_value, cv2.THRESH_BINARY)
                # draw_some_contours does not need imfunctions.draw_some_contours in here. But outside this file.
                worm_contour_img = draw_some_contours(new_img, contour_size=contour_size, tolerance=tolerance,
                                                      inner_contour_area_to_fill=inner_contour_area_to_fill)

                tif_writer.write(worm_contour_img, contiguous=True)


def unet_segmentation_contours_with_children(binary_input_filepath, raw_input_filepath, output_filepath, weights_path):
    """
    Run through the unet segmentation the contours with children.
    TO DO: It would be more efficient to do a list of frames.
    Parameters:
    -----------
    input_filepath, str
    output_filepath, str
    weights_path, str
    Returns:
    -----------

    """

    from imutils.src.model import unet
    model = unet()
    model.load_weights(weights_path)

    reader_obj_binary = MicroscopeDataReader(binary_input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    reader_obj_raw = MicroscopeDataReader(raw_input_filepath, as_raw_tiff=True, raw_tiff_num_slices=1)
    binary_tif = da.squeeze(reader_obj_binary.dask_array)
    raw_tif = da.squeeze(reader_obj_raw.dask_array)

    with tiff.TiffWriter(output_filepath, bigtiff=True) as tif_writer:

        for i, img in enumerate(binary_tif):

            img = np.array(img)
            # find contours
            cnts, hierarchy = cv2_find_contours_compatibility_mode(img)

            # if there is None or less than 2 contours: write the binary and continue
            if cnts is None or len(cnts) < 2:
                tif_writer.write(img, contiguous=True)
                continue

            # find contours with children
            contours_with_children = extract_contours_with_children(img)

            # If there are no contours_with_children (empty list), write binary too
            if contours_with_children == []:
                tif_writer.write(img, contiguous=True)
                continue

            # make a copy of the original image here in order to paste more than one contour with children
            #TODO: Is this copy needed?
            # new_img = raw_tif.pages[i].asarray()
            new_img = raw_tif[i].compute().copy()
            for cnt_idx, cnt in enumerate(contours_with_children):
                x, y, w, h = cv2.boundingRect(cnt)
                # make the crop
                cnt_img = new_img[y:y + h, x:x + w]

                #TODO: can the unet_functions.unet_segmentation() be used here instead of all this, to produce results_reshaped?
                #TODO: Be careful, because that function does NOT normalize to 255!
                # run U-Net network:
                cnt_img = cv2.resize(cnt_img, (256, 256))
                cnt_img = np.reshape(cnt_img, cnt_img.shape + (1,))
                cnt_img = np.reshape(cnt_img, (1,) + cnt_img.shape)

                # normalize to 1 by dividing by 255
                cnt_img = cnt_img / 255
                results = model.predict(cnt_img)
                # reshape results
                results_reshaped = results.reshape(256, 256)
                # resize results
                results_reshaped = cv2.resize(results_reshaped, (w, h))
                # multiply it by 255
                results_reshaped = results_reshaped * 255

                # paste it into the binary image
                img[y:y + h, x:x + w] = results_reshaped

            tif_writer.write(img, contiguous=True)


def erode(binary_input_filepath, output_filepath):
    """
    erode all the frames of a stack file
    Paramereters:
    -------------
    input_filepath, str
    Binary file
    output_filepath, str
    """
    with tiff.TiffFile(binary_input_filepath) as tif, tiff.TiffWriter(output_filepath,
                                                                                       bigtiff=True) as tif_writer:
        for i, page in enumerate(tif.pages):
            img = page.asarray()
            eroded_img = binary_erosion(img)
            # convery to image with values form 0 to 255
            eroded_img = eroded_img.astype(np.uint8)  # convert to an unsigned byte
            eroded_img *= 255
            tif_writer.write(eroded_img, contiguous=True)


def make_hyperstack_from_ometif(input_path, output_filepath, shape, dtype, imagej=True, metadata={'axes': 'TZYX'}):
    """
    Creates a hyperstack from ome.tiff files path
    Parameters:
    --------------
    input_path,
    output_filepath,
    shape, tuple
    Dimensions of the stack. Prefered format TZYX. Example: (100,30,600,600)
    dtype, str
    data type. Example: 'uint16'
    imagej=True,
    metadata, dict
    Any metadata that has to be in the hyperstack
    """

    # create the hyperstack
    hyperstack = tiff.memmap(
        output_filepath,
        shape=shape,
        dtype=dtype,
        imagej=True,
        metadata={'axes': 'TZYX'},
    )

    # loop through it to fill it:
    c = 0
    z_index = 0
    t_index = 0
    for file in natsorted(os.listdir(input_path)):
        if file.endswith('ome.tif'):
            # print(os.path.join(path,file))
            with tiff.TiffFile(os.path.join(input_path, file)) as tif:
                for idx, page in enumerate(tif.pages):
                    img = page.asarray()
                    hyperstack[t_index, z_index] = img
                    hyperstack.flush()
                    c = c + 1
                    z_index = z_index + 1
                    # if z index is equal to the planes per volume (shape[1]), reset z and start new t_index
                    if z_index == shape[1]:
                        z_index = 0
                        t_index = t_index + 1


####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:
####### THE FUNCTION BELOW CAN'T BE CALLED FROM THE IMUTILS PARSER YET:


def extract_frames(input_image, output_folder, frames_list):
    """
    Extract the frames from an stack (image) and save them as single images given a list.
    #TODO name of the output file has the basename of the original image

    Parameters:
    -----------
    input_image: str,
        Path to the input_image (stack)
    output_folder: str
        Path to the folder where the images will be saved (It will be created if it does not exist)
    frames_list: list, numpy array or int
        list of integers, frames that will be extracted
    """
    # create output_folder if it does not exist
    if not os.path.exists(output_folder):
        print('making ', output_folder, ' directory')
        os.makedirs(output_folder)
    else:
        print(output_folder, 'already exists')

    with tiff.TiffFile(input_image) as tif:
        # iterate over the frames in the list
        # for i, page in enumerate(tif.pages[frames_list]):
        for frame in frames_list:
            img = tif.pages[frame].asarray()
            # print(os.path.join(output_folder,'img'+str(i)+'.'+str(file_format)))
            tiff.imwrite(os.path.join(output_folder, 'img' + str(frame) + '.tif'), img)


def add_zeros_to_filename(path, len_max_number=6):
    """
    Change the filename of images inside the path from img235.png to img00235.png depending on len_max_number
    It has a sister function: add_zeros_to_csv
    # TODO: make it less specific, so it does not required the 'img' string
    Parameters:
    -----------
    path: str,
        Path to the directory with the images
    len_max_number: int
        number of digits the number should have, default is 6
    """
    # creates numberic regular expression
    regex_num = re.compile(r'\d+')

    files = os.listdir(path)
    # this could be improved with a regular expression to catch the numbers.
    for filename in files:
        if 'img' not in filename: continue
        # print(filename)
        new_filename = filename

        number = regex_num.search(filename).group(0)

        # get the file exntesion without the do (e.g. 'png')
        file_extension = re.split('\.', filename)[-1]

        # while the number is smaller than the len_max_number
        while len(number) < len_max_number:
            # print(re.split('img', filename)[1])
            number = '0' + number
        # new filename= img string+number+ dot + extension
        new_filename = 'img' + number + '.' + file_extension
        os.rename(os.path.join(path, filename), os.path.join(path, new_filename))


def images2stack_RAM(path, output_filename):
    """
    Convert the images in one folder into a stack, keeping their filenames in the metadata.
    It is not an object to it needs to allocate all the memory for the stack
    Parameters:
    -------------
    path: str, path to the input_folder
    output_filename: str, name of the output stack
    """
    # Function in construction
    # files = os.listdir(path)#tifffile.natural_sorted(output_path)
    # image = tifffile.imread(os.path.join(path,files))


def images2stack(path, output_filename):
    """
    Convert the images in one folder into a stack, keeping their filenames
    Images have to be .tif, can't be PNG.
    Parameters:
    -------------
    path: str, path to the input_folder
    output_filename: str, name of the output stack
    """
    files = natsorted(os.listdir(path))
    metadata = {'Info': '\n'.join(files)}

    with tiff.TiffWriter(output_filename, imagej=True) as tif:
        for filename in files:
            # if the images are tiff
            print(filename)
            #skip files that start with '.'
            if filename.startswith('.'): continue

            if filename.endswith(('.tif', '.tiff')):
                image = tiff.imread(os.path.join(path, filename))
            # if the images are png
            if filename.endswith('.png'):
                image = cv2.imread(os.path.join(path, filename))

            tif.write(image, contiguous=True, photometric='minisblack', metadata=metadata)


def rgbimages2stacks(list_of_images, output_path):
    """
    Converts a list of PNG images into three stacks, one for each channel. It assumes the default is BGR.
    Parameters:
    -------------
    list_of_images: list, list of png images
    output_path: str, name of the directory where the stack will be written
    """
    r_output = os.path.join(output_path, 'Stack_red.tiff')
    g_output = os.path.join(output_path, 'Stack_green.tiff')
    b_output = os.path.join(output_path, 'Stack_blue.tiff')

    with tiff.TiffWriter(r_output, imagej=True) as tif_r, tiff.TiffWriter(g_output,
                                                                          imagej=True) as tif_g, tiff.TiffWriter(
        b_output, imagej=True) as tif_b:
        for image_path in list_of_images:
            image = cv2.imread(image_path)
            # somehow the default from PreSens is BGR so we need to convert it
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            r_image = rgb_image[:, :, 0]
            g_image = rgb_image[:, :, 1]
            b_image = rgb_image[:, :, 2]

            tif_r.write(r_image, contiguous=True, photometric='minisblack')
            tif_g.write(g_image, contiguous=True, photometric='minisblack')
            tif_b.write(b_image, contiguous=True, photometric='minisblack')


def stack2images(input_filename, output_path):
    """
    Convert a stack into a folder with all the images, saving each image with its original name
    Parameters:
    -------------
    input_filename:str, name of the input stack
    output_path: str, path to the directory where it will be saved

    If it does not work check here: https://forum.image.sc/t/keep-image-description-metadata-in-a-stack-after-modifying-it/50625/4
    """
    try:
        os.mkdir(output_path)  # creates the subdirectory where it should be stored
    except:
        print('Output Directory already exists, might overwrite')
    with tiff.TiffFile(input_filename) as tif:
        # try to get metadata from imageJ
        try:
            files = tif.imagej_metadata['Info'].split('\n')
            metadata = True
        except:
            metadata = False
        metadata = False
        for idx, page in enumerate(tif.pages):
            img = page.asarray()
            # if metadata is True: name according to metadata, else name image1.tif,etc.
            if metadata == True:
                filename = files[idx]
            else:
                filename = 'image' + str(idx) + '.tif'
            tiff.imwrite(os.path.join(output_path, filename), img)


def tiff2png_list(tiff_img_list):
    """
    Convert images in the list from tiff to png. There is compression happening.
    :param tiff_img_list:
    :return:
    """
    for img_path in tiff_img_list:
        img = tiff.imread(img_path)
        new_filename = os.path.splitext(img_path)[0]+".png"
        io.imsave(new_filename, img)
    return None

def contours_length(img):
    """
    Return length and perimeter of the contours in an image.
    Length is assumed to be half of the perimeter. Only valid for elongated contours.

    Parameters
    -------------
    img: numpy_array,
    name of the input stack

    Returns
    ------------
    contours_len: numpy array,
    contains the length of the contours
    contours_peri: numpy array,
    contains the perimeter of the contours

    """
    cnts, hierarchy = cv2_find_contours_compatibility_mode(img)
    contours_peri = []

    for cnt in cnts:
        contours_peri.append(cv2.arcLength(cnt, True))

    contours_peri = np.array(contours_peri)
    contours_len = contours_peri / 2

    return contours_len, contours_peri


def z_projection(img, projection_type, axis=0):
    """
    Careful: mean projection might change dtype to float32
    Parameters:
    ------------
    img, 3-D numpy array
    Image stack that needs to be projected across the z dimension

    projection type, str
    String containing one of the 4 projections options: max, min, mean or median.

    axis : None or int or tuple of ints, optional
        Axis or axes along which to operate.  By default, flattened input is
        used.
    Returns:
    ------------
    projected_img, numpy array
    Contains the projected img
    """
    if projection_type == 'max':
        projected_img = np.max(img, axis=axis)
    if projection_type == 'min':
        projected_img = np.min(img, axis=axis)
    if projection_type == 'mean':
        projected_img = np.mean(img, axis=axis)
    if projection_type == 'median':
        projected_img = np.median(img, axis=axis)

    return projected_img


def stack_z_projection(input_path, output_path, projection_type, dtype='uint16', axis=0):
    """

    Parameters:
    :param input_path:
    :param output_path:
    :param projection_type:
    :param dtype:
    :param axis:
    :return:
    """
    try:
        reader_obj = MicroscopeDataReader(input_path, as_raw_tiff=True, raw_tiff_num_slices=1)
    except TypeError:
        reader_obj = MicroscopeDataReader(input_path, as_raw_tiff=False)
    stack = da.squeeze(reader_obj.dask_array)
    projected_img = z_projection(stack, projection_type, axis)
    projected_img = projected_img.astype(dtype)
    tiff.imwrite(output_path, projected_img)
    return None


def z_projection_parser(hyperstack_filepath, output_filepath, projection_type, axis):
    """
    parser do run the z_projection function

    Warning: Write permission is required for this function

    Parameters:
    ----------
    img_path, str
    output_path, str
    projection_type, str
    axis : None or int or tuple of ints, optional
    Axis or axes along which to operate.  By default, flattened input is
    used.
    Returns:
    ----------
    Writes the projection. Function itself returns None
    """
    # load hyperstack in memory map
    hyperstack = tiff.memmap(hyperstack_filepath, dtype='uint16')
    # crate writer object
    with tiff.TiffWriter(output_filepath, bigtiff=True) as tif_writer:
        # iterate for each volume of the hyperstack
        for volume in hyperstack:
            projected_img = z_projection(volume, projection_type, axis)
            tif_writer.write(projected_img, contiguous=True)


def draw_some_contours(img, contour_size, tolerance, inner_contour_area_to_fill):
    """
    Return img with drawn contours based on size, filling contours below inner_contour_area_to_fill
    Parameters:
    -----------
    img, numpy array
    image from where the contours will be taken
    contour_size, float
        expected area of the contour to be extracted
    tolerance, float
        tolerance around which other contours will be accepted. e.g. contour_size 100 and tolerance 0.1 will include contours from 90 to 110.
    inner_contour_area_to_fill, float
        area of inner contours that will be filled

    Returns:
    -----------
    img_contours, numpy array
        image with drawn contours
    """

    # convert image dtype if not uint8
    # image has to be transformed to uint8 for the findContours
    img = img.astype(np.uint8)
    # get contours
    cnts, hierarchy = cv2_find_contours_compatibility_mode(img)

    # good contours index
    cnts_idx = []  # np.array([])
    # create empty image
    img_contours = np.zeros(img.shape)

    for cnt_idx, cnt in enumerate(cnts):
        cnt_area = cv2.contourArea(cnt)
        # if the contour area is between the expected values with tolerance, save contour in cnts_idx and draw it
        if (contour_size * (1 - tolerance) < cnt_area < contour_size * (1 + tolerance)):
            cnts_idx.append(np.array(cnt_idx))
            cv2.drawContours(img_contours, cnts, cnt_idx, color=255, thickness=-1, hierarchy=hierarchy, maxLevel=1)

        # if the current cnt_idx has as a parent a contour in good countours (cnts_idx)
        if hierarchy[0][cnt_idx][3] in cnts_idx:
            # (and) if it is smaller than inner contour, draw it
            if cnt_area < inner_contour_area_to_fill:
                # print(cv2.contourArea(contours[j]))
                cv2.drawContours(img_contours, cnts, cnt_idx, color=255, thickness=-1)

    # convert the resulting image into a 8 binary numpy array
    img_contours = np.array(img_contours, dtype=np.uint8)

    return img_contours


def extract_contours_with_children(img):
    """
    Find the contours that have a children in the given image and return them as list

    Parameters:
    -----------
    img, np.array
    Returns:
    -----------
    contours that have a children, list of contours with children
    Important does not return the children, only the contour that has children.
    """

    #important, findCountour() has different outputs depending on CV version! _, cnts, hierarchy or cnts, hierarchy
    cnts, hierarchy = cv2_find_contours_compatibility_mode(img)
    contours_with_children = []
    for cnt_idx, cnt in enumerate(cnts):
        # draw contours with children: last column in the array is -1 if an external contour, column 2 is different than -1 meaning it has children
        if hierarchy[0][cnt_idx][3] == -1 and hierarchy[0][cnt_idx][2] != -1:
            contours_with_children.append(cnt)
            # not needed, do it outside this function
            # get coords of boundingRect
            # x,y,w,h = cv2.boundingRect(cnt)
            # make the crop
            # cnt_img=img[y:y+h,x:x+w]
    return contours_with_children


def cv2_find_contours_compatibility_mode(img):
    output = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if len(output) == 3:
        # Older versions of cv2 return 3 values
        _, cnts, hierarchy = output
    elif len(output) == 2:
        cnts, hierarchy = output
    else:
        raise ValueError("The output of cv2.findContours is not the expected length "
                         f"(2 or 3), but instead: {len(output)}; Full output: {output}")
    return cnts, hierarchy


def crop_image_from_contour(img, contour):
    """crop the image based on a contour
    Parameters:
    -----------
    img, img
    contour, contour object
    returns:
    cnt_img
    """
    x, y, w, h = cv2.boundingRect(contour)
    # make the crop
    cnt_img = img[y:y + h, x:x + w]

    return cnt_img


def stack_extract_and_save_contours_with_children(binary_input_filepath, raw_input_filepath, output_folder, crop=False,
                                                  subsample=250):
    """

    :param binary_input_filepath: image from where the contours will be extracted
    :param raw_input_filepath: image that will be cropped based on the binary contours (can be the same as binary_input_filepath)
    :param output_folder: folder where to save the images
    :param subsample: subsample rate to not to save all the images.
    :return: None
    """

    file_basename = os.path.splitext(os.path.basename(raw_input_filepath))[0]
    print(file_basename)

    with tiff.TiffFile(binary_input_filepath) as tif_binary, tiff.TiffFile(raw_input_filepath) as tif_raw:
        for i, page in enumerate(tif_binary.pages):
            if i % subsample != 0: continue
            img = page.asarray()

            # extract contours with children
            contours_with_children = extract_contours_with_children(img)

            for cnt_idx, cnt in enumerate(contours_with_children):
                # get the raw image
                raw_img = tif_raw.pages[i].asarray()
                # if crop == True make the crop on the raw image
                if crop==True:
                    raw_img = crop_image_from_contour(raw_img, cnt)
                # add zeros to str(i) so that it can be more easily read by natsort algorithms
                while (len(str(i)))<6:
                    i= "0"+str(i)
                output_filepath = os.path.join(output_folder,
                                               file_basename + '_frame_' + i + '_cnt_' + str(cnt_idx) + '.tiff')
                print(output_filepath)
                tiff.imwrite(output_filepath, raw_img)
    return None


def find_specific_contours_with_specific_children(img, external_contour_area, internal_contour_area):
    """
    Inspired by imutils.src.imfunctions.extract_contours_with_children()
    :return:
    """

    # important, findCountour() has different outputs depending on CV version! _, cnts, hierarchy or cnts, hierarchy
    cnts, hierarchy = cv2_find_contours_compatibility_mode(img)
    specific_contours_with_specific_children = []

    for cnt_idx, cnt in enumerate(cnts):
        # draw contours with children: last column in the array is -1 if an external contour, column 2 is different than -1 meaning it has children
        if hierarchy[0][cnt_idx][3] == -1 and hierarchy[0][cnt_idx][2] != -1:
            area = cv2.contourArea(cnt)

            # check if the contours with children have an area between the external_cnt_area
            if external_contour_area[0] < area < external_contour_area[1]:
                # find the rows of an array where the 3rd column is equal to cnt_idx
                new_array = np.where(hierarchy[0][:, 3] == cnt_idx)
                for child_cnt_idx in new_array:
                    child_cnt_area = cv2.contourArea(cnts[child_cnt_idx[0]])

                    if internal_contour_area[0] < child_cnt_area < internal_contour_area[1]:
                        specific_contours_with_specific_children.append(cnt)

    return specific_contours_with_specific_children

def stack_self_touch(binary_path, external_contour_area, internal_contour_area):
    """
    This function was written to detect self touch in worm, which will form a contour with children.
    :param binary_path: path to the binary stack image
    :param external_contour_area: area range of the external contour (min and max), e.g. [7000, 20000]
    :param internal_contour_area: area range the internal contour (min and max), e.g. [100, 2000]
    """
    df = pd.DataFrame()

    with tiff.TiffFile(binary_path) as tif_binary:
        for i, page in enumerate(tif_binary.pages):
            img = page.asarray()
            contours_with_children = find_specific_contours_with_specific_children(img, external_contour_area, internal_contour_area)
            if contours_with_children:
                #print('self touch')
                df = df.append({'self_touch': 1}, ignore_index=True)
            else:
                #print('no self touch')
                df = df.append({'self_touch': 0}, ignore_index=True)
    return df

def measure_mask(img, threshold):

    """
    Returns the number of values above a threshold and the sum of its values
    """
    roi = img >= threshold
    n_values = np.sum(roi)
    intensity = np.sum(img[roi])

    return n_values, intensity

def distance_to_image_center(image_shape, point):
    """
    Calculate the distance (in px) from the center of the image to the point coords
    :param image_shape: tuple, shape of the image
    :param point: tuple, point coordinates
    :return: np.array containing the x,y distance
    """
    center = np.asarray(image_shape)/2
    result = np.asarray(point) - center
    return result



#if __name__ == "__main__":
    # import matplotlib.pyplot as plt
    # import pandas as pd
    # import glob
    #
    # project_path = '/Volumes/scratch/neurobiology/zimmer/ulises/active_sensing/epifluorescence_recordings/20220408/data/ZIM1661_worm3/'
    # img_path = '/Volumes/scratch/neurobiology/zimmer/ulises/active_sensing/epifluorescence_recordings/20220408/data/ZIM1661_worm3/2022-04-08_17-22-49_ZIM1661_BAG_worm3-channel-0-behaviour-/2022-04-08_17-22-49_ZIM1661_BAG_worm3-channel-0-behaviour-bigtiff.btf'
    #
    # dlc_coords = '/Volumes/scratch/neurobiology/zimmer/ulises/active_sensing/epifluorescence_recordings/20220408/data/ZIM1661_worm3/2022-04-08_17-22-49_ZIM1661_BAG_worm3-channel-0-behaviour-/2022-04-08_17-22-49_ZIM1661_BAG_worm3-channel-0-behaviour-bigtiffDLC_resnet50_new_worms_5_7_8Apr15shuffle1_57500.h5'
    #
    # center_coords = pd.read_csv(glob.glob(os.path.join(project_path, '*TablePos*'))[0])
    # center_coords = center_coords[['X', 'Y']].values
    # df = pd.read_hdf(dlc_coords)
    # df.head()
    # points = df[df.columns.levels[0][0]]['head'][['x', 'y']][:].values
    # with tiff.TiffFile(img_path) as tif:
    #     img_shape = tif.pages[0].asarray().shape
    #     print('img shape is', img_shape)
    # # img_shape = (900, 900)
    # # points = ([800, 400], [150, 500], [450, 460])
    # # center_coords = ([2, 0], [3, -1], [4, -2])
    # result = distance_to_image_center(img_shape, points)
    #
    # px2mm_ratio = 0.00325
    #
    # print(result)
    # #print(type(result))
    # result_mm = result * px2mm_ratio
    #
    # abs_coords = center_coords + result_mm
    # print(abs_coords)
    #
    # # plt.plot(points)
    # # plt.plot(abs_coords)
    # # plt.show()
    # # fig, ax = plt.subplots()
    # # ax.scatter(abs_coords[:, 0], abs_coords[:, 1])
    # abs_coords_df=pd.DataFrame(abs_coords)
    # print(os.path.join(project_path, 'nose_coords_mm.csv'))
    # abs_coords_df.to_csv(os.path.join(project_path, 'nose_coords_mm.csv'))
    # print('end')

# input_filepath='/Users/ulises.rey/local_data/epifluorescence/2022-04-08_16-12_ZIM1661_BAG_worm1_Ch1bigtiff_masked.btf'
# with tiff.TiffFile(input_filepath) as tif:
#     for i, page in enumerate(tif.pages):
#         img=page.asarray()
#         n_values, intensity = measure_mask(img, 250)
#         print(i, n_values, intensity)
#         #if intensity!=intensity2: print("False")
#         if i == 500: break
