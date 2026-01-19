import sensor, image, time, json, math, pyb

# --- CONFIG ---
MM_PER_PIXEL = 0.06
JSON_FILE = "CIRCLE_TEST_PRO.json"
TOTAL_CYCLES = 1000
SAMPLES_PER_CYCLE = 5

# CIRCLE PARAMETERS
R_MIN, R_MAX = 20, 100
MAG_THRESHOLD = 2000
ROI_PADDING = 40  # Extra space around the circle for the search window

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)

# --- GLOBAL STATE ---
ref_cx, ref_cy = 0.0, 0.0
# Initialize ROI to full screen [x, y, w, h]
search_roi = (0, 0, sensor.width(), sensor.height())

def find_target_circle(img):
    global search_roi

    # 1. BLUR: Removes high-frequency noise that causes false edges
    img.gaussian(1)

    # 2. SEARCH: Only look inside the current ROI
    circles = img.find_circles(threshold=MAG_THRESHOLD,
                               roi=search_roi,
                               x_stride=2, y_stride=2,
                               r_min=R_MIN, r_max=R_MAX)

    if circles:
        # Get the strongest circle
        target = max(circles, key=lambda c: c.magnitude())

        # 3. UPDATE ROI: Center the next search window on this circle
        new_x = target.x() - (target.r() + ROI_PADDING)
        new_y = target.y() - (target.r() + ROI_PADDING)
        new_size = (target.r() + ROI_PADDING) * 2

        # Ensure ROI stays within camera bounds
        search_roi = (max(0, int(new_x)),
                      max(0, int(new_y)),
                      min(sensor.width(), int(new_size)),
                      min(sensor.height(), int(new_size)))
        return target
    else:
        # 4. RESET ROI: If we lose the object, look at the whole screen next time
        search_roi = (0, 0, sensor.width(), sensor.height())
        return None

def capture_golden_reference():
    global ref_cx, ref_cy
    print("Waiting for stable Golden Reference lock...")

    while True:
        img = sensor.snapshot()
        target = find_target_circle(img)

        if target:
            ref_cx, ref_cy = target.x(), target.y()
            img.draw_circle(target.x(), target.y(), target.r(), color=255)
            print("Reference Locked! X:%0.1f, Y:%0.1f" % (ref_cx, ref_cy))
            break
        else:
            print("Searching for object...")
            time.sleep_ms(100)

def log_iteration(cycle, dx, dy, conf):
    data = {"c": cycle, "dx": dx, "dy": dy, "conf": conf}
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

# --- MAIN EXECUTION ---

capture_golden_reference()
with open(JSON_FILE, "w") as f: f.write("") # Clear log

for cycle in range(TOTAL_CYCLES):
    time.sleep(1) # Simulated trigger delay

    found_count = 0
    total_dx, total_dy = 0, 0

    print("Cycle %d: Processing..." % cycle)

    for _ in range(SAMPLES_PER_CYCLE):
        img = sensor.snapshot()
        target = find_target_circle(img)

        if target:
            total_dx += (target.x() - ref_cx)
            total_dy += (target.y() - ref_cy)
            found_count += 1
            # Visual feedback on the OpenMV IDE frame buffer
            img.draw_rectangle(search_roi, color=125)
            img.draw_cross(target.x(), target.y(), color=255)

    if found_count > 0:
        avg_dx = (total_dx / found_count) * MM_PER_PIXEL
        avg_dy = (total_dy / found_count) * MM_PER_PIXEL
        conf = found_count / SAMPLES_PER_CYCLE
        log_iteration(cycle, round(avg_dx, 3), round(avg_dy, 3), conf)
        print(" -> Detected. Shift: %0.3f, %0.3f" % (avg_dx, avg_dy))
    else:
        print(" -> FAILED (Object lost)")
