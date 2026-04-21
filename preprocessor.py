"""
module1_vision/preprocessor.py
--------------------------------
Normalises any incoming screenshot to the 1920x1080 canonical frame
and applies per-task image enhancements before OCR or template matching.
"""

import cv2
import numpy as np
from typing import Tuple


BASELINE_W, BASELINE_H = 1920, 1080


def load_image(path: str) -> np.ndarray:
    """Load an image from disk; raise FileNotFoundError on failure."""
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return img


def normalise_resolution(img: np.ndarray) -> Tuple[np.ndarray, float, float]:
    """
    Resize the image to 1920x1080 baseline.

    Returns
    -------
    normalised : np.ndarray
        Resized image.
    scale_x : float
        Width scale factor (original → baseline).
    scale_y : float
        Height scale factor (original → baseline).
    """
    h, w = img.shape[:2]
    scale_x = BASELINE_W / w
    scale_y = BASELINE_H / h

    if scale_x == 1.0 and scale_y == 1.0:
        return img, 1.0, 1.0

    resized = cv2.resize(img, (BASELINE_W, BASELINE_H), interpolation=cv2.INTER_LANCZOS4)
    return resized, scale_x, scale_y


def crop_region(img: np.ndarray, region: list) -> np.ndarray:
    """
    Crop a [x, y, w, h] region from the image.
    Clamps coordinates to image bounds safely.
    """
    x, y, w, h = region
    ih, iw = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(iw, x + w), min(ih, y + h)
    return img[y1:y2, x1:x2]


def enhance_for_ocr(img: np.ndarray, mode: str = "auto") -> np.ndarray:
    """
    Prepare a cropped region for OCR.

    Parameters
    ----------
    mode : str
        "auto"    — detect best method from image content
        "dark_bg" — white text on dark background (pot, stacks default)
        "light_bg"— dark text on light background
        "colour"  — pass to easyOCR without binarization
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    if mode == "auto":
        mean_val = np.mean(gray)
        mode = "dark_bg" if mean_val < 128 else "light_bg"

    if mode == "colour":
        # Return upscaled colour crop for easyOCR
        return cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    # Upscale for better OCR accuracy
    upscaled = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(upscaled, h=10)

    # Adaptive threshold to handle shadows and uneven lighting
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY if mode == "light_bg" else cv2.THRESH_BINARY_INV,
        blockSize=15, C=8
    )

    # Morphological cleanup — remove tiny noise dots
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return cleaned


def enhance_for_card_detection(img: np.ndarray) -> np.ndarray:
    """
    Sharpen and normalise contrast for card region matching.
    """
    # Bilateral filter — preserves edges while smoothing noise
    smooth = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)

    # CLAHE for contrast normalisation across different lighting conditions
    lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    enhanced = cv2.merge([l_eq, a, b])

    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
