import sensor, image, time

# Config
REAL_WORLD_WIDTH_MM = 75.6  # Width of an object in mm
THRESHOLD = (200, 255)      # Change as needed for lighting conditions

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False)
sensor.set_auto_exposure(False, exposure_us=5000)

print("--- CALIBRATION MODE ---")

while(True):
    img = sensor.snapshot()
    blobs = img.find_blobs([THRESHOLD], pixels_threshold=200, area_threshold=200)

    if blobs:
        b = max(blobs, key=lambda x: x.pixels())
        img.draw_rectangle(b.rect(), color=255)

        pixel_width = b.w()
        mm_per_pixel = REAL_WORLD_WIDTH_MM / pixel_width

        # Display
        img.draw_string(10, 10, "PX Width: %d" % pixel_width, color=255, scale=2)
        img.draw_string(10, 40, "Ratio: %0.6f" % mm_per_pixel, color=255, scale=2)

        print("Pixel Width: %d | Suggested MM_PER_PIXEL: %0.6f" % (pixel_width, mm_per_pixel))

    time.sleep_ms(100)
