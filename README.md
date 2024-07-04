# dicom16
DICOM16 project is an attempt to losslessly compress 16bit DICOM images for storage, and reliably reassmble those images on demond. The purpose of these scripts are to 
1. Extract uncompressed 16bit images from a DICOM study
2. Split the 16bit images into high and low bit images and save them as 8bit AVIF uncompressed files
3. Reconstruct the original DICOM images and measure for any differences in quality or size

In order to use the script you must have a .DCM file in the "source" folder. If you do not have a multi-image DCM you can use the script "makeDicom.py" to combine individual .DCM files into a multi-image DCM. 

With the source in place, run the "dicom16.py" script which will perform all operations and output into the "reconstrcut" folder.

# DICOM Processing Script Breakdown

## Required Directories

1. `source`: This directory should contain your DICOM (.dcm) files.
2. `reconstruct`: This is the main output directory, which will contain three subdirectories:
   - `extracted`: For storing extracted images from DICOM files
   - `split`: For storing split high and low bit images
   - `reconstructed`: For storing reconstructed images

## Required Elements

1. Python Libraries:
   - csv
   - json
   - os
   - time
   - numpy
   - pillow_avif
   - pydicom
   - PIL (Python Imaging Library)

2. DICOM Files:
   - At least one .dcm file in the `source` directory

## Script Structure

1. **Import Statements**: The script starts by importing necessary libraries.

2. **Functions**:
   a. `extract_images_from_dicom(dicom_path, output_dir)`:
      - Extracts images from a DICOM file
      - Saves them as .tif files in the `extracted` directory
   
   b. `split_and_save_image(image_path, output_dir)`:
      - Splits a 16-bit image into high and low 8-bit components
      - Saves them as lossless AVIF files in the `split` directory
      - Creates a metadata JSON file
   
   c. `reconstruct_image(high_bits_path, low_bits_path, output_path)`:
      - Reconstructs the original 16-bit image from high and low bit components
      - Saves the reconstructed image in the `reconstructed` directory

   d. `main()`:
      - Orchestrates the entire process
      - Generates a report CSV file with processing statistics

3. **Main Execution**:
   - The script runs the `main()` function when executed directly

## Process Flow

1. Find DICOM files in the `source` directory
2. Extract images from the DICOM file
3. For each extracted image:
   - Split into high and low bit components
   - Save split images and metadata
   - Reconstruct the image
   - Calculate and store processing statistics
4. Generate a CSV report with all processing statistics

## Output

- Extracted .tif images in the `extracted` directory
- Split high and low bit AVIF images in the `split` directory
- Reconstructed images in the `reconstructed` directory
- A `report.csv` file in the `reconstruct` directory with processing statistics

This script is designed to process DICOM files, split the extracted images into high and low bit components for potential compression benefits, and then reconstruct the images. It also provides performance metrics for the process.
