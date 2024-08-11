import csv
import json
import os
import time

import numpy as np
import pydicom
from glymur import Jp2k
from PIL import Image
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_voi_lut
from skimage.metrics import structural_similarity as ssim


def dicom_to_jp2(dicom_path, output_dir):
    try:
        dicom_data = dcmread(dicom_path)
        os.makedirs(output_dir, exist_ok=True)
        pixel_array = apply_voi_lut(dicom_data.pixel_array, dicom_data)
        pixel_array = ((pixel_array - np.min(pixel_array)) / np.max(pixel_array) * 65535.0).astype(np.uint16)

        base_name = os.path.splitext(os.path.basename(dicom_path))[0]
        jp2_files = []
        metadata_files = []
        original_arrays = []

        if len(pixel_array.shape) == 3:
            for i, frame in enumerate(pixel_array):
                jp2_path, metadata_path = process_frame(frame, output_dir, f'{base_name}_frame_{i}')
                jp2_files.append(jp2_path)
                metadata_files.append(metadata_path)
                original_arrays.append(frame)
        else:
            jp2_path, metadata_path = process_frame(pixel_array, output_dir, base_name)
            jp2_files.append(jp2_path)
            metadata_files.append(metadata_path)
            original_arrays.append(pixel_array)

        return jp2_files, metadata_files, original_arrays
    except Exception as e:
        print(f"An error occurred while processing DICOM: {e}")
        return None, None, None


def process_frame(frame, output_dir, base_name):
    height, width = frame.shape
    print(f"Processing image with dimensions: {width}x{height}")

    # Create JP2 file
    jp2_path = os.path.join(output_dir, f'{base_name}.jp2')
    Jp2k(jp2_path, data=frame)

    # Define the metadata
    metadata = {
        "original_image": f"{base_name}.dcm",
        "width": width,
        "height": height
    }

    # Save metadata to a separate JSON file
    metadata_path = os.path.join(output_dir, f'{base_name}_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    return jp2_path, metadata_path


def reconstruct_image(jp2_path, metadata_path, output_path):
    try:
        # Read metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        print(f"Reconstructing image with dimensions: {metadata['width']}x{metadata['height']}")

        # Read and reconstruct image
        jp2 = Jp2k(jp2_path)
        reconstructed_array = jp2[:]

        print(f"Reconstructed array shape: {reconstructed_array.shape}")

        reconstructed_image = Image.fromarray(reconstructed_array, mode='I;16')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        reconstructed_image.save(output_path)

        return output_path, reconstructed_array
    except Exception as e:
        print(f"An error occurred during reconstruction: {e}")
        return None, None


def calculate_ssim_in_memory(original_array, reconstructed_array):
    try:
        return ssim(original_array, reconstructed_array, data_range=original_array.max() - original_array.min())
    except Exception as e:
        print(f"An error occurred during SSIM calculation: {e}")
        return None


def main():
    source_dir = 'source'
    dicom_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.dcm')]
    if not dicom_files:
        print("No DICOM files found in the source directory.")
        return

    dicom_path = os.path.join(source_dir, dicom_files[0])
    output_dir = 'reconstruct-jp2'
    jp2_output_dir = os.path.join(output_dir, 'jp2')
    reconstructed_output_dir = os.path.join(output_dir, 'reconstructed')

    jp2_files, metadata_files, original_arrays = dicom_to_jp2(dicom_path, jp2_output_dir)
    if jp2_files is None or len(jp2_files) == 0:
        print("No JP2 files created. Exiting.")
        return

    report_data = []

    for jp2_path, metadata_path, original_array in zip(jp2_files, metadata_files, original_arrays):
        print(f"Processing JP2 file: {jp2_path}")

        jp2_file_size = os.path.getsize(jp2_path)
        metadata_file_size = os.path.getsize(metadata_path)
        total_size = jp2_file_size + metadata_file_size

        start_time = time.time()
        base_name = os.path.splitext(os.path.basename(jp2_path))[0]
        reconstructed_image_path, reconstructed_array = reconstruct_image(jp2_path, metadata_path,
                                                                          os.path.join(reconstructed_output_dir,
                                                                                       f'reconstructed_{base_name}.tif'))
        if reconstructed_image_path is None:
            print(f"Skipping JP2 file due to reconstruction error: {jp2_path}")
            continue

        reconstruct_time = time.time() - start_time
        reconstructed_size = os.path.getsize(reconstructed_image_path)

        ssim_value = calculate_ssim_in_memory(original_array, reconstructed_array)

        original_size = original_array.nbytes
        percentage_reduction = ((original_size - total_size) / float(original_size)) * 100

        print(
            f"JP2 file size: {jp2_file_size}, Metadata size: {metadata_file_size}, Total size: {total_size}, Reconstructed size: {reconstructed_size}, SSIM: {ssim_value}, Reduction: {percentage_reduction:.2f}%")

        report_data.append({
            'jp2_file': jp2_path,
            'metadata_file': metadata_path,
            'original_size': original_size,
            'jp2_file_size': jp2_file_size,
            'metadata_file_size': metadata_file_size,
            'total_size': total_size,
            'reconstruct_time': reconstruct_time,
            'reconstructed_size': reconstructed_size,
            'ssim': ssim_value,
            'percentage_reduction': percentage_reduction
        })

    if report_data:
        report_csv_path = os.path.join(output_dir, 'report.csv')
        with open(report_csv_path, 'w', newline='') as csvfile:
            fieldnames = ['jp2_file', 'metadata_file', 'original_size', 'jp2_file_size', 'metadata_file_size',
                          'total_size', 'reconstruct_time', 'reconstructed_size', 'ssim', 'percentage_reduction']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in report_data:
                writer.writerow(row)
        print(f"Report saved as: {report_csv_path}")
    else:
        print("No data to write to report.")


if __name__ == '__main__':
    main()
