from pyzbar import pyzbar
import cv2

def read_qr_from_frame(frame):
    decoded_objs = pyzbar.decode(frame)
    for obj in decoded_objs:
        return obj.data.decode('utf-8')
    return None
