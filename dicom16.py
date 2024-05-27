import csv
import json
import os
import time

import numpy as np
import pillow_avif  # Ensure AVIF support is added
import rawpy
from PIL import Image
from pydicom import dcmread


def extract_images_from_dicom(dicom_path, output_dir):
    extracted_images = []
    try:
        # Read the DICOM file
        dicom_data = dcmread(dicom_path)
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Check if pixel data handler is present
        if 'PixelData' not in dicom_data:
            print(f"No pixel data found in {dicom_path}")
            return None

        # Get pixel data
        pixel_array = dicom_data.pixel_array
        print(f"Pixel array shape: {pixel_array.shape}, dtype: {pixel_array.dtype}")

        # Loop through each frame in the DICOM file (if multi-frame)
        for i, frame in enumerate(pixel_array):
            output_image_path = os.path.join(output_dir, f'image_{i}.tif')
            Image.fromarray(frame).save(output_image_path)
            extracted_images.append(output_image_path)
        
        return extracted_images
    except Exception as e:
        print(f"An error occurred while extracting images: {e}")
        return None

def split_and_save_image(image_path, output_dir):
    try:
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Load the 16-bit image
        img = Image.open(image_path)
        img_array = np.array(img)

        # Split into higher and lower 8-bit images
        high_bits = (img_array >> 8).astype(np.uint8)
        low_bits = (img_array & 0xFF).astype(np.uint8)

        # Save the high and low bit images as lossless AVIF
        high_bits_image_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_high_bits.avif')
        low_bits_image_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_low_bits.avif')

        high_bits_img = Image.fromarray(high_bits)
        low_bits_img = Image.fromarray(low_bits)

        high_bits_img.save(high_bits_image_path, format='avif', quality=100, lossless=True)
        low_bits_img.save(low_bits_image_path, format='avif', quality=100, lossless=True)

        # Define the metadata
        metadata = {
            "original_image": image_path,
            "high_bits_file": high_bits_image_path,
            "low_bits_file": low_bits_image_path
        }

        # Write the metadata to a JSON file
        metadata_file_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_image_metadata.json')
        with open(metadata_file_path, 'w') as json_file:
            json.dump(metadata, json_file, indent=4)

        return high_bits_image_path, low_bits_image_path, metadata_file_path
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None

def reconstruct_image(high_bits_path, low_bits_path, output_path):
    try:
        # Load the high and low bit images
        high_bits = Image.open(high_bits_path)
        low_bits = Image.open(low_bits_path)

        # Ensure the images are in the correct mode
        high_bits = high_bits.convert('L')
        low_bits = low_bits.convert('L')

        # Convert images to numpy arrays and shift/combine bits
        high_bits_array = np.array(high_bits).astype(np.uint16) << 8
        low_bits_array = np.array(low_bits).astype(np.uint16)

        # Combine to reconstruct the 16-bit image
        reconstructed_image_array = high_bits_array | low_bits_array
        reconstructed_image = Image.fromarray(reconstructed_image_array, mode='I;16')

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the reconstructed image
        reconstructed_image.save(output_path)
        return output_path
    except Exception as e:
        print(f"An error occurred during reconstruction: {e}")
        return None

def process_dng(image_path, output_dir):
    try:
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Read the DNG file using rawpy
        with rawpy.imread(image_path) as raw:
            img_array = raw.postprocess(output_bps=16)

        # Convert the image array to an Image object
        img = Image.fromarray(img_array)

        # Save the image as a 16-bit TIFF
        tiff_image_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}.tif')
        img.save(tiff_image_path)

        return tiff_image_path
    except Exception as e:
        print(f"An error occurred while processing DNG: {e}")
        return None

def main():
    source_dir = 'source'
    dicom_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.dcm')]
    dng_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.dng')]
    
    if not dicom_files and not dng_files:
        print("No DICOM or DNG files found in the source directory.")
        return
    
    output_dir = 'reconstruct'
    extracted_output_dir = os.path.join(output_dir, 'extracted')
    split_output_dir = os.path.join(output_dir, 'split')
    reconstructed_output_dir = os.path.join(output_dir, 'reconstructed')

    report_data = []

    # Process DICOM files
    for dicom_file in dicom_files:
        dicom_path = os.path.join(source_dir, dicom_file)

        # Extract images from DICOM file
        extracted_images = extract_images_from_dicom(dicom_path, extracted_output_dir)
        if extracted_images is None:
            print("No images extracted. Skipping.")
            continue

        for image_path in extracted_images:
            # Process each extracted image
            process_image(image_path, split_output_dir, reconstructed_output_dir, report_data)

    # Process DNG files
    for dng_file in dng_files:
        dng_path = os.path.join(source_dir, dng_file)

        # Convert DNG to TIFF
        tiff_image_path = process_dng(dng_path, extracted_output_dir)
        if tiff_image_path is None:
            print(f"Skipping DNG due to processing error: {dng_path}")
            continue

        # Process the converted TIFF image
        process_image(tiff_image_path, split_output_dir, reconstructed_output_dir, report_data)

    # Write report to CSV
    report_csv_path = os.path.join(output_dir, 'report.csv')
    with open(report_csv_path, 'w', newline='') as csvfile:
        fieldnames = ['original_image', 'original_size', 'split_time', 'combined_split_size', 'reconstruct_time', 'reconstructed_size', 'percentage_reduction']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in report_data:
            writer.writerow(row)

    print(f"Report saved as: {report_csv_path}")

def process_image(image_path, split_output_dir, reconstructed_output_dir, report_data):
    # Get original image size
    original_size = os.path.getsize(image_path)
    start_time = time.time()

    # Split and save image
    high_bits_path, low_bits_path, metadata_path = split_and_save_image(image_path, split_output_dir)
    if high_bits_path is None or low_bits_path is None:
        print(f"Skipping image due to split error: {image_path}")
        return

    split_time = time.time() - start_time
    combined_split_size = os.path.getsize(high_bits_path) + os.path.getsize(low_bits_path)

    # Reconstruct image
    start_time = time.time()
    reconstructed_image_path = reconstruct_image(high_bits_path, low_bits_path, os.path.join(reconstructed_output_dir, f'reconstructed_{os.path.basename(image_path)}'))
    if reconstructed_image_path is None:
        print(f"Skipping image due to reconstruction error: {image_path}")
        return

    reconstruct_time = time.time() - start_time
    reconstructed_size = os.path.getsize(reconstructed_image_path)

    # Calculate percentage reduction
    if original_size > 0:
        percentage_reduction = ((original_size - reconstructed_size) / float(original_size)) * 100
    else:
        percentage_reduction = 0.0

    print(f"Original size: {original_size}, Reconstructed size: {reconstructed_size}, Percentage reduction: {percentage_reduction}")

    report_data.append({
        'original_image': image_path,
        'original_size': original_size,
        'split_time': split_time,
        'combined_split_size': combined_split_size,
        'reconstruct_time': reconstruct_time,
        'reconstructed_size': reconstructed_size,
        'percentage_reduction': percentage_reduction
    })

if __name__ == '__main__':
    main()