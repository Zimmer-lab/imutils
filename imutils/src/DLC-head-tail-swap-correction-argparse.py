import argparse
import sys
import pandas as pd
import numpy as np

def correct_head_tail_swaps(csv_path, head_name, tail_name, window_size, threshold_distance):
    # Load the CSV file
    df = pd.read_csv(csv_path, header=[0, 1])  # 2-level multi-index
    
    # Extract x and y coordinates for head and tail
    head_x = df[head_name]['x'].values
    head_y = df[head_name]['y'].values
    tail_x = df[tail_name]['x'].values
    tail_y = df[tail_name]['y'].values
    
    total_frames = len(df)
    swaps = []

    for frame in range(total_frames):
        # Determine the window range
        start = max(0, frame - window_size)
        end = min(total_frames, frame + window_size + 1)
        
        # Calculate average positions excluding the current frame
        avg_head_x = (np.sum(head_x[start:frame]) + np.sum(head_x[frame+1:end])) / (end - start - 1)
        avg_head_y = (np.sum(head_y[start:frame]) + np.sum(head_y[frame+1:end])) / (end - start - 1)
        avg_tail_x = (np.sum(tail_x[start:frame]) + np.sum(tail_x[frame+1:end])) / (end - start - 1)
        avg_tail_y = (np.sum(tail_y[start:frame]) + np.sum(tail_y[frame+1:end])) / (end - start - 1)
        
        # Calculate distances
        head_to_avg_head = np.sqrt((head_x[frame] - avg_head_x)**2 + (head_y[frame] - avg_head_y)**2)
        tail_to_avg_tail = np.sqrt((tail_x[frame] - avg_tail_x)**2 + (tail_y[frame] - avg_tail_y)**2)
        head_to_avg_tail = np.sqrt((head_x[frame] - avg_tail_x)**2 + (head_y[frame] - avg_tail_y)**2)
        tail_to_avg_head = np.sqrt((tail_x[frame] - avg_head_x)**2 + (tail_y[frame] - avg_head_y)**2)
        
        # Check if a swap occurred
        if (head_to_avg_tail < threshold_distance and tail_to_avg_head < threshold_distance and
            head_to_avg_tail < head_to_avg_head and tail_to_avg_head < tail_to_avg_tail):
            swaps.append(frame)
    
    # Correct swaps
    for swap in swaps:
        df.loc[swap, (head_name, 'x')], df.loc[swap, (tail_name, 'x')] = df.loc[swap, (tail_name, 'x')], df.loc[swap, (head_name, 'x')]
        df.loc[swap, (head_name, 'y')], df.loc[swap, (tail_name, 'y')] = df.loc[swap, (tail_name, 'y')], df.loc[swap, (head_name, 'y')]
    
    # Save corrected data
    output_path = csv_path.replace('.csv', f'_corrected_w{window_size}.csv')
    df.to_csv(output_path, index=False)
    print(f"Corrected data saved to {output_path}")
    print(f"Number of swaps detected and corrected: {len(swaps)}")

def main(arg_list=None):
    parser = argparse.ArgumentParser(description="Correct head-tail swaps in DeepLabCut CSV output")
    parser.add_argument("csv_path", help="Path to the input CSV file")
    parser.add_argument("--head", default="head", help="Name of the head bodypart in the CSV (default: head)")
    parser.add_argument("--tail", default="tail", help="Name of the tail bodypart in the CSV (default: tail)")
    parser.add_argument("--window", type=int, default=20, help="Window size for averaging (default: 20)")
    parser.add_argument("--threshold", type=float, default=10, help="Distance threshold for swap detection (default: 10)")
    
    args = parser.parse_args(arg_list)
    
    correct_head_tail_swaps(args.csv_path, args.head, args.tail, args.window, args.threshold)

if __name__ == "__main__":
    main(sys.argv[1:])
