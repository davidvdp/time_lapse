from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
import logging
from pathlib import Path
 
IMAGE_RESOLUTION = (1280, 960)
ROI = [0.65, 0.0, 0.1, 0.1]  # start_x, start_y, width, height in image scale
EXPECTED_INTENSITY = 150
MAX_SHUTTER = 1000000
MIN_SHUTTER = 1000
INTERVAL_SECONDS = 60

SHUTTER_SPEED = 200000

def check_exposure(image, tl, br):
    mean = np.mean(image[tl[1]:br[1], tl[0]:br[0]])
    return mean - EXPECTED_INTENSITY

def change_exposure(camera, diff):
    global SHUTTER_SPEED
    change = SHUTTER_SPEED * 0.05
    if SHUTTER_SPEED > 1990000:
        SHUTTER_SPEED = 200000
    elif SHUTTER_SPEED < 16:
        SHUTTER_SPEED = 200000
    elif diff < 0:
        SHUTTER_SPEED = int(SHUTTER_SPEED + change)
    else:
        SHUTTER_SPEED = int(SHUTTER_SPEED - change)
    camera.shutter_speed = SHUTTER_SPEED
    # get last capture this is with the old setting.
    time.sleep(2)
    logging.info(f'diff: {diff}, exposure: {camera.exposure_speed} us, new_shutter_speed: {SHUTTER_SPEED}')
    raw_capture = PiRGBArray(camera)
    camera.capture(raw_capture, format="rgb")
        

def captures(camera):
    # initialize the camera and grab a reference to the raw camera capture
    raw_capture = PiRGBArray(camera)
    time.sleep(2)
    while True:
        camera.capture(raw_capture, format="rgb")
        # grab an image from the camera
        image = raw_capture.array
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        yield image
        raw_capture.truncate(0)
    camera.close()
    
def draw_rect(image, tl, br):
    cv2.rectangle(image, tl, br, (0, 0, 0), thickness=2)
    cv2.rectangle(image, tl, br, (255, 255, 255), thickness=1)

def main():
    camera = PiCamera()
    camera.resolution = IMAGE_RESOLUTION
    camera.framerate = 0.5
    camera.shutter_speed = 15
    width, height = IMAGE_RESOLUTION
    roi_tl = (int(width * ROI[0]), int(height * ROI[1]))
    roi_br = (roi_tl[0] + int(width * ROI[2]), roi_tl[1] + int(height * ROI[3]))
    
    capture_dir = Path("/home/pi/captures")
    if not capture_dir.exists():
        print(f'Directory {capture_dir} does not exist')
        exit(-1)
    
    last_image = datetime.now() - timedelta(seconds=INTERVAL_SECONDS)
    cnt = 0
    for image in captures(camera):
        diff = check_exposure(image, roi_tl, roi_br)
        if abs(diff) > 0.035 * EXPECTED_INTENSITY:
            change_exposure(camera, diff)
        elif datetime.now() - last_image > timedelta(seconds=INTERVAL_SECONDS):
            last_image = datetime.now()
            date_time_fmt = str(int(datetime.timestamp(last_image)))
            image_name = f'{capture_dir}/{date_time_fmt}_{cnt:07d}.png'
            logging.info(f'saving image to {image_name}')
            cv2.imwrite(image_name, image)
            cnt += 1
        
        draw_rect(image, roi_tl, roi_br)
        cv2.imshow("Image", image)
        key = cv2.waitKey(10)
        if key == 27:
            raise KeyboardInterrupt
        

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    try:
        main()
    except KeyboardInterrupt:
        print('Closing...')
    exit(0)
