import os
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
import matplotlib.pyplot as plt
import hashlib
import csv
import glob
import logging
import subprocess
from datetime import datetime
import subprocess


def set_imagemagick_limits():
    subprocess.run(["convert", "-limit", "memory", "8GB", "-limit", "map", "16GB", "+version"])


set_imagemagick_limits()


# Set up logging
def setup_logging(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(output_dir, f'image_comparison_log_{timestamp}.txt')

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler(log_filename),
                            logging.StreamHandler()
                        ])
    logging.info(f"Logging to file: {log_filename}")


def load_image(file_path):
    return np.array(Image.open(file_path))


def calculate_ssim(img1, img2):
    return ssim(img1, img2, data_range=img1.max() - img1.min())


def calculate_psnr(img1, img2):
    return psnr(img1, img2, data_range=img1.max() - img1.min())


def calculate_mse(img1, img2):
    return np.mean((img1 - img2) ** 2)


def compare_histograms(img1, img2):
    hist1, _ = np.histogram(img1.flatten(), bins=2 ** 16, range=(0, 2 ** 16 - 1))
    hist2, _ = np.histogram(img2.flatten(), bins=2 ** 16, range=(0, 2 ** 16 - 1))
    return np.allclose(hist1, hist2)


def calculate_file_hash(file_path):
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
    return file_hash.hexdigest()


def pixel_by_pixel_comparison(img1, img2):
    return np.allclose(img1, img2)


def plot_histogram(image, title, output_path):
    plt.figure(figsize=(12, 6))

    # Calculate histogram
    hist, bin_edges = np.histogram(image.flatten(), bins=1000, range=(0, 65535))

    # Add a small constant to avoid log(0)
    hist = hist + 1

    # Plot the histogram with log scale
    plt.bar(bin_edges[:-1], hist, width=np.diff(bin_edges), align="edge", log=True)

    plt.title(title)
    plt.xlabel('Pixel Intensity')
    plt.ylabel('Log Frequency')
    plt.yscale('log')
    plt.xlim(0, 65535)
    plt.grid(True, which="both", ls="-", alpha=0.2)

    # Optional: Add cumulative distribution function
    cdf = np.cumsum(hist)
    cdf_normalized = cdf / cdf[-1]
    plt.plot(bin_edges[:-1], cdf_normalized, 'r-', linewidth=1.5, label='CDF')

    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_histograms(source_img, avif_img, jpeg2000_img, output_dir, filename):
    plot_histogram(source_img, f'Histogram of Source Image: {filename}',
                   os.path.join(output_dir, f'{filename}_source_histogram.png'))
    plot_histogram(avif_img, f'Histogram of AVIF Reconstructed Image: {filename}',
                   os.path.join(output_dir, f'{filename}_avif_histogram.png'))
    plot_histogram(jpeg2000_img, f'Histogram of JPEG2000 Reconstructed Image: {filename}',
                   os.path.join(output_dir, f'{filename}_jpeg2000_histogram.png'))


def imagemagick_compare(source_path, recon_path, output_dir, filename):
    output_path = os.path.join(output_dir, f"{filename}_difference.png")
    try:
        result = subprocess.run(
            ["compare", "-metric", "AE", source_path, recon_path, output_path],
            capture_output=True,
            text=True,
            check=True
        )
        diff_pixels = int(result.stderr)
        return diff_pixels, output_path
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # ImageMagick returns 1 if images are different
            diff_pixels = int(e.stderr)
            return diff_pixels, output_path
        else:
            logging.error(f"ImageMagick error: {e.stderr}")
            return None, None
    except Exception as e:
        logging.error(f"Error in ImageMagick comparison: {str(e)}")
        return None, None


