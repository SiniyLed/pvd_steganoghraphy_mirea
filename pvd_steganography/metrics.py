import math
import os

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

from pvd_lib import pvd_lib


def calculate_metrics(original_path, stego_path):
    """
    Calculate PSNR, MSE, SSIM, and RMSE between original and stego images
    """
    # Load images
    original = Image.open(original_path)
    stego = Image.open(stego_path)

    # Convert to numpy arrays
    original_arr = np.array(original)
    stego_arr = np.array(stego)

    # Ensure images have same dimensions
    if original_arr.shape != stego_arr.shape:
        raise ValueError("Images must have the same dimensions")

    # Calculate MSE (Mean Squared Error)
    mse = np.mean((original_arr - stego_arr) ** 2)

    # Calculate RMSE (Root Mean Squared Error)
    rmse = np.sqrt(mse)

    # Calculate PSNR (Peak Signal-to-Noise Ratio)
    if mse == 0:
        psnr = float('inf')
    else:
        max_pixel = 255.0
        psnr = 20 * math.log10(max_pixel / math.sqrt(mse))

    # Calculate SSIM (Structural Similarity Index)
    # For color images, calculate SSIM for each channel and average
    if len(original_arr.shape) == 3:
        ssim_r = ssim(original_arr[:, :, 0], stego_arr[:, :, 0], data_range=255)
        ssim_g = ssim(original_arr[:, :, 1], stego_arr[:, :, 1], data_range=255)
        ssim_b = ssim(original_arr[:, :, 2], stego_arr[:, :, 2], data_range=255)
        ssim_value = (ssim_r + ssim_g + ssim_b) / 3
    else:
        ssim_value = ssim(original_arr, stego_arr, data_range=255)

    return {
        'PSNR': psnr,
        'MSE': mse,
        'SSIM': ssim_value,
        'RMSE': rmse
    }


def evaluate_pvd_steganography(original_image, secret_file, stego_image):
    """
    Comprehensive evaluation of PVD steganography
    """
    # Calculate embedding capacity
    capacity = pvd._embed_capacity(original_image)
    secret_size = os.path.getsize(secret_file)

    print("=== PVD Steganography Evaluation ===")
    print(f"Embedding capacity: {capacity} bytes")
    print(f"Secret file size: {secret_size} bytes")
    print(f"Capacity utilization: {(secret_size / capacity) * 100:.2f}%")

    # Calculate quality metrics
    metrics = calculate_metrics(original_image, stego_image)

    print("\n=== Quality Metrics ===")
    print(f"PSNR: {metrics['PSNR']:.2f} dB")
    print(f"MSE: {metrics['MSE']:.6f}")
    print(f"RMSE: {metrics['RMSE']:.6f}")
    print(f"SSIM: {metrics['SSIM']:.6f}")

    # Interpret results
    print("\n=== Interpretation ===")
    if metrics['PSNR'] > 40:
        print("PSNR: Excellent (>40 dB) - Very high quality")
    elif metrics['PSNR'] > 30:
        print("PSNR: Good (30-40 dB) - Good quality")
    else:
        print("PSNR: Poor (<30 dB) - Visible degradation")

    if metrics['SSIM'] > 0.95:
        print("SSIM: Excellent (>0.95) - Very similar structure")
    elif metrics['SSIM'] > 0.90:
        print("SSIM: Good (0.90-0.95) - Good structural similarity")
    else:
        print("SSIM: Poor (<0.90) - Structural differences noticeable")

    return metrics


# Пример использования:
if __name__ == "__main__":
    pvd = pvd_lib()

    original_img = "2.png"
    secret_file = "mes.txt"
    stego_img = "encoded.png"
    extracted_file = "another_mes.txt"

    #встраивание
    print("Embedding data...")
    embedded_bits = pvd.pvd_embed(original_img, secret_file, stego_img)
    print(f"Embedded bits: {embedded_bits}")

    #извлечение
    print("\nExtracting data...")
    extracted_bits = pvd.pvd_extract(original_img, extracted_file, stego_img)
    print(f"Extracted bits: {extracted_bits}")

    #оценка качества
    print("\nEvaluating steganography quality...")
    metrics = evaluate_pvd_steganography(original_img, secret_file, stego_img)

    #проверка целостности данных
    print("\n=== Data Integrity Check ===")
    with open(secret_file, 'rb') as f1, open(extracted_file, 'rb') as f2:
        original_data = f1.read()
        extracted_data = f2.read()

    if original_data == extracted_data:
        print("Data integrity: PERFECT - Secret file recovered exactly")
    else:
        print("Data integrity: FAILED - Extracted data differs from original")
        print(f"Original size: {len(original_data)} bytes")
        print(f"Extracted size: {len(extracted_data)} bytes")

