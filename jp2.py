from PIL import Image
import numpy as np
import glymur

# Load the image (replace with your image file)
input_image_path = '/Users/dames/PycharmProjects/dicom16/reconstruct/extracted/image_0.tif'
output_image_path = 'output_image.jp2'

# Open the image using PIL
image = Image.open(input_image_path)

# Ensure the image is in 16-bit mode
if image.mode != 'I;16':
    raise ValueError("The image is not in 16-bit mode. Please provide a 16-bit image.")

# Convert the image to a numpy array
image_array = np.array(image)

# Convert image array to unsigned 16-bit integers if needed
if image_array.dtype != np.uint16:
    image_array = image_array.astype(np.uint16)

# Save the image as 16-bit lossless JPEG 2000 using glymur
jp2 = glymur.Jp2k(output_image_path, data=image_array, cratios=[1])

# Re-open the saved JPEG 2000 file and inspect the pixel array
jp2_file = glymur.Jp2k(output_image_path)
decoded_image = jp2_file[:]

# Check the bit depth of the decoded image by inspecting the dtype
print(f"Decoded image shape: {decoded_image.shape}")
print(f"Decoded image data type: {decoded_image.dtype}")
print(f"Image saved as {output_image_path} in 16-bit lossless JPEG 2000 format.")