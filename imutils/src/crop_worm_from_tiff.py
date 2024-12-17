'''
This script processes TIFF images by segmenting, cropping, and analyzing regions of interest (ROIs) based on the largest segmented region in each frame. It performs the following:

Frame Processing: For each frame in the TIFF stack, it segments the image to find regions, calculates the centroid of the largest region, and crops the image around this centroid.
Cropping: The frame is cropped around the largest region to a specified size.
ROI Data Collection: The coordinates of the top-left corner of each crop (ROI) are recorded.
Excel Output: The ROI coordinates (x and y) are saved in an Excel file.
TIFF File Output: The cropped frames are saved to a new TIFF file.

In summary, the script processes RAW DATA TIFF image stacks by cropping and analyzing regions based on the largest object, saving both the cropped images and the ROI data to specified output files.

'''


import os
import tifffile
import numpy as np
from skimage import measure
import argparse
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from imutils.scopedatamanager import MicroscopeDataReader
import dask.array as da
import tifffile as tiff

def process_frame(frame, crop_size):
    crop_width, crop_height = crop_size

    # Segment the image
    labeled_frame = measure.label(frame)
    regions = measure.regionprops(labeled_frame)

    if not regions:
        print("No regions found. Returning a blank frame.")
        return np.zeros(crop_size, dtype=frame.dtype), 0, 0

    # Sort regions by area and get the largest
    largest_region = max(regions, key=lambda r: r.area)

    # Get the centroid of the largest region
    centroid_y, centroid_x = largest_region.centroid

    # Calculate the top-left corner of the crop area, ensuring it doesn't go out of bounds
    start_x = int(max(min(centroid_x - crop_width // 2, frame.shape[1] - crop_width), 0))
    start_y = int(max(min(centroid_y - crop_height // 2, frame.shape[0] - crop_height), 0))

    # Crop the frame
    cropped_frame = frame[start_y:start_y + crop_height, start_x:start_x + crop_width]

    return cropped_frame, start_x, start_y

def crop_tiff(path, output_path, crop_size):
    print(f"Cropping: {path}")

    x_roi_data = []
    y_roi_data = []

    reader_obj = MicroscopeDataReader(args.input_file_path, as_raw_tiff=True, raw_tiff_num_slices=1)
    tif = da.squeeze(reader_obj.dask_array)

    with tiff.TiffWriter(args.output_file_path, bigtiff=True) as tif_writer:

        cropped_data = []

        for i, img in enumerate(tif):

            frame =  np.array(img)
            result = process_frame(frame, crop_size)

            if result is None:
                # Handle empty frame case - e.g., skip or use a blank frame
                blank_frame = np.zeros(crop_size, dtype=np.uint8)
                tif_writer.write(blank_frame, contiguous=True)
                continue

            cropped_frame, start_x, start_y = result

            tif_writer.write(cropped_frame, contiguous=True)

            x_roi_data.append(start_x)
            y_roi_data.append(start_y)

    return x_roi_data, y_roi_data


def save_to_excel(x_roi_data, y_roi_data, excel_file):
    # Create a DataFrame with the appropriate column names
    df = pd.DataFrame({
        'x_roi': x_roi_data,
        'y_roi': y_roi_data
    })

    # Ensure the file ends with '.xlsx'
    if not excel_file.endswith('.xlsx'):
        excel_file += '.xlsx'

    # Save the DataFrame to an Excel file
    df.to_excel(excel_file, index=False)
    print(f"ROI data saved to {excel_file}")

def main(arg_list=None):

    #print(arg_list)
    parser = argparse.ArgumentParser(description="crop_worm_from_binary_mask_tiff")
    parser.add_argument("--binary_stack", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--crop_size", required=True, help="Crop size in format 'width,height'")
    parser.add_argument("--excel_file", required=True, help="Output Excel file to store ROI data")
    args = parser.parse_args(arg_list)

    path = args.binary_stack
    output = args.output
    excel_file = args.excel_file
    crop_size = tuple(map(int, args.crop_size.split(',')))

    search_margin = 50  # Define how far from the last known position to search, adjust as needed

    print(f"Excel file path: {excel_file}")
    print("Processing TIFF...")
    x_roi_data, y_roi_data = crop_tiff(path, output, crop_size)

    print("Saving ROI data to Excel file...")
    save_to_excel(x_roi_data, y_roi_data, excel_file)


if __name__ == "__main__":

    print("Shell commands passed:", sys.argv)
    main(sys.argv[1:])  # exclude the script name from the args when called from shell


