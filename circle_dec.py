import sensor, image, time, json, math, pyb

# CONFIG
MM_PER_PIXEL = 0.06  # Adjust based on setup
JSON_FILE = "CIRCLE_TEST.json"
TOTAL_CYCLES = 1000
SAMPLES_PER_CYCLE = 5

# CIRCLE DETECTION CONFIG
# Note: find_circles uses edge gradients, so THRESHOLD is used less strictly
# or can be ignored if you run it on the raw grayscale image.
R_MIN = 20    # Minimum radius of the circle to find
R_MAX = 100   # Maximum radius of the circle to find
MAG_THRESHOLD = 2000 # Controls how "strong" the circle edges must be

# GPIO: Using Pin 0 (P0) as a Trigger Input
trigger_pin = pyb.Pin("P0", pyb.Pin.IN, pyb.Pin.PULL_DOWN)

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA) # If this is too slow, change to sensor.QVGA
sensor.skip_frames(time = 2000)

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)

# Global variables to store the "Home" center point
ref_cx = 0.0
ref_cy = 0.0

# Pre-allocate buffer for images
burst_buffers = []
for i in range(SAMPLES_PER_CYCLE):
    burst_buffers.append(sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE))

# Helper function to find the target circle
def find_target_circle(img):
    # x_stride and y_stride can be increased to speed up the search
    circles = img.find_circles(threshold=MAG_THRESHOLD,
                               x_stride=2,
                               y_stride=2,
                               r_min=R_MIN,
                               r_max=R_MAX,
                               r_step=2)
    if circles:
        # Return the circle with the strongest magnitude (most distinct shape)
        return max(circles, key=lambda c: c.magnitude())
    return None

# Capture the golden reference position
def capture_golden_reference():
    global ref_cx, ref_cy
    print("Capturing Golden Reference Circle...")

    img = sensor.snapshot()
    target = find_target_circle(img)

    if target:
        ref_cx = target.x()
        ref_cy = target.y()
        # Draw for visual confirmation
        img.draw_circle(target.x(), target.y(), target.r(), color=255)
        img.draw_cross(int(ref_cx), int(ref_cy), color=255)
        print("Reference Locked at Pixels: X:%0.1f, Y:%0.1f" % (ref_cx, ref_cy))
    else:
        print("ERROR: No circle found! Adjust R_MIN/R_MAX or MAG_THRESHOLD.")

# --- MAIN ---

capture_golden_reference()
time.sleep(2)

# Clear the log file
with open(JSON_FILE, "w") as f: f.write("")

for cycle in range(TOTAL_CYCLES):
    # wait_for_trigger() # Uncomment for hardware trigger
    time.sleep(1) # Testing delay

    print("\n Taking Burst Images...")
    for buf in burst_buffers:
        buf.replace(sensor.snapshot())

    print("Processing Burst...")
    total_dx = 0
    total_dy = 0
    found_count = 0

    for buf in burst_buffers:
        target = find_target_circle(buf)
        if target:
            # target.x() and target.y() are the center of the circle
            total_dx += (target.x() - ref_cx)
            total_dy += (target.y() - ref_cy)
            found_count += 1

    if found_count > 0:
        avg_dx_mm = (total_dx / found_count) * MM_PER_PIXEL
        avg_dy_mm = (total_dy / found_count) * MM_PER_PIXEL
        conf = found_count / SAMPLES_PER_CYCLE

        log_iteration(cycle, round(avg_dx_mm, 3), round(avg_dy_mm, 3), conf)
        print("Cycle %d: DX: %0.3f, DY: %0.3f (Based on %d samples)" %
              (cycle, avg_dx_mm, avg_dy_mm, found_count))
    else:
        print("Cycle %d: FAILED - No circles detected" % cycle)

print("\nTest Complete.")
