import csv
import json
import os
import time

import numpy as np
import pillow_avif  # Ensure AVIF support is added
import pydicom
from PIL import Image
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_voi_lut


def extract_images_from_dicom(dicom_path, output_dir):
    extracted_images = []
    try:
        # Read the DICOM file
        dicom_data = dcmread(dicom_path)
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Check photometric interpretation
        photometric_interpretation = dicom_data.PhotometricInterpretation
        if photometric_interpretation in ['MONOCHROME1', 'MONOCHROME2']:
            # Apply VOI LUT (if available)
            pixel_array = apply_voi_lut(dicom_data.pixel_array, dicom_data)
        else:
            pixel_array = dicom_data.pixel_array

        # Print pixel array shape and dtype for debugging
        print(f"Pixel array shape: {pixel_array.shape}, dtype: {pixel_array.dtype}")
        
        # Normalize pixel values to the range [0, 255] if 8-bit
        if pixel_array.dtype == np.uint8 and len(pixel_array.shape) == 4 and pixel_array.shape[3] == 3:
            pass  # Color image already in 8-bit format
        else:
            raise ValueError(f"Cannot handle this data type: {pixel_array.shape}, {pixel_array.dtype}")

        # Check if the DICOM is multi-frame
        if len(pixel_array.shape) == 4 and pixel_array.shape[-1] == 3:
            for i, frame in enumerate(pixel_array):
                output_image_path = os.path.join(output_dir, f'image_{i}.tif')
                Image.fromarray(frame).save(output_image_path, format='TIFF', compression='none')
                extracted_images.append(output_image_path)
        else:
            output_image_path = os.path.join(output_dir, 'image_0.tif')
            Image.fromarray(pixel_array).save(output_image_path, format='TIFF', compression='none')
            extracted_images.append(output_image_path)
        
        return extracted_images
    except Exception as e:
        print(f"An error occurred while extracting images: {e}")
        return None

def split_and_save_image(image_path, output_dir):
    try:
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Load the image
        img = Image.open(image_path)
        img_array = np.array(img)

        if img_array.ndim == 3:  # Color image
            channels = img_array.shape[2]
            high_bits_paths = []
            low_bits_paths = []
            metadata = {"original_image": image_path, "channels": []}

            for channel in range(channels):
                channel_data = img_array[:, :, channel]
                high_bits = (channel_data >> 4).astype(np.uint8)
                low_bits = (channel_data & 0x0F).astype(np.uint8)

                high_bits_image_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_high_bits_channel_{channel}.avif')
                low_bits_image_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_low_bits_channel_{channel}.avif')

                high_bits_img = Image.fromarray(high_bits)
                low_bits_img = Image.fromarray(low_bits)

                high_bits_img.save(high_bits_image_path, format='AVIF', quality=100, lossless=True)
                low_bits_img.save(low_bits_image_path, format='AVIF', quality=100, lossless=True)

                high_bits_paths.append(high_bits_image_path)
                low_bits_paths.append(low_bits_image_path)
                metadata["channels"].append({
                    "high_bits_file": high_bits_image_path,
                    "low_bits_file": low_bits_image_path
                })
        else:
            raise ValueError("Only 8-bit color images are supported.")

        # Write the metadata to a JSON file
        metadata_file_path = os.path.join(output_dir, f'{os.path.basename(image_path).split(".")[0]}_image_metadata.json')
        with open(metadata_file_path, 'w') as json_file:
            json.dump(metadata, json_file, indent=4)

        return high_bits_paths, low_bits_paths, metadata_file_path
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None

def reconstruct_image(high_bits_paths, low_bits_paths, output_path):
    try:
        if len(high_bits_paths) > 1:  # Color image
            channels = len(high_bits_paths)
            reconstructed_channels = []

            for channel in range(channels):
                high_bits = Image.open(high_bits_paths[channel])
                low_bits = Image.open(low_bits_paths[channel])

                high_bits = high_bits.convert('L')
                low_bits = low_bits.convert('L')

                high_bits_array = np.array(high_bits).astype(np.uint8) << 4
                low_bits_array = np.array(low_bits).astype(np.uint8)

                reconstructed_channel = high_bits_array | low_bits_array
                reconstructed_channels.append(reconstructed_channel)

            reconstructed_image_array = np.stack(reconstructed_channels, axis=-1)
            mode = 'RGB'
        else:
            raise ValueError("Only 8-bit color images are supported.")

        reconstructed_image = Image.fromarray(reconstructed_image_array, mode=mode)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the reconstructed image
        reconstructed_image.save(output_path, format='TIFF', compression='none')
        return output_path
    except Exception as e:
        print(f"An error occurred during reconstruction: {e}")
        return None

def main():
    source_dir = 'source'
    dicom_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.dcm')]
    if not dicom_files:
        print("No DICOM files found in the source directory.")
        return
    
    dicom_path = os.path.join(source_dir, dicom_files[0])
    output_dir = 'reconstruct'
    extracted_output_dir = os.path.join(output_dir, 'extracted')
    split_output_dir = os.path.join(output_dir, 'split')
    reconstructed_output_dir = os.path.join(output_dir, 'reconstructed')

    # Extract images from DICOM file
    extracted_images = extract_images_from_dicom(dicom_path, extracted_output_dir)
    if extracted_images is None:
        print("No images extracted. Exiting.")
        return

    report_data = []

    for image_path in extracted_images:
        # Get original image size
        original_size = os.path.getsize(image_path)
        start_time = time.time()

        high_bits_paths, low_bits_paths, metadata_path = split_and_save_image(image_path, split_output_dir)
        if high_bits_paths is None or low_bits_paths is None:
            print(f"Skipping image due to split error: {image_path}")
            continue

        split_time = time.time() - start_time
        combined_split_size = sum(os.path.getsize(path) for path in high_bits_paths) + sum(os.path.getsize(path) for path in low_bits_paths)

        # Reconstruct image
        start_time = time.time()
        reconstructed_image_path = reconstruct_image(high_bits_paths, low_bits_paths, os.path.join(reconstructed_output_dir, f'reconstructed_{os.path.basename(image_path)}'))
        if reconstructed_image_path is None:
            print(f"Skipping image due to reconstruction error: {image_path}")
            continue

        reconstruct_time = time.time() - start_time
        reconstructed_size = os.path.getsize(reconstructed_image_path)

        # Calculate percentage reduction
        if original_size > 0:
            percentage_reduction = ((original_size - combined_split_size) / float(original_size)) * 100
        else:
            percentage_reduction = 0.0

        print(f"Original size: {original_size}, Combined split size: {combined_split_size}, Percentage reduction: {percentage_reduction}")

        report_data.append({
            'original_image': image_path,
            'original_size': original_size,
            'split_time': split_time,
            'combined_split_size': combined_split_size,
            'reconstruct_time': reconstruct_time,
            'reconstructed_size': reconstructed_size,
            'percentage_reduction': percentage_reduction
        })

    # Write report to CSV
    report_csv_path = os.path.join(output_dir, 'report.csv')
    with open(report_csv_path, 'w', newline='') as csvfile:
        fieldnames = ['original_image', 'original_size', 'split_time', 'combined_split_size', 'reconstruct_time', 'reconstructed_size', 'percentage_reduction']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in report_data:
            writer.writerow(row)

    print(f"Report saved as: {report_csv_path}")

if __name__ == '__main__':
    main()