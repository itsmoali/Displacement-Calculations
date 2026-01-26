import sensor, image, time, math

# ------------
# CONFIG
# ------------
# Known real-world width of the object used for calibration (in mm)
REAL_WORLD_WIDTH_MM = 75.6
THRESHOLD = (200, 255)

# Calibration parameters (Change as needed depending on the size of the object)
PIXELS_THRESHOLD = 300
AREA_THRESHOLD = 300

SAMPLES = 30
PIXEL_STD_LIMIT = 0.3

# ------------
# SENSOR SETUP
# ------------
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time=2000)

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False, exposure_us=5000)
sensor.set_auto_whitebal(False)

print("\n--- CALIBRATION MODE (PRECISION) ---")
print("Hold object steady...")

# ------------
# MAIN LOOP
# ------------
while True:
    widths = []

    for _ in range(SAMPLES):
        img = sensor.snapshot()

        # Edge-based detection for better accuracy
        img.find_edges(image.EDGE_CANNY, threshold=THRESHOLD)

        blobs = img.find_blobs(
            [(255, 255)],
            pixels_threshold=PIXELS_THRESHOLD,
            area_threshold=AREA_THRESHOLD
        )

        if not blobs:
            widths.clear()
            continue

        b = max(blobs, key=lambda x: x.pixels())
        widths.append(b.w())

        img.draw_rectangle(b.rect(), color=255)

        time.sleep_ms(30)

    if not widths:
        print("No stable detection")
        continue

    mean_px = sum(widths) / len(widths)
    var_px = sum((w - mean_px) ** 2 for w in widths) / max(1, len(widths) - 1)
    sigma_px = math.sqrt(var_px)

    if sigma_px > PIXEL_STD_LIMIT:
        print("Unstable measurement (σ=%.3f px) — retry" % sigma_px)
        continue

    mm_per_pixel = REAL_WORLD_WIDTH_MM / mean_px

    print("\n=== CALIBRATION LOCKED ===")
    print("Mean Pixel Width : %.3f px" % mean_px)
    print("Pixel Std Dev    : %.4f px" % sigma_px)
    print("MM_PER_PIXEL     : %.6f mm/px" % mm_per_pixel)
    print("==========================\n")

    time.sleep(1000)
