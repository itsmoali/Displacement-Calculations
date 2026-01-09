import sensor, image, time, json, pyb

# CONFIG
MM_PER_PIXEL = 0.06  #Adjust based on setup
JSON_FILE = "FFT_TEST.json"
TOTAL_CYCLES = 1000
SAMPLES_PER_CYCLE = 5
# Adjust based on the environment
THRESHOLD  =(150, 255)

# Locking all setting for reproducibility
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)

# GPIO: Using Pin 0 (P0) as a Trigger Input
# Robot will set this pin HIGH when it arrives at each measurement point
trigger_pin = pyb.Pin("P0", pyb.Pin.IN, pyb.Pin.PULL_DOWN)

# Ideal Imagae ram
ref_buffer = sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE)

# Pre-allocate buffer for images, so robot can do other stuff and not sitt still
burst_buffers = []
for i in range(SAMPLES_PER_CYCLE):
    burst_buffers.append(sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE))

# Capture the golden reference image
def capture_golden_reference():
    print("Capturing Golden Reference...")
    img = sensor.snapshot()
    img.find_edges(image.EDGE_CANNY, threshold=THRESHOLD )
    ref_buffer.replace(img)
    print("Reference Locked.")

# Log data to JSON file
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
with open(JSON_FILE, "w") as f: f.write("")

# Burst capture multiple images
for cycle in range(TOTAL_CYCLES):

    # Wait for robot trigger
    #wait_for_trigger() # Uncomment for hardware trigger
    time.sleep(2)        # Manual delay for testing

    print("\n Taking Burst Images...")

    # Capture N images into RAM buffers
    for buf in burst_buffers:
        buf.replace(sensor.snapshot())

    print("Burst Complete!")


    # Background processing of the images
    print("Processing data in background...")
    total_dx = 0
    total_dy = 0
    total_conf = 0

    # Processes each image and takes an average to reduce environemnt and system noise
    for buf in burst_buffers:
        # Process the stored frame from RAM
        buf.find_edges(image.EDGE_CANNY, threshold=THRESHOLD )
        # Finds displacement from reference
        res = buf.find_displacement(ref_buffer, logpolar=False)

        total_dx += res.x_translation()
        total_dy += res.y_translation()
        total_conf += res.response()

    # Calculate average displacement and confidence
    avg_dx_mm = -(total_dx / SAMPLES_PER_CYCLE) * MM_PER_PIXEL
    avg_dy_mm = -(total_dy / SAMPLES_PER_CYCLE) * MM_PER_PIXEL
    avg_conf = total_conf / SAMPLES_PER_CYCLE

    log_iteration(cycle, round(avg_dx_mm, 3), round(avg_dy_mm, 3), round(avg_conf, 3))

    print("Cycle %d Logged: DX: %0.3f, DY: %0.3f" % (cycle, avg_dx_mm, avg_dy_mm))
    # Wait for the remainder of the robot's cycle if necessary
    time.sleep(1)

print("\nTest Complete.")
