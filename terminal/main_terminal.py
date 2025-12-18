import threading
import cv2
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
from terminal.qr_utils import read_qr_from_frame
from terminal.face_utils import compare_faces
from admin_panel.models import Pracownicy, KodyQR, RejestrWejsc, StatusKoduEnum, WynikProbyEnum
from admin_panel.db import db
from admin_panel.app import create_app
from config import FACE_MATCH_TOLERANCE, READER_ID

app = create_app()

class FaceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System SKD - Face Recognition")

        self.label = Label(root, text="Oczekiwanie na kod QR...", font=("Arial", 16))
        self.label.pack()

        self.video_label = Label(root)
        self.video_label.pack()

        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.processing_qr = False  # Flag to prevent multiple QR processing threads
        self.next_scan_face = None
        self.lock = threading.Lock()
        self.scan_loop()

    def log_entry(self, timestamp, qr_id, pracownik_id, wynik_twarzy, wynik_proby):
        entry = RejestrWejsc(
            timestamp=timestamp,
            id_kodu_qr_zeskanowany=qr_id,
            id_pracownika_zidentyfikowany=pracownik_id,
            wynik_weryfikacji_twarzy=str(wynik_twarzy) if wynik_twarzy is not None else None,
            wynik_proby_wejscia=wynik_proby,
            id_czytnika=READER_ID
        )
        db.session.add(entry)
        db.session.commit()

    def scan_loop(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if ret:
            # Display the video feed
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            # Check for QR code if not already processing
            if not self.processing_qr:
                qr_id = read_qr_from_frame(frame)
                if qr_id:
                    self.processing_qr = True
                    threading.Thread(target=self.process_qr, args=(qr_id, app.app_context())).start()

            # Handle delayed facial recognition
            with self.lock:
                if self.next_scan_face:
                    pracownik, qr_id, timestamp = self.next_scan_face
                    self.next_scan_face = None  # Reset state

                    # Schedule the facial recognition after a delay
                    self.label.config(text="Zeskanowano QR. Upewnij się, że twoja twarz jest widoczna w kamerze...")
                    self.root.after(3000, self.start_scan_face_thread, pracownik, qr_id, timestamp)

        self.root.after(10, self.scan_loop)

    def process_qr(self, qr_id, app_context):
        with app_context:  # Push the Flask app context for database operations
            now = int(time.time())
            kod = db.session.query(KodyQR).filter_by(id_kodu_qr=qr_id).first()
            if not kod or kod.status_kodu != StatusKoduEnum.Aktywny or kod.data_waznosci < now:
                self.log_entry(now, qr_id, None, None, WynikProbyEnum.OdmowaKodNiewazny)
                self.label.config(text="ODMOWA - kod nieważny")
                self.processing_qr = False
                return

            pracownik = db.session.query(Pracownicy).filter_by(id_pracownika=kod.id_pracownika).first()
            if not pracownik or not pracownik.status_uprawnien:
                self.log_entry(now, qr_id, kod.id_pracownika, None, WynikProbyEnum.OdmowaBrakUprawnien)
                self.label.config(text="ODMOWA - brak uprawnień")
                self.processing_qr = False
                return

            with self.lock:
                self.next_scan_face = (pracownik, qr_id, now)

    def start_scan_face_thread(self, pracownik, qr_id, timestamp):
        """Start the scan_face method in a new thread."""
        threading.Thread(target=self.scan_face, args=(pracownik, qr_id, timestamp, app.app_context())).start()

    def scan_face(self, pracownik, qr_id, timestamp, app_context):
        with app_context:
            self.label.config(text="Rejestracja twarzy...")
            start = time.time()
            match, distance = None, None
            found = False
            while time.time() - start < 5:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                match, distance = compare_faces(pracownik.wzorzec_twarzy, frame, tolerance=FACE_MATCH_TOLERANCE)
                if match is not None:
                    found = True
                    break

            if found and match:
                self.log_entry(timestamp, qr_id, pracownik.id_pracownika, distance, WynikProbyEnum.Zezwolono)
                self.label.config(text=f"Pracownik: {pracownik.imie} {pracownik.nazwisko} -> ZEZWOLONO")
            else:
                self.log_entry(timestamp, qr_id, pracownik.id_pracownika, distance, WynikProbyEnum.OdmowaNiezgodnosc)
                self.label.config(text="ODMOWA - Niezgodność Twarzy")
        
            # Reset the label after a delay
            self.root.after(3000, self.reset_label)
    
    def reset_label(self):
        # Reset the label to the default message
        self.processing_qr = False
        self.label.config(text="Oczekiwanie na kod QR...")

    def on_closing(self):
        self.running = False
        self.cap.release()
        self.root.destroy()


if __name__ == '__main__':
    with app.app_context():
        root = tk.Tk()
        SDKapp = FaceRecognitionApp(root)
        root.protocol("WM_DELETE_WINDOW", SDKapp.on_closing)
        root.mainloop()