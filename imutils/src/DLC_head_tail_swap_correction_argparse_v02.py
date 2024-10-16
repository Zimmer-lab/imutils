import argparse
import sys
import pandas as pd
import numpy as np
import os

def correct_head_tail_swaps(df, head_name, tail_name):
    """
    Correct head-tail swaps in tracking data by comparing positions frame by frame
    with dynamic thresholding based on the previous head-tail distance.

    Parameters:
    - df: pandas DataFrame containing the tracking data.
    - head_name: string, name of the head body part in the DataFrame.
    - tail_name: string, name of the tail body part in the DataFrame.

    Returns:
    - df_corrected: pandas DataFrame with corrected head and tail positions.
    """
    # Get the scorer name from the DataFrame columns
    scorer = df.columns.get_level_values(0)[0]
    total_frames = len(df)
    swaps = []

    # Iterate over frames starting from the second frame
    for frame in range(1, total_frames):
        # Get head and tail positions for previous frame
        head_x_prev = df.loc[frame - 1, (scorer, head_name, 'x')]
        head_y_prev = df.loc[frame - 1, (scorer, head_name, 'y')]
        tail_x_prev = df.loc[frame - 1, (scorer, tail_name, 'x')]
        tail_y_prev = df.loc[frame - 1, (scorer, tail_name, 'y')]

        # Compute previous head-tail distance
        D_prev = np.sqrt((head_x_prev - tail_x_prev)**2 + (head_y_prev - tail_y_prev)**2)

        # Handle potential division by zero
        if D_prev == 0:
            D_prev = 1e-5  # Small number to avoid division by zero

        # Get head and tail positions for current frame
        head_x_curr = df.loc[frame, (scorer, head_name, 'x')]
        head_y_curr = df.loc[frame, (scorer, head_name, 'y')]
        tail_x_curr = df.loc[frame, (scorer, tail_name, 'x')]
        tail_y_curr = df.loc[frame, (scorer, tail_name, 'y')]

        # Compute head movement from previous frame to current frame
        H_move = np.sqrt((head_x_curr - head_x_prev)**2 + (head_y_curr - head_y_prev)**2)
        T_move = np.sqrt((tail_x_curr - tail_x_prev)**2 + (tail_y_curr - tail_y_prev)**2)
        total_movement = H_move + T_move

        # Check if head movement exceeds 90% of previous head-tail distance
        if H_move > 0.9 * D_prev:
            # Possible head-tail swap detected, attempt to swap
            # Compute movements if we swap head and tail
            swapped_H_move = np.sqrt((tail_x_curr - head_x_prev)**2 + (tail_y_curr - head_y_prev)**2)
            swapped_T_move = np.sqrt((head_x_curr - tail_x_prev)**2 + (head_y_curr - tail_y_prev)**2)
            swapped_total_movement = swapped_H_move + swapped_T_move

            # If swapping reduces the total movement, perform the swap
            if swapped_total_movement < total_movement:
                # Perform swap
                df.loc[frame, (scorer, head_name, 'x')], df.loc[frame, (scorer, tail_name, 'x')] = tail_x_curr, head_x_curr
                df.loc[frame, (scorer, head_name, 'y')], df.loc[frame, (scorer, tail_name, 'y')] = tail_y_curr, head_y_curr
                swaps.append(frame)
                print(f"Swap performed at frame {frame}: total movement reduced from {total_movement:.2f} to {swapped_total_movement:.2f}")
        # Else, no swap needed
        else:
            continue  # No action needed

    print(f"\nTotal number of swaps detected and corrected: {len(swaps)}")
    print("Frames where swaps occurred:", swaps)

    return df


def find_initial_stable_window(df, scorer, head_name, tail_name, window_size, threshold=5.0):
    """
    Finds the first stable window where the head and tail positions are consistent.

    Parameters:
    - df: pandas DataFrame containing the tracking data.
    - scorer: string, name of the scorer in the DataFrame.
    - head_name: string, name of the head body part.
    - tail_name: string, name of the tail body part.
    - window_size: integer, size of the window to consider.
    - threshold: float, maximum allowed standard deviation to consider the window stable.

    Returns:
    - start_frame: integer, starting frame of the stable window.
    - avg_head_x, avg_head_y: floats, average head positions in the window.
    - avg_tail_x, avg_tail_y: floats, average tail positions in the window.
    """
    total_frames = len(df)
    for start_frame in range(total_frames - window_size + 1):
        window = df.iloc[start_frame:start_frame + window_size]

        # Calculate positional standard deviations
        head_std = window[scorer][head_name][['x', 'y']].std().mean()
        tail_std = window[scorer][tail_name][['x', 'y']].std().mean()

        # Check if variances are below the threshold
        if head_std < threshold and tail_std < threshold:
            # Stable window found
            avg_head_x = window[scorer][head_name]['x'].mean()
            avg_head_y = window[scorer][head_name]['y'].mean()
            avg_tail_x = window[scorer][tail_name]['x'].mean()
            avg_tail_y = window[scorer][tail_name]['y'].mean()
            print(f"Stable window found starting at frame {start_frame}")
            return start_frame, avg_head_x, avg_head_y, avg_tail_x, avg_tail_y
    raise ValueError("No stable window found in the dataset")


