'''
This script corrects head-tail swaps and jumps in DeepLabCut output data.
It uses dynamic window-based correction and a Hampel filter to identify and fix
potential errors in animal tracking data. The script processes H5 files,
applies corrections, and saves the results in both H5 and CSV formats.

Key features:
1. Dynamic stable window detection for coordinate correction
2. Head-tail swap correction based on dynamic thresholds
3. Hampel filter for jump correction
4. Command-line interface for easy use
5. Supports custom body part names and window sizes
'''

'''
rule correct_head_tail_swaps:
    input:
        h5_file = "{datasets_output}track"+config["network_string"]+".h5"  
    output:
        corrected_csv = "{datasets_output}track"+config["network_string"]+"_corrected.csv",
        hdf5_file = "{datasets_output}track"+config["network_string"]+"_corrected.h5"
    params:
        head = config['nose'], 
        tail = config['tail'],
        window = 20,
    run:
        from imutils.src import DLC_head_tail_swap_correction_argparse_v02 as head_tail_correction

        head_tail_correction.main([
            str(input.h5_file),
            "--output_file_path", str(output.hdf5_file),  # Ensure the correct file is passed here
            "--head", str(params.head),
            "--tail", str(params.tail),
            "--window", str(params.window),
        ])

'''

import argparse
import sys
import pandas as pd
import numpy as np
import os


def find_dynamic_stable_window(df, scorer, body_part, coord, current_frame, window_size, threshold):
    """
    Finds a dynamic stable window for a specific coordinate (x or y) of a body part,
    centered around the current frame.

    Parameters:
    - df: pandas DataFrame containing the tracking data.
    - scorer: string, name of the scorer in the DataFrame.
    - body_part: string, name of the body part (e.g., head).
    - coord: string, coordinate to check ('x' or 'y').
    - current_frame: integer, the current frame around which the window is centered.
    - window_size: integer, size of the window to consider.
    - threshold: float, maximum allowed standard deviation to consider the window stable.

    Returns:
    - avg_value: float, average value of the coordinate in the stable window.
    """
    # Define the window range, ensuring it's within the DataFrame bounds
    window_start = max(current_frame - window_size, 0)
    window_end = min(current_frame + 1, len(df))  # Add 1 to include the current frame

    # Get the windowed segment
    window = df.iloc[window_start:window_end]

    # Calculate the standard deviation for the given coordinate
    std_dev = window[scorer][body_part][coord].std()

    # Check if the standard deviation is below the threshold
    if std_dev < threshold:
        # Stable window found
        avg_value = window[scorer][body_part][coord].mean()
        return avg_value
    else:
        # If not stable, fall back to using the current frame's value as reference
        return df.at[current_frame, (scorer, body_part, coord)]


def correct_head_coord_with_dynamic_window(df, scorer, head_name, tail_name, window_size):
    """
    Corrects the head's x and y coordinates using a reference from a dynamic stable window.
    The window updates dynamically based on the current frame being processed.
    If the current frame's value is outside the dynamic threshold, it swaps the head coordinate with the tail coordinate.

    Parameters:
    - df: pandas DataFrame containing the tracking data.
    - scorer: string, name of the scorer in the DataFrame.
    - head_name: string, name of the head body part.
    - tail_name: string, name of the tail body part.
    - window_size: integer, size of the dynamic window to find the stable segment.

    Returns:
    - df_corrected: pandas DataFrame with corrected head positions.
    """
    total_frames = len(df)

    # Calculate the average distances between head and tail for x and y
    avg_distance_x = (df[scorer][head_name]['x'] - df[scorer][tail_name]['x']).abs().mean()
    avg_distance_y = (df[scorer][head_name]['y'] - df[scorer][tail_name]['y']).abs().mean()

    # Compute the dynamic threshold as 50% of the average of avg_distance_x and avg_distance_y
    average_avg_distance = (avg_distance_x + avg_distance_y) / 2
    dynamic_threshold = average_avg_distance * 0.5

    print(f"Dynamic threshold: {dynamic_threshold}")

    # Iterate over each coordinate (x and y) for the head
    for coord in ['x', 'y']:
        # Forward correction with dynamic window
        for frame in range(total_frames):
            # Find the dynamic stable window for the current coordinate
            avg_value = find_dynamic_stable_window(
                df, scorer, head_name, coord, frame, window_size, dynamic_threshold)

            current_value = df.at[frame, (scorer, head_name, coord)]
            # Check if the current value is within acceptable limits (threshold)
            if abs(current_value - avg_value) > dynamic_threshold:
                # Swap the head coordinate with the tail coordinate
                tail_value = df.at[frame, (scorer, tail_name, coord)]

                # Perform the swap
                df.at[frame, (scorer, head_name, coord)] = tail_value
                df.at[frame, (scorer, tail_name, coord)] = current_value

    return df

