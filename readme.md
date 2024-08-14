# Medical Image Processing and Analysis

This project contains a set of Python scripts for processing, compressing, and analyzing medical images, with a focus on DICOM (Digital Imaging and Communications in Medicine) files. The scripts utilize various compression techniques, including AVIF and JPEG2000, and provide tools for comparing the quality and efficiency of these methods.

## Scripts

1. **dicom-analyze.py**: A comprehensive image comparison tool that analyzes and compares different compression methods (AVIF and JPEG2000) for medical imagery.

2. **dicom8-8.py**: Processes DICOM images by splitting them into 8-bit high and low components, compressing them using lossy AVIF, and then reconstructing the images.

3. **dicom16-jp2k.py**: Converts DICOM images to JPEG2000 format, processes them, and provides analysis on the compression efficiency and image quality.

4. **dicom16.py**: Similar to dicom8-8.py, but uses lossless AVIF compression for the 8-bit components of 16-bit DICOM images.

## Features

- DICOM file processing and extraction
- Image compression using AVIF and JPEG2000
- Image quality assessment using SSIM (Structural Similarity Index)
- Detailed logging and reporting
- Visualization of results (histograms, comparison plots)

## Requirements

- Python 3.x
- Libraries: numpy, pillow, pydicom, scikit-image, matplotlib, glymur

You can install the required libraries using pip:

```
pip install numpy pillow pydicom scikit-image matplotlib glymur pillow-avif
```

Note: You may need to install additional system libraries for JPEG2000 support.

## Usage

1. Place your DICOM files in the `source` directory.

2. Run the desired script:

   ```
   python dicom-analyze.py
   ```
   or
   ```
   python dicom8-8.py
   ```
   or
   ```
   python dicom16-jp2k.py
   ```
   or
   ```
   python dicom16.py
   ```

3. Check the output in the respective directories:
   - `output` for dicom-analyze.py
   - `reconstruct-8-8` for dicom8-8.py
   - `reconstruct-jp2` for dicom16-jp2k.py
   - `reconstruct` for dicom16.py

4. Review the generated CSV reports and image files for analysis results.

## Output

Each script generates:
- Compressed image files
- Reconstructed image files
- CSV reports with metrics such as file sizes, compression ratios, and SSIM values
- Log files with detailed processing information
- Visualization plots (for some scripts)

## Notes

- These scripts are designed for research and analysis purposes. Always validate results before using in a clinical setting.
- Processing large DICOM files or datasets may require significant computational resources and time.
- Ensure you have necessary permissions to process and store medical imaging data.

## Contributing

Contributions to improve the scripts or extend functionality are welcome. Please submit pull requests or open issues for any bugs or feature requests.

## License

[Specify your license here]