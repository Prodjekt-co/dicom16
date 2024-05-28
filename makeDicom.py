import os

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def combine_dicoms(dicom_files, output_path):
    # Read the first file to get the metadata
    ds = pydicom.dcmread(dicom_files[0])
    
    # Initialize a list to hold the pixel data
    pixel_arrays = []

    # Find the maximum dimensions
    max_shape = (0, 0)
    for dicom_file in dicom_files:
        dicom = pydicom.dcmread(dicom_file)
        max_shape = (
            max(max_shape[0], dicom.pixel_array.shape[0]),
            max(max_shape[1], dicom.pixel_array.shape[1])
        )

    # Loop through the DICOM files and collect pixel data
    for dicom_file in dicom_files:
        dicom = pydicom.dcmread(dicom_file)
        pixel_array = dicom.pixel_array

        # Pad the pixel array to the maximum dimensions
        padded_array = np.zeros(max_shape, dtype=pixel_array.dtype)
        padded_array[:pixel_array.shape[0], :pixel_array.shape[1]] = pixel_array

        pixel_arrays.append(padded_array)
    
    # Stack pixel arrays along a new dimension to create a 3D array
    combined_pixel_array = np.stack(pixel_arrays, axis=0)
    
    # Update the original dataset to create a multi-frame DICOM
    ds.PixelData = combined_pixel_array.tobytes()
    ds.NumberOfFrames = combined_pixel_array.shape[0]
    
    # Update relevant metadata
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = generate_uid()
    ds.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    # Create a new FileDataset instance (derived class of Dataset)
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    # Create FileDataset object with file_meta
    file_ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Copy the main dataset's attributes to the new FileDataset
    for elem in ds:
        if elem.tag.group != 0x0002:  # File meta information is already in file_meta
            file_ds.add(elem)

    # Save the new combined DICOM file
    file_ds.save_as(output_path)
    print(f"Combined DICOM file saved to {output_path}")

if __name__ == "__main__":
    # Directory containing DICOM files to combine
    dicom_dir = "dicom_files"
    dicom_files = [os.path.join(dicom_dir, f) for f in os.listdir(dicom_dir) if f.endswith('.dcm')]
    
    # Output path for the combined DICOM file
    output_path = "source/combined.dcm"
    
    combine_dicoms(dicom_files, output_path)