def hampel_filter(data, window_size=5, n_sigmas=3):
    """
    Apply the Hampel filter to detect and correct outliers.

    Args:
        data (np.array or pd.Series): The data to filter.
        window_size (int): Size of the moving window; must be odd.
        n_sigmas (float): Number of standard deviations for outlier detection.

    Returns:
        np.array: The filtered data with outliers corrected.
    """
    n = len(data)
    filtered_data = data.copy()
    k = 1.4826  # Scaling factor for Gaussian distribution
    half_window = (window_size - 1) // 2

    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        window = data[start:end]
        median = np.median(window)
        MAD = k * np.median(np.abs(window - median))
        threshold = n_sigmas * MAD
        difference = np.abs(data[i] - median)
        if difference > threshold:
            filtered_data[i] = median
    return filtered_data

def correct_jumps_in_df(df, scorer, body_parts, coords, window_size=5, n_sigmas=3):
    """
    Correct jumps in the DataFrame for specified body parts and coordinates.

    Args:
        df (pd.DataFrame): The DataFrame containing the coordinate data.
        scorer (str): The name of the scorer.
        body_parts (list): List of body parts to process.
        coords (list): List of coordinates to process (default ['x', 'y']).
        window_size (int): Window size for the Hampel filter.
        n_sigmas (float): Number of standard deviations for threshold.

    Returns:
        pd.DataFrame: The DataFrame with corrected data.
    """
    corrected_df = df.copy()
    for body_part in body_parts:
        for coord in coords:
            data = df[scorer][body_part][coord]
            corrected_data = hampel_filter(data.values, window_size=window_size, n_sigmas=n_sigmas)
            # Use .loc to avoid SettingWithCopyWarning
            corrected_df.loc[:, (scorer, body_part, coord)] = corrected_data

    return corrected_df


def save_data(df, input_file_path, output_file_path):
    # Extract the model name from the input file path
    file_name = os.path.basename(input_file_path)
    model_name = file_name.split('_filtered.h5')[0].split('track')[1]

    # Save as H5
    df.to_hdf(output_file_path, key='df', mode='w')
    print(f"Corrected H5 data saved to {output_file_path}")

    # Save as CSV
    output_csv_path = output_file_path.replace('.h5', '.csv')
    df.to_csv(output_csv_path)
    print(f"Corrected CSV data saved to {output_csv_path}")

    return model_name

def main(arg_list=None):
    parser = argparse.ArgumentParser(description="Correct head-tail swaps in DeepLabCut output")
    parser.add_argument("input_file_path", help="Path to the input H5 file")
    parser.add_argument("--output_file_path", required=True, help="Path to the output H5 file")
    parser.add_argument("--head", default="head", help="Name of the head bodypart (default: head)")
    parser.add_argument("--tail", default="tail", help="Name of the tail bodypart (default: tail)")
    parser.add_argument("--window", type=int, default=20, help="Window size for averaging (default: 20)")

    args = parser.parse_args(arg_list)

    try:
        # Perform the head-tail correction operation
        df = pd.read_hdf(args.input_file_path)

        # Check if the dataframe is empty
        if df.empty:
            print(f"The input H5 file '{args.input_file_path}' is empty.")

            # Create empty DataFrame and save as H5 and CSV using pandas
            empty_df = pd.DataFrame()

            # Save empty DataFrame as H5
            empty_df.to_hdf(args.output_file_path, key='df', mode='w')
            print(f"Empty H5 file created at {args.output_file_path}")

            # Save empty DataFrame as CSV
            output_csv_path = args.output_file_path.replace('.h5', '.csv')
            empty_df.to_csv(output_csv_path)
            print(f"Empty CSV file created at {output_csv_path}")

            # Exit after creating the empty files
            sys.exit(1)

        scorer = df.columns.get_level_values(0)[0]

        df_corrected = correct_head_coord_with_dynamic_window(
            df,
            scorer=scorer,
            head_name=args.head,
            tail_name=args.tail,
            window_size=args.window
        )

        # Correct the jumps in your DataFrame
        df_corrected = correct_jumps_in_df(
            df_corrected,
            scorer=scorer,
            body_parts=[str(args.head), str(args.tail)],
            coords=['x', 'y'],
            window_size=args.window,
            n_sigmas=1
        )

        save_data(df_corrected, args.input_file_path, args.output_file_path)
        print("Processing completed successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])