def run_tests(source_path, avif_recon_path, jpeg2000_recon_path, output_dir):
    results = {'Filename': os.path.basename(source_path)}
    source_img = load_image(source_path)
    source_hash = calculate_file_hash(source_path)
    results['Source_Hash'] = source_hash

    avif_img = None
    jpeg2000_img = None

    for format_name, recon_path in [('AVIF', avif_recon_path), ('JPEG2000', jpeg2000_recon_path)]:
        if os.path.exists(recon_path):
            recon_img = load_image(recon_path)
            if format_name == 'AVIF':
                avif_img = recon_img
            else:
                jpeg2000_img = recon_img

            recon_hash = calculate_file_hash(recon_path)
            results[f'{format_name}_Hash'] = recon_hash
            results[f'{format_name}_Hash_Match'] = source_hash == recon_hash

            if source_img.shape != recon_img.shape:
                logging.warning(
                    f"{format_name} image shape mismatch for {os.path.basename(source_path)}. Source: {source_img.shape}, {format_name}: {recon_img.shape}")
                continue

            results[f'{format_name}_SSIM'] = calculate_ssim(source_img, recon_img)
            results[f'{format_name}_PSNR'] = calculate_psnr(source_img, recon_img)
            results[f'{format_name}_MSE'] = calculate_mse(source_img, recon_img)
            results[f'{format_name}_Histogram_Match'] = compare_histograms(source_img, recon_img)
            results[f'{format_name}_Pixel_by_Pixel'] = pixel_by_pixel_comparison(source_img, recon_img)

            # Add ImageMagick comparison
            diff_pixels, diff_image_path = imagemagick_compare(source_path, recon_path, output_dir,
                                                               f"{os.path.splitext(results['Filename'])[0]}_{format_name}")
            if diff_pixels is not None and diff_image_path is not None:
                results[f'{format_name}_ImageMagick_Diff_Pixels'] = diff_pixels
                results[f'{format_name}_ImageMagick_Diff_Image'] = diff_image_path
            else:
                logging.warning(f"ImageMagick comparison failed for {format_name}")

    return results, source_img, avif_img, jpeg2000_img


