import argparse
import sys
import pandas as pd
import numpy as np
import os


def correct_head_tail_swaps(df, input_file_path, output_file_path, head_name, tail_name, window_size, threshold_distance):
    scorer = df.columns.get_level_values(0)[0]

    # Extract x and y coordinates for head and tail
    head_x = df[scorer][head_name]['x'].values
    head_y = df[scorer][head_name]['y'].values
    tail_x = df[scorer][tail_name]['x'].values
    tail_y = df[scorer][tail_name]['y'].values

    total_frames = len(df)
    swaps = []

    for frame in range(total_frames):
        # Determine the window range
        start = max(0, frame - window_size)
        end = min(total_frames, frame + window_size + 1)

        # Calculate average positions excluding the current frame
        avg_head_x = (np.sum(head_x[start:frame]) + np.sum(head_x[frame + 1:end])) / (end - start - 1)
        avg_head_y = (np.sum(head_y[start:frame]) + np.sum(head_y[frame + 1:end])) / (end - start - 1)
        avg_tail_x = (np.sum(tail_x[start:frame]) + np.sum(tail_x[frame + 1:end])) / (end - start - 1)
        avg_tail_y = (np.sum(tail_y[start:frame]) + np.sum(tail_y[frame + 1:end])) / (end - start - 1)

        # Calculate distances
        head_to_avg_head = np.sqrt((head_x[frame] - avg_head_x) ** 2 + (head_y[frame] - avg_head_y) ** 2)
        tail_to_avg_tail = np.sqrt((tail_x[frame] - avg_tail_x) ** 2 + (tail_y[frame] - avg_tail_y) ** 2)
        head_to_avg_tail = np.sqrt((head_x[frame] - avg_tail_x) ** 2 + (head_y[frame] - avg_tail_y) ** 2)
        tail_to_avg_head = np.sqrt((tail_x[frame] - avg_head_x) ** 2 + (tail_y[frame] - avg_head_y) ** 2)

        # Check if a swap occurred
        if (head_to_avg_tail < threshold_distance and tail_to_avg_head < threshold_distance and
                head_to_avg_tail < head_to_avg_head and tail_to_avg_head < tail_to_avg_tail):
            swaps.append(frame)

    # Correct swaps
    for swap in swaps:
        df.loc[swap, (scorer, head_name, 'x')], df.loc[swap, (scorer, tail_name, 'x')] = df.loc[
            swap, (scorer, tail_name, 'x')], df.loc[swap, (scorer, head_name, 'x')]
        df.loc[swap, (scorer, head_name, 'y')], df.loc[swap, (scorer, tail_name, 'y')] = df.loc[
            swap, (scorer, tail_name, 'y')], df.loc[swap, (scorer, head_name, 'y')]

    # Extract the model name from the input file path
    file_name = os.path.basename(input_file_path)
    model_name = file_name.split('_filtered.h5')[0].split('track')[1]


    df.to_hdf(output_file_path, key='df', mode='w')
    print(f"Corrected H5 data saved to {output_file_path}")

    # Save as CSV
    output_csv_path = output_file_path.replace('.h5', '.csv')
    df.to_csv(output_csv_path)
    print(f"Corrected CSV data saved to {output_csv_path}")

    print(f"Number of swaps detected and corrected: {len(swaps)}")


def main(arg_list=None):
    parser = argparse.ArgumentParser(description="Correct head-tail swaps in DeepLabCut output")
    parser.add_argument("input_file_path", help="Path to the input H5 file")
    parser.add_argument("output_file_path", help="Path to the output H5 file")
    parser.add_argument("--head", default="head", help="Name of the head bodypart (default: head)")
    parser.add_argument("--tail", default="tail", help="Name of the tail bodypart (default: tail)")
    parser.add_argument("--window", type=int, default=20, help="Window size for averaging (default: 20)")
    parser.add_argument("--threshold", type=float, default=10,
                        help="Distance threshold for swap detection (default: 10)")

    args = parser.parse_args(arg_list)

    df = pd.read_hdf(args.input_file_path)

    correct_head_tail_swaps(df, args.input_file_path, args.output_file_path, args.head, args.tail, args.window,
                            args.threshold)


if __name__ == "__main__":
    main(sys.argv[1:])