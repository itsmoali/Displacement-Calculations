import sensor, image, time, json, math, pyb

# CONFIG
MM_PER_PIXEL = 0.06  # Adjust based on setup
JSON_FILE = "BLOB_TEST.json"
TOTAL_CYCLES = 1000
SAMPLES_PER_CYCLE = 5
# Adjust based on the color of the target blob
THRESHOLD = (150, 255)

# GPIO: Using Pin 0 (P0) as a Trigger Input
# Robot will set this pin HIGH when it arrives at each measurement point
trigger_pin = pyb.Pin("P0", pyb.Pin.IN, pyb.Pin.PULL_DOWN)

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time = 2000)

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)

# Global variables to store the "Home" center point
ref_cx = 0.0
ref_cy = 0.0

# Pre-allocate buffer for images, so robot can do other stuff and not sitt still
burst_buffers = []
for i in range(SAMPLES_PER_CYCLE):
    burst_buffers.append(sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE))

# Helper function to find the target blob
def find_target_blob(img):
    blobs = img.find_blobs([THRESHOLD], pixels_threshold=200, area_threshold=200, merge=True)
    if blobs:
        # Return the largest blob by pixel count
        return max(blobs, key=lambda b: b.pixels())
    return None

# Capture the golden reference position
def capture_golden_reference():
    global ref_cx, ref_cy
    print("Capturing Golden Reference...")

    # Take image and find blob
    img = sensor.snapshot()
    target = find_target_blob(img)

    # Draw for visial confirmation
    if target:
        ref_cx = target.cx()
        ref_cy = target.cy()
        img.draw_rectangle(target.rect())
        img.draw_cross(int(ref_cx), int(ref_cy))
        print("Reference Locked at Pixels: X:%0.1f, Y:%0.1f" % (ref_cx, ref_cy))
    else:
        print("ERROR: No blob found! Adjust your BLOB_THRESHOLD.")

# Find average displacement over multiple samples
def get_smoothed_displacement():
    total_dx = 0
    total_dy = 0
    found_count = 0

    for _ in range(SAMPLES_PER_CYCLE):
        img = sensor.snapshot()
        target = find_target_blob(img)

        if target:
            # Calculate pixel difference from the reference center
            total_dx += (target.cx() - ref_cx)
            total_dy += (target.cy() - ref_cy)
            found_count += 1

    if found_count == 0:
        return None, None, 0.0 # Failed to find blob

    # Calculate average pixel shift and convert to mm
    avg_dx_mm = (total_dx / found_count) * MM_PER_PIXEL
    avg_dy_mm = (total_dy / found_count) * MM_PER_PIXEL
    confidence = found_count / SAMPLES_PER_CYCLE
    return round(avg_dx_mm, 3), round(avg_dy_mm, 3), round(confidence, 3)

def log_iteration(cycle, dx, dy, conf):
    data = {"c": cycle, "dx": dx, "dy": dy, "conf": conf}
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

def wait_for_trigger():
    print("Waiting for Robot Signal on Pin P0...")
    # Wait for pin to go HIGH (Robot arrives)
    while trigger_pin.value() == 0:
        # Sleep in meantime while pin is low
        time.sleep_ms(10)

    print("Signal Received!")

    # Delay for stability
    time.sleep_ms(50)

# --- MAIN---

capture_golden_reference()
time.sleep(2)
# Clear the log file to start fresh
with open(JSON_FILE, "w") as f: f.write("")

# Main loop for total cycles
for cycle in range(TOTAL_CYCLES):

    # Robot signal
    # wait_for_trigger() # Uncomment for hardware trigger
    time.sleep(2)        # Manual delay for testing

    # Capture N images into RAM buffers
    print("\n Taking Burst Images...")
    for buf in burst_buffers:
        buf.replace(sensor.snapshot())

    print("Burst Complete!")

    # Background processing
    total_dx = 0
    total_dy = 0
    found_count = 0

    # Go through all images in buffer
    for buf in burst_buffers:
        target = find_target_blob(buf)
        if target:
            total_dx += (target.cx() - ref_cx)
            total_dy += (target.cy() - ref_cy)
            found_count += 1

    # Calculate average displacement and log
    if found_count > 0:
        avg_dx_mm = (total_dx / found_count) * MM_PER_PIXEL
        avg_dy_mm = (total_dy / found_count) * MM_PER_PIXEL
        conf = found_count / SAMPLES_PER_CYCLE

        log_iteration(cycle, round(avg_dx_mm, 3), round(avg_dy_mm, 3), conf)

        print("Cycle %d: DX: %0.3f, DY: %0.3f (Based on %d samples)" %
              (cycle, avg_dx_mm, avg_dy_mm, found_count))
    else:
        print("Cycle %d: FAILED - No blobs in burst" % cycle)

print("\nTest Complete.")