def analyze_hash_mismatch(results):
    filename = results['Filename']
    source_hash = results['Source_Hash']

    for format_name in ['AVIF', 'JPEG2000']:
        if f'{format_name}_Hash' in results:
            recon_hash = results[f'{format_name}_Hash']
            logging.info(f"Analyzing hash for {filename} - {format_name}")
            logging.info(f"Source hash: {source_hash}")
            logging.info(f"{format_name} hash: {recon_hash}")

            if not results[f'{format_name}_Hash_Match']:
                logging.warning(f"Hash mismatch detected for {filename} - {format_name}")

                # Compare the hashes byte by byte
                mismatch_positions = []
                mismatch_count = 0
                for i, (s, r) in enumerate(zip(source_hash, recon_hash)):
                    if s != r:
                        mismatch_positions.append(i)
                        mismatch_count += 1
                        logging.debug(f"Mismatch at position {i}: Source '{s}' vs {format_name} '{r}'")

                # Calculate percentage of mismatched bytes
                mismatch_percentage = (mismatch_count / len(source_hash)) * 100

                # Calculate Hamming distance
                hamming_distance = sum(c1 != c2 for c1, c2 in zip(source_hash, recon_hash))

                logging.warning(f"Total mismatches: {mismatch_count}")
                logging.warning(f"Mismatch percentage: {mismatch_percentage:.2f}%")
                logging.warning(f"Hamming distance: {hamming_distance}")
                logging.warning(f"Mismatch positions: {mismatch_positions}")

                # Analyze the pattern of mismatches
                if mismatch_count > 0:
                    avg_gap = (mismatch_positions[-1] - mismatch_positions[0]) / (len(mismatch_positions) - 1) if len(
                        mismatch_positions) > 1 else 0
                    logging.warning(f"Average gap between mismatches: {avg_gap:.2f}")

                    # Check if mismatches are concentrated in specific regions
                    regions = [0] * 4  # Divide hash into 4 regions
                    region_size = len(source_hash) // 4
                    for pos in mismatch_positions:
                        regions[pos // region_size] += 1
                    logging.warning(f"Mismatch distribution across regions: {regions}")

                # Visualize the mismatches
                mismatch_visualization = ''.join(
                    ['X' if i in mismatch_positions else '.' for i in range(len(source_hash))])
                logging.warning(f"Mismatch visualization: {mismatch_visualization}")
            else:
                logging.info(f"Hashes match for {filename} - {format_name}")


def interpret_imagemagick_results(results):
    for format_name in ['AVIF', 'JPEG2000']:
        diff_pixels = results.get(f'{format_name}_ImageMagick_Diff_Pixels')
        if diff_pixels is not None:
            if diff_pixels == 0:
                logging.info(f"ImageMagick comparison for {format_name}: No pixel differences detected.")
            else:
                logging.warning(f"ImageMagick comparison for {format_name}: {diff_pixels} pixel differences detected.")
                logging.info(f"Difference image saved at: {results.get(f'{format_name}_ImageMagick_Diff_Image')}")
        else:
            logging.warning(f"ImageMagick comparison for {format_name} failed or was not performed.")


def log_file_sizes(source_path, recon_path):
    source_size = os.path.getsize(source_path)
    recon_size = os.path.getsize(recon_path)
    logging.info(f"Source file size: {source_size / (1024 * 1024):.2f} MB")
    logging.info(f"Reconstructed file size: {recon_size / (1024 * 1024):.2f} MB")


# Call this function in run_tests before imagemagick_compare

def save_results_to_csv(results, output_path):
    if not results:
        logging.warning("No results to save to CSV.")
        return

    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    logging.info(f"Results saved to: {output_path}")


def plot_results(results, output_dir):
    if not results:
        logging.warning("No results to plot.")
        return

    metrics = ['SSIM', 'PSNR', 'MSE']

    for metric in metrics:
        avif_values = [result.get(f'AVIF_{metric}', None) for result in results]
        jpeg2000_values = [result.get(f'JPEG2000_{metric}', None) for result in results]

        plt.figure(figsize=(10, 6))
        plt.scatter(range(len(results)), avif_values, label='AVIF')
        plt.scatter(range(len(results)), jpeg2000_values, label='JPEG2000')
        plt.xlabel('Image Index')
        plt.ylabel(metric)
        plt.title(f'{metric} Comparison: AVIF vs JPEG2000')
        plt.legend()
        plot_path = os.path.join(output_dir, f'{metric}_comparison.png')
        plt.savefig(plot_path)
        plt.close()
        logging.info(f"Plot saved to: {plot_path}")


def process_directory(source_dir, avif_dir, jpeg2000_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    results = []
    processed_count = 0
    skipped_count = 0
    error_count = 0

    logging.info(f"Searching for .tif files in source directory: {source_dir}")
    source_files = glob.glob(os.path.join(source_dir, '*.tif'))
    logging.info(f"Found {len(source_files)} .tif files in source directory")

    for source_path in source_files:
        filename = os.path.basename(source_path)
        name, _ = os.path.splitext(filename)

        avif_path = os.path.join(avif_dir, "reconstructed", f"{name}.tif")
        jpeg2000_path = os.path.join(jpeg2000_dir, "reconstructed", f"{name}.tif")

        logging.debug(f"Processing file: {filename}")
        logging.debug(f"Looking for AVIF reconstructed image: {avif_path}")
        logging.debug(f"Looking for JPEG2000 reconstructed image: {jpeg2000_path}")

        if os.path.exists(avif_path) and os.path.exists(jpeg2000_path):
            try:
                result, source_img, avif_img, jpeg2000_img = run_tests(source_path, avif_path, jpeg2000_path,
                                                                       output_dir)
                results.append(result)
                plot_histograms(source_img, avif_img, jpeg2000_img, output_dir, name)
                analyze_hash_mismatch(result)
                interpret_imagemagick_results(result)
                processed_count += 1
                logging.info(f"Processed: {filename}")
            except Exception as e:
                error_count += 1
                logging.error(f"Error processing {filename}: {str(e)}")
        elif os.path.exists(avif_path):
            logging.warning(f"Skipping {filename}: Missing JPEG2000 reconstructed image")
            skipped_count += 1
        elif os.path.exists(jpeg2000_path):
            logging.warning(f"Skipping {filename}: Missing AVIF reconstructed image")
            skipped_count += 1
        else:
            logging.warning(f"Skipping {filename}: Missing both reconstructed images")
            skipped_count += 1

    if results:
        csv_path = os.path.join(output_dir, 'comparison_results.csv')
        save_results_to_csv(results, csv_path)
        plot_results(results, output_dir)
    else:
        logging.warning("No results to save or plot.")

    logging.info(f"Processing complete. Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}")

    # Print contents of directories for debugging
    logging.debug("Contents of source directory:")
    for file in os.listdir(source_dir):
        if file != '.DS_Store':
            logging.debug(f"  {file}")
    logging.debug("Contents of AVIF directory:")
    for root, dirs, files in os.walk(avif_dir):
        for file in files:
            if file != '.DS_Store':
                logging.debug(f"  {os.path.join(root, file)}")
    logging.debug("Contents of JPEG2000 directory:")
    for root, dirs, files in os.walk(jpeg2000_dir):
        for file in files:
            if file != '.DS_Store':
                logging.debug(f"  {os.path.join(root, file)}")


if __name__ == "__main__":
    source_dir = "source"
    avif_dir = "avif"
    jpeg2000_dir = "jpeg2000"
    output_dir = "output"

    setup_logging(output_dir)

    process_directory(source_dir, avif_dir, jpeg2000_dir, output_dir)

    print("Script execution complete. Please check the logs for detailed output.")