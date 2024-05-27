# dicom16
DICOM16 project is an attempt to losslessly compress 16bit DICOM images for storage, and reliably reassmble those images on demond. The purpose of these scripts are to 
1. Extract uncompressed 16bit images from a DICOM study
2. Split the 16bit images into high and low bit images and save them as 8bit AVIF uncompressed files
3. Reconstruct the original DICOM images and measure for any differences in quality or size
