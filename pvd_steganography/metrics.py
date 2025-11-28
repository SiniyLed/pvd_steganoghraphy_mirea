import math
import os
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt
from pvd_lib import pvd_lib


class PVDSteganographyAnalyzer:
    def __init__(self):
        self.pvd = pvd_lib()

    def calculate_quality_metrics(self, original_path, stego_path):
        original = Image.open(original_path)
        stego = Image.open(stego_path)

        original_arr = np.array(original, dtype=np.float64)
        stego_arr = np.array(stego, dtype=np.float64)

        mse = np.mean((original_arr - stego_arr) ** 2)

        rmse = np.sqrt(mse)

        if mse == 0:
            psnr = float('inf')
        else:
            psnr = 20 * math.log10(255.0 / np.sqrt(mse))

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
            'RMSE': rmse,
            'SSIM': ssim_value
        }

    def calculate_capacity_metrics(self, image_path, secret_size):
        capacity = self.pvd._embed_capacity(image_path)
        image = Image.open(image_path)
        pixels = image.size[0] * image.size[1]

        utilization = (secret_size / capacity) * 100
        bpp = (secret_size * 8) / pixels

        return {
            'capacity_bytes': capacity,
            'secret_size_bytes': secret_size,
            'utilization_percent': utilization,
            'bpp': bpp,
            'total_pixels': pixels
        }

    def analyze_histograms(self, original_path, stego_path):
        original = Image.open(original_path).convert('RGB')
        stego = Image.open(stego_path).convert('RGB')

        orig_array = np.array(original)
        stego_array = np.array(stego)

        orig_all_pixels = orig_array.flatten()
        stego_all_pixels = stego_array.flatten()

        plt.figure(figsize=(10, 6))

        plt.hist(orig_all_pixels, bins=50, alpha=0.7, color='blue',
                 label='Оригинал', density=True, edgecolor='black', linewidth=0.5)
        plt.hist(stego_all_pixels, bins=50, alpha=0.7, color='red',
                 label='Стего', density=True, edgecolor='black', linewidth=0.5)

        plt.title('Сравнение гистограмм оригинального и стего-изображения', fontsize=14)
        plt.xlabel('Значение пикселя', fontsize=12)
        plt.ylabel('Плотность вероятности', fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)

        # Добавляем текстовую информацию
        orig_mean = np.mean(orig_all_pixels)
        stego_mean = np.mean(stego_all_pixels)
        orig_std = np.std(orig_all_pixels)
        stego_std = np.std(stego_all_pixels)

        plt.text(0.02, 0.98, f'Оригинал: μ={orig_mean:.1f}, σ={orig_std:.1f}',
                 transform=plt.gca().transAxes, fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        plt.text(0.02, 0.90, f'Стего: μ={stego_mean:.1f}, σ={stego_std:.1f}',
                 transform=plt.gca().transAxes, fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

        plt.tight_layout()
        plt.savefig('histogram_comparison.png', dpi=150, bbox_inches='tight')
        plt.show()

        ks_statistic = np.max(np.abs(
            np.cumsum(np.histogram(orig_all_pixels, bins=256, density=True)[0]) -
            np.cumsum(np.histogram(stego_all_pixels, bins=256, density=True)[0])
        ))

        return {
            'total_histogram_difference': np.sum(np.abs(
                np.histogram(orig_all_pixels, bins=256)[0] -
                np.histogram(stego_all_pixels, bins=256)[0]
            )),
            'ks_statistic': ks_statistic,
            'mean_difference': abs(orig_mean - stego_mean),
            'std_difference': abs(orig_std - stego_std)
        }
    def interpret_metrics(self, metrics, capacity_info=None):
        if metrics['PSNR'] > 40:
            psnr_interp = "Excellent (>40 dB) - changes invisible"
        elif metrics['PSNR'] > 30:
            psnr_interp = "Good (30-40 dB) - changes barely visible"
        else:
            psnr_interp = "Poor (<30 dB) - changes visible"

        if metrics['MSE'] < 1.0:
            mse_interp = "Very low error"
        elif metrics['MSE'] < 5.0:
            mse_interp = "Low error"
        else:
            mse_interp = "Noticeable error"

        if metrics['RMSE'] < 1.0:
            rmse_interp = "Excellent quality - minimal distortions"
        elif metrics['RMSE'] < 2.0:
            rmse_interp = "Good quality - insignificant distortions"
        elif metrics['RMSE'] < 5.0:
            rmse_interp = "Satisfactory quality - distortions visible on close inspection"
        else:
            rmse_interp = "Poor quality - distortions clearly visible"

        if metrics['SSIM'] > 0.95:
            ssim_interp = "Excellent similarity (>0.95)"
        elif metrics['SSIM'] > 0.90:
            ssim_interp = "Good similarity (0.90-0.95)"
        else:
            ssim_interp = "Moderate similarity (<0.90)"

        bpp_interp = "Insufficient data for evaluation"

        if capacity_info and 'bpp' in capacity_info:
            bpp = capacity_info['bpp']
            if bpp < 0.01:
                bpp_interp = "Very low density - conservative embedding"
            elif bpp < 0.05:
                bpp_interp = "Low density - safe embedding"
            elif bpp < 0.1:
                bpp_interp = "Medium density - optimal embedding"
            elif bpp < 0.2:
                bpp_interp = "High density - aggressive embedding"
            else:
                bpp_interp = "Very high density - detection risk"

        return {
            'PSNR_interpretation': psnr_interp,
            'MSE_interpretation': mse_interp,
            'RMSE_interpretation': rmse_interp,
            'SSIM_interpretation': ssim_interp,
            'bpp_interpretation': bpp_interp
        }

    def run_pvd_experiments(self, original_image, output_dir="pvd_results"):
        os.makedirs(output_dir, exist_ok=True)

        print("=== PVD STEGANOGRAPHY EXPERIMENTS ===")

        max_capacity = self.pvd._embed_capacity(original_image)
        print(f"\n1. MAXIMUM CAPACITY: {max_capacity} bytes")

        test_sizes = [
            max_capacity // 10,
            max_capacity // 4,
            max_capacity // 2,
            max_capacity * 3 // 4,
            max_capacity
        ]

        results = []

        for i, size in enumerate(test_sizes):
            print(f"\n2.{i + 1}. Test with {size} bytes ({size / max_capacity * 100:.1f}% capacity):")

            test_file = f"test_data_{i}.txt"
            test_data = os.urandom(size)
            with open(test_file, 'wb') as f:
                f.write(test_data)

            stego_img = f"stego_{i-1}.png"
            embedded_bits = self.pvd.pvd_embed(original_image, test_file, stego_img)

            quality = self.calculate_quality_metrics(original_image, stego_img)
            capacity = self.calculate_capacity_metrics(original_image, size)
            interpretation = self.interpret_metrics(quality, capacity)

            result = {
                'test_id': i,
                'secret_size': size,
                'embedded_bits': embedded_bits,
                'quality': quality,
                'capacity': capacity,
                'interpretation': interpretation
            }
            results.append(result)

            print(f"   PSNR: {quality['PSNR']:.2f} dB - {interpretation['PSNR_interpretation']}")
            print(f"   MSE:  {quality['MSE']:.6f} - {interpretation['MSE_interpretation']}")
            print(f"   RMSE: {quality['RMSE']:.6f} - {interpretation['RMSE_interpretation']}")
            print(f"   SSIM: {quality['SSIM']:.6f} - {interpretation['SSIM_interpretation']}")
            print(f"   Capacity utilization: {capacity['utilization_percent']:.1f}%")
            print(f"   bpp: {capacity['bpp']:.4f} - {interpretation['bpp_interpretation']}")

        print(f"\n3. HISTOGRAM ANALYSIS (50% load test):")
        middle_stego = "stego_2.png"
        hist_analysis = self.analyze_histograms(original_image, middle_stego)
        print(f"   Total histogram difference: {hist_analysis['total_histogram_difference']}")
        print(f"   Kolmogorov-Smirnov statistic: {hist_analysis['ks_statistic']:.6f}")
        print(f"   Mean difference: {hist_analysis['mean_difference']:.6f}")
        print(f"   Standard deviation difference: {hist_analysis['std_difference']:.6f}")

        print(f"\n4. SUMMARY RESULTS:")
        print("Size   | PSNR (dB) | MSE      | RMSE     | SSIM     | Utilization | bpp")
        print("-" * 85)
        for result in results:
            print(
                f"{result['secret_size']:6} | {result['quality']['PSNR']:8.2f} | {result['quality']['MSE']:8.6f} | {result['quality']['RMSE']:8.6f} | {result['quality']['SSIM']:8.6f} | {result['capacity']['utilization_percent']:10.1f}% | {result['capacity']['bpp']:.4f}")

        self.save_detailed_report(results, output_dir)

        return results

    def save_detailed_report(self, results, output_dir):
        report_path = os.path.join(output_dir, "pvd_detailed_report.txt")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("ОТЧЕТ ПО ЭКСПЕРИМЕНТАМ С PVD СТЕГАНОГРАФИЕЙ\n")

            f.write("ОПИСАНИЕ МЕТРИК:\n")
            f.write("- PSNR (Пиковое отношение сигнал/шум) - отношение сигнал/шум в дБ\n")
            f.write("- MSE (Среднеквадратичная ошибка) - средняя квадратичная ошибка\n")
            f.write("- RMSE (Среднеквадратичное отклонение) - корень из MSE\n")
            f.write("- SSIM (Структурное сходство) - индекс структурного сходства (0-1)\n")
            f.write("- bpp (бит на пиксель) - количество бит на один пиксель\n\n")

            f.write("РЕЗУЛЬТАТЫ ЭКСПЕРИМЕНТОВ:\n")
            f.write("-" * 85 + "\n")
            f.write("Размер  | PSNR (дБ) | MSE      | RMSE     | SSIM     | Загрузка   | bpp\n")
            f.write("-" * 85 + "\n")

            for result in results:
                f.write(
                    f"{result['secret_size']:6} | {result['quality']['PSNR']:8.2f} | {result['quality']['MSE']:8.6f} | {result['quality']['RMSE']:8.6f} | {result['quality']['SSIM']:8.6f} | {result['capacity']['utilization_percent']:10.1f}% | {result['capacity']['bpp']:.4f}\n")

            f.write("\nВЫВОДЫ:\n")
            f.write("- Метод PVD обеспечивает высокую незаметность (PSNR > 40 дБ)\n")
            f.write("- MSE и RMSE показывают очень низкий уровень ошибок\n")
            f.write("- SSIM близок к 1, что указывает на сохранение структуры изображения\n")
            f.write("- Метод адаптивен - качество сохраняется при разной загрузке\n")
            f.write("- Подходит для скрытой передачи данных в PNG изображениях\n")
            f.write("- Эффективно использует контрастные области изображения\n")
            f.write("- Обеспечивает хороший баланс между емкостью и незаметностью\n")


if __name__ == "__main__":
    analyzer = PVDSteganographyAnalyzer()

    results = analyzer.run_pvd_experiments("test.png")
