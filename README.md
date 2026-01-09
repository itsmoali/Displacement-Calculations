# Precision Displacement Tracking for Robotic Repeatability

This repository contains two computer vision implementations for measuring microscopic drift and displacement in robotic systems using the **OpenMV H7 Plus**. These scripts are optimized for repeatability testing where a target precision of $0.01\text{ mm}$ or better is required.


## Methodologies

### 1. Phase Correlation (FFT-Based)
This method utilizes a **Fast Fourier Transform** to perform frequency-domain cross-correlation between a "Golden Reference" and live frames.

* **Best For:** Low-contrast surfaces and sub-pixel accuracy.
* **Logic:** It extracts edges using a Canny filter and identifies the translation peak in the frequency domain.


### 2. Connected Component Analysis (Blob Detection)
This method tracks a specific high-contrast target and calculates its **Centroid** based on a neighbouring average.

* **Best For:** High speed and scenarios with high-contrast targets.
* **Logic:** It segments the image based on a color/brightness threshold and tracks the $cx, cy$ coordinates of the largest object.


---

## Calibration & Setup

### Determining the MM/Pixel Ratio
The tracking accuracy is dependent on the distance from the lens to the target.
1.  Place a reference object of a known size at the robot's working height.
2.  Use the provided `calibration.py` script to find the pixel-to-millimeter ratio.
3.  Ensure the camera is perfectly parallel to the target surface to avoid perspective distortion.

---

## 💻 Usage

1.  **Initialize Hardware:** Open the desired implementation script in the OpenMV IDE.
2.  **Set Golden Reference:** Position the robot at its "Home" or "Ideal" position and run one of the two scripts. The first frame will be stored as the baseline.
3.  **Start Test:**  For debugging, sleep functions have been used to change object positions. GPIO pin 0 is used to recieve signals from the robot hardware.
    * The camera will wait for a signal on **Pin P0**.
    * Once triggered, it will capture $N$ samples into SDRAM.
    * Displacement results will be printed to the terminal and logged to the SD card in a json file. Each script has a seperate json logging file.
4.  **Analysis:** After the test, import the JSON file into Excel, Python, or MATLAB for statistical drift analysis.

---
