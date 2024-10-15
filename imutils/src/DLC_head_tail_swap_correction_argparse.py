import argparse
import sys
import pandas as pd
import numpy as np

def read_DLC_csv(csv_file_path):

    df = pd.read_csv(csv_file_path)

    #remove column names and set first row to new column name
    df.columns = df.iloc[0]
    df = df[1:]

    # Get the first row (which will become the second level of column names)
    second_level_names = df.iloc[0]

    # Create a MultiIndex for columns using the existing column names as the first level
    first_level_names = df.columns
    multi_index = pd.MultiIndex.from_arrays([first_level_names, second_level_names])

    # Set the new MultiIndex as the columns of the DataFrame
    df.columns = multi_index

    # Remove the first row from the DataFrame as it's now used for column names
    df = df.iloc[1:]

    # Removing the first column (index 0)
    df = df.drop(df.columns[0], axis=1)
    df = df.reset_index(drop=True)

    # Convert each column to numeric, coerce errors to NaN
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(isinstance(df.columns, pd.MultiIndex))
    print(list(df.columns))

    return df

def correct_head_tail_swaps(df, output_file_path, head_name, tail_name, window_size, threshold_distance):
    
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

    # Extract the model name from the input file path
    file_name = os.path.basename(input_file_path)
    model_name = file_name.split('_filtered.csv')[0].split('track')[1]

    # Add the scorer row
    scorer_row = pd.DataFrame([[model_name] * len(df.columns)],
                              columns=df.columns)
    df = pd.concat([scorer_row, df]).reset_index(drop=True)

    # Rename the first row to 'scorer'
    df.rename(index={0: 'scorer'}, inplace=True)

    df.to_csv(output_file_path, index=False)
    print(f"Corrected CSV data saved to {output_file_path}")

    # Save corrected data as H5
    output_h5_path = output_file_path.replace('.csv', '.h5')
    df.to_hdf(output_h5_path, key='df', mode='w')
    print(f"Corrected H5 data saved to {output_h5_path}")

    print(f"Number of swaps detected and corrected: {len(swaps)}")

def main(arg_list=None):
    parser = argparse.ArgumentParser(description="Correct head-tail swaps in DeepLabCut CSV output")
    parser.add_argument("csv_path", help="Path to the input CSV file")
    parser.add_argument("--output_file_path", help="Path to the input CSV file")
    parser.add_argument("--head", default="head", help="Name of the head bodypart in the CSV (default: head)")
    parser.add_argument("--tail", default="tail", help="Name of the tail bodypart in the CSV (default: tail)")
    parser.add_argument("--window", type=int, default=20, help="Window size for averaging (default: 20)")
    parser.add_argument("--threshold", type=float, default=10, help="Distance threshold for swap detection (default: 10)")
    
    args = parser.parse_args(arg_list)

    DLC_data = read_DLC_csv(args.csv_path)

    correct_head_tail_swaps(DLC_data, args.output_file_path, args.head, args.tail, args.window, args.threshold)

if __name__ == "__main__":
    main(sys.argv[1:])
