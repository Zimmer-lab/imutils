#!/usr/bin/env python3
"""
NDTIFF Dataset Renamer Using Direct ndstorage API

This script renames NDTIFF microscope datasets by either cleaning the existing name
or using a provided new name. It places renamed datasets directly in the specified destination.

The script can process:
- A single dataset folder
- A parent folder containing multiple dataset subfolders

Usage:
    python ndtiff_direct_renamer.py --src_folder /path/to/source --dst_folder /path/to/destination [--new_name NewName]
"""

import argparse
import re
import os
import gc
from pathlib import Path
from tqdm import tqdm
import numpy as np
from datetime import datetime

from imutils import MicroscopeDataReader
from imutils import MicroscopeDataWriter

def clean_name(name):
    """Clean a dataset name by removing/replacing unallowed characters."""
    # Replace spaces, periods, and special characters with underscores
    cleaned = re.sub(r'[^\w\-]', '_', name)  # Removed the \. to exclude periods
    # Remove any leading/trailing underscores
    cleaned = cleaned.strip('_')
    # Replace multiple consecutive underscores with a single one
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned

def is_tiff_dataset(folder_path):
    """Check if a folder contains .tif files directly."""
    path = Path(folder_path)
    return any(file.suffix.lower() in ['.tif', '.tiff'] for file in path.glob('*.*'))

def process_dataset(src_path, dst_path, dataset_name=None, verbose=False):
    """Process a single NDTIFF dataset."""
    # Determine dataset name if not provided
    if not dataset_name:
        dataset_name = clean_name(src_path.name)
        if verbose:
            print(f"Original name: {src_path.name}")
            print(f"Cleaned name: {dataset_name}")
    
    print(f"Processing dataset: {src_path} → {dst_path / dataset_name}")
    
    reader_obj = None
    my_dataset = None
    
    try:
        reader_obj = MicroscopeDataReader(src_path)
        
        if verbose:
            print(f"Summary metadata: {reader_obj.get_summary_metadata()}")

        # Create dataset with metadata
        my_dataset = MicroscopeDataWriter(
            dataset_path=dst_path, 
            dataset_name=dataset_name,
            summary_metadata=reader_obj.get_summary_metadata()
        )
        
        # Get dataset dimensions
        positions = reader_obj.get_number_of_positions()
        timepoints = reader_obj.get_number_of_timepoints()
        channels = reader_obj.get_number_of_channels()
        z_slices = reader_obj.get_number_of_z_slices()
        
        # Calculate total number of images for progress bar
        total_images = positions * timepoints * channels * z_slices
        
        # Create progress bar
        progress_bar = tqdm(total=total_images, desc=f"Processing {dataset_name}")
        
        # Iterate through all dimensions
        for p in range(positions):
            for t in range(timepoints):
                for c in range(channels):
                    for z in range(z_slices):
                        # Read and write each image
                        img = reader_obj.read_image(position=p, time=t, channel=c, z=z)
                        
                        # Get image metadata if available
                        image_metadata = reader_obj.get_image_metadata(position=p, time=t, channel=c, z=z)

                        if verbose:
                            print(f"Image metadata for p{p} t{t} c{c} z{z}: {image_metadata}")
                        
                        # Write image with full coordinates and metadata
                        my_dataset.put_image(
                            image=img, 
                            position=p,
                            time=t, 
                            channel=c, 
                            z=z,
                            image_metadata=image_metadata
                        )
                        
                        # Free memory by removing reference to image
                        del img
                        
                        # Update progress bar
                        progress_bar.update(1)
        
        # Close progress bar
        progress_bar.close()
        
        print(f"Successfully processed: {dataset_name}")
        return True
    
    except Exception as e:
        print(f"Error processing {src_path}: {str(e)}")
        return False
    
    finally:
        # Ensure proper cleanup regardless of success or failure
        if my_dataset is not None:
            try:
                my_dataset.close()
            except Exception as e:
                print(f"Warning: Error closing dataset writer: {str(e)}")
                
        if reader_obj is not None:
            try:
                reader_obj.close()
            except Exception as e:
                print(f"Warning: Error closing dataset reader: {str(e)}")
        
        # Force garbage collection
        gc.collect()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="NDTIFF Dataset Renamer Using Direct ndstorage API")
    parser.add_argument("--src_folder", required=True, help="Source folder containing NDTIFF datasets or parent folder with dataset subfolders")
    parser.add_argument("--dst_folder", required=True, help="Destination folder where renamed datasets will be placed")
    parser.add_argument("--new_name", help="New name for all datasets (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    
    args = parser.parse_args()
    
    src_path = Path(args.src_folder)
    dst_path = Path(args.dst_folder)
    
    # Ensure destination folder exists
    dst_path.mkdir(parents=True, exist_ok=True)
    
    # Check if source is a single dataset or a parent folder with multiple datasets
    if is_tiff_dataset(src_path):
        # Process as a single dataset
        if args.verbose:
            print(f"Processing single dataset: {src_path}")
            
        process_dataset(
            src_path=src_path,
            dst_path=dst_path,
            dataset_name=args.new_name,
            verbose=args.verbose
        )
    else:
        # Process as a parent folder with dataset subfolders
        if args.verbose:
            print(f"Processing parent folder with multiple datasets: {src_path}")
        
        # Find all subfolders that contain TIFF files
        dataset_folders = []
        for subfolder in src_path.iterdir():
            if subfolder.is_dir() and is_tiff_dataset(subfolder):
                dataset_folders.append(subfolder)
        
        if not dataset_folders:
            print(f"No TIFF datasets found in {src_path} or its subfolders.")
            return
        
        print(f"Found {len(dataset_folders)} TIFF datasets to process.")
        
        # Process each dataset subfolder
        successful = 0
        for i, dataset_folder in enumerate(dataset_folders):
            print(f"\nProcessing folder {i+1}/{len(dataset_folders)}: {dataset_folder.name}")
            
            # If new_name is provided, we'll use it as a prefix and add the subfolder name
            if args.new_name:
                name = f"{args.new_name}_{clean_name(dataset_folder.name)}"
            else:
                name = clean_name(dataset_folder.name)
                
            if process_dataset(
                src_path=dataset_folder,
                dst_path=dst_path,
                dataset_name=name,
                verbose=args.verbose
            ):
                successful += 1
            
            print(f"Completed {i+1}/{len(dataset_folders)} folders")
            
            # Force garbage collection between processing datasets
            gc.collect()
        
        print(f"\nProcessing complete. Successfully processed {successful}/{len(dataset_folders)} datasets.")

if __name__ == "__main__":
    main()