def correct_head_tail_swaps_with_reference(df, head_name, tail_name, window_size, threshold=5.0):
    """
    Corrects head-tail swaps using a reference from an initial stable window.

    Parameters:
    - df: pandas DataFrame containing the tracking data.
    - head_name: string, name of the head body part.
    - tail_name: string, name of the tail body part.
    - window_size: integer, size of the window to find the stable segment.
    - threshold: float, maximum allowed standard deviation to consider the window stable.

    Returns:
    - df_corrected: pandas DataFrame with corrected head and tail positions.
    """
    scorer = df.columns.get_level_values(0)[0]

    # Step 1: Find initial stable window
    start_frame, avg_head_x, avg_head_y, avg_tail_x, avg_tail_y = find_initial_stable_window(
        df, scorer, head_name, tail_name, window_size, threshold)

    swaps = []
    total_frames = len(df)

    # Step 2: Backward correction
    for frame in range(start_frame - 1, -1, -1):
        # Get current positions
        head_x = df.loc[frame, (scorer, head_name, 'x')]
        head_y = df.loc[frame, (scorer, head_name, 'y')]
        tail_x = df.loc[frame, (scorer, tail_name, 'x')]
        tail_y = df.loc[frame, (scorer, tail_name, 'y')]

        # Compute distances to averages
        dist_head_to_avg_head = np.sqrt((head_x - avg_head_x) ** 2 + (head_y - avg_head_y) ** 2)
        dist_tail_to_avg_tail = np.sqrt((tail_x - avg_tail_x) ** 2 + (tail_y - avg_tail_y) ** 2)

        dist_head_to_avg_tail = np.sqrt((head_x - avg_tail_x) ** 2 + (head_y - avg_tail_y) ** 2)
        dist_tail_to_avg_head = np.sqrt((tail_x - avg_head_x) ** 2 + (tail_y - avg_head_y) ** 2)

        # Decide whether to swap
        original_total_distance = dist_head_to_avg_head + dist_tail_to_avg_tail
        swapped_total_distance = dist_head_to_avg_tail + dist_tail_to_avg_head

        if swapped_total_distance < original_total_distance:
            # Perform swap
            df.loc[frame, (scorer, head_name, 'x')], df.loc[frame, (scorer, tail_name, 'x')] = tail_x, head_x
            df.loc[frame, (scorer, head_name, 'y')], df.loc[frame, (scorer, tail_name, 'y')] = tail_y, head_y
            swaps.append(frame)
            # Update averages after swap
            head_x, head_y = tail_x, tail_y
            tail_x, tail_y = head_x, head_y

    # Step 3: Forward correction
    for frame in range(start_frame + window_size, total_frames):
        # Get current positions
        head_x = df.loc[frame, (scorer, head_name, 'x')]
        head_y = df.loc[frame, (scorer, head_name, 'y')]
        tail_x = df.loc[frame, (scorer, tail_name, 'x')]
        tail_y = df.loc[frame, (scorer, tail_name, 'y')]

        # Compute distances to averages
        dist_head_to_avg_head = np.sqrt((head_x - avg_head_x) ** 2 + (head_y - avg_head_y) ** 2)
        dist_tail_to_avg_tail = np.sqrt((tail_x - avg_tail_x) ** 2 + (tail_y - avg_tail_y) ** 2)

        dist_head_to_avg_tail = np.sqrt((head_x - avg_tail_x) ** 2 + (head_y - avg_tail_y) ** 2)
        dist_tail_to_avg_head = np.sqrt((tail_x - avg_head_x) ** 2 + (tail_y - avg_head_y) ** 2)

        # Decide whether to swap
        original_total_distance = dist_head_to_avg_head + dist_tail_to_avg_tail
        swapped_total_distance = dist_head_to_avg_tail + dist_tail_to_avg_head

        if swapped_total_distance < original_total_distance:
            # Perform swap
            df.loc[frame, (scorer, head_name, 'x')], df.loc[frame, (scorer, tail_name, 'x')] = tail_x, head_x
            df.loc[frame, (scorer, head_name, 'y')], df.loc[frame, (scorer, tail_name, 'y')] = tail_y, head_y
            swaps.append(frame)
            # Update averages after swap
            head_x, head_y = tail_x, tail_y
            tail_x, tail_y = head_x, head_y

    print(f"\nTotal number of swaps detected and corrected: {len(swaps)}")
    print("Frames where swaps occurred:", sorted(swaps))

    return df

def final_alignment(df_original, df_corrected, head_name, tail_name):
    """
    Performs final alignment by checking if swapping head and tail in corrected data
    results in better alignment with the original data.

    Parameters:
    - df_original: pandas DataFrame with original tracking data.
    - df_corrected: pandas DataFrame with corrected tracking data.
    - head_name: string, name of the head body part.
    - tail_name: string, name of the tail body part.

    Returns:
    - df_aligned: pandas DataFrame with final aligned data.
    """
    scorer = df_original.columns.get_level_values(0)[0]

    # Compute total difference between original and corrected data
    head_diff_x = df_corrected.loc[:, (scorer, head_name, 'x')] - df_original.loc[:, (scorer, head_name, 'x')]
    head_diff_y = df_corrected.loc[:, (scorer, head_name, 'y')] - df_original.loc[:, (scorer, head_name, 'y')]
    tail_diff_x = df_corrected.loc[:, (scorer, tail_name, 'x')] - df_original.loc[:, (scorer, tail_name, 'x')]
    tail_diff_y = df_corrected.loc[:, (scorer, tail_name, 'y')] - df_original.loc[:, (scorer, tail_name, 'y')]

    total_difference = np.sum(np.abs(head_diff_x) + np.abs(head_diff_y) + np.abs(tail_diff_x) + np.abs(tail_diff_y))

    # Create a swapped version of df_corrected
    df_swapped = df_corrected.copy()

    # Swap the head and tail data in df_swapped
    temp_head_x = df_swapped.loc[:, (scorer, head_name, 'x')].copy()
    temp_head_y = df_swapped.loc[:, (scorer, head_name, 'y')].copy()

    df_swapped.loc[:, (scorer, head_name, 'x')] = df_corrected.loc[:, (scorer, tail_name, 'x')].values
    df_swapped.loc[:, (scorer, head_name, 'y')] = df_corrected.loc[:, (scorer, tail_name, 'y')].values

    df_swapped.loc[:, (scorer, tail_name, 'x')] = temp_head_x.values
    df_swapped.loc[:, (scorer, tail_name, 'y')] = temp_head_y.values

    # Compute total difference between original data and swapped corrected data
    head_diff_swapped_x = df_swapped.loc[:, (scorer, head_name, 'x')] - df_original.loc[:, (scorer, head_name, 'x')]
    head_diff_swapped_y = df_swapped.loc[:, (scorer, head_name, 'y')] - df_original.loc[:, (scorer, head_name, 'y')]
    tail_diff_swapped_x = df_swapped.loc[:, (scorer, tail_name, 'x')] - df_original.loc[:, (scorer, tail_name, 'x')]
    tail_diff_swapped_y = df_swapped.loc[:, (scorer, tail_name, 'y')] - df_original.loc[:, (scorer, tail_name, 'y')]

    total_difference_swapped = np.sum(
        np.abs(head_diff_swapped_x) + np.abs(head_diff_swapped_y) +
        np.abs(tail_diff_swapped_x) + np.abs(tail_diff_swapped_y)
    )

    print(f"Total difference without swapping: {total_difference}")
    print(f"Total difference after swapping: {total_difference_swapped}")

    if total_difference_swapped < total_difference:
        # Swapping improves alignment, so use df_swapped
        df_aligned = df_swapped
        print("Swapped head and tail in corrected data for final alignment.")
    else:
        df_aligned = df_corrected
        print("No need to swap head and tail in corrected data.")

    return df_aligned

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

    return model_name

def main(arg_list=None):
    parser = argparse.ArgumentParser(description="Correct head-tail swaps in DeepLabCut output")
    parser.add_argument("input_file_path", help="Path to the input H5 file")
    parser.add_argument("--output_file_path", required=True, help="Path to the output H5 file")
    parser.add_argument("--head", default="head", help="Name of the head bodypart (default: head)")
    parser.add_argument("--tail", default="tail", help="Name of the tail bodypart (default: tail)")
    parser.add_argument("--window", type=int, default=20, help="Window size for averaging (default: 20)")
    parser.add_argument("--threshold", type=float, default=10, help="Distance threshold for swap detection (default: 10)")

    args = parser.parse_args(arg_list)

    # Perform the head-tail correction operation
    df = pd.read_hdf(args.input_file_path)

    df_original = df.copy()

    # Correct head-tail swaps
    df_corrected = correct_head_tail_swaps(df, args.head, args.tail)

    # Correct head-tail swaps using the new function
    df_corrected = correct_head_tail_swaps_with_reference(df_corrected, args.head, args.tail, args.window, args.threshold)

    # Perform final alignment
    df_aligned = final_alignment(df_original, df_corrected, args.head, args.tail)

    save_data(df_aligned, args.input_file_path, args.output_file_path)


if __name__ == "__main__":
    main(sys.argv[1:])