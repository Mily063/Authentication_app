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
            qr_id = read_qr_from_frame(frame)
            if qr_id:
                self.process_qr(qr_id, frame)
                return

            # Display the video feed
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(10, self.scan_loop)

    def process_qr(self, qr_id, frame):
        now = int(time.time())
        kod = db.session.query(KodyQR).filter_by(id_kodu_qr=qr_id).first()
        if not kod or kod.status_kodu != StatusKoduEnum.Aktywny or kod.data_waznosci < now:
            self.log_entry(now, qr_id, None, None, WynikProbyEnum.OdmowaKodNiewazny)
            self.label.config(text="ODMOWA - kod nieważny")
            self.root.after(2000, self.reset)
            return

        pracownik = db.session.query(Pracownicy).filter_by(id_pracownika=kod.id_pracownika).first()
        if not pracownik or not pracownik.status_uprawnien:
            self.log_entry(now, qr_id, kod.id_pracownika, None, WynikProbyEnum.OdmowaBrakUprawnien)
            self.label.config(text="ODMOWA - brak uprawnień")
            self.root.after(2000, self.reset)
            return

        self.label.config(text="Zeskanowano QR. Ustaw twarz przed kamerą...")
        self.root.after(5000, lambda: self.scan_face(pracownik, qr_id, now))

    def scan_face(self, pracownik, qr_id, timestamp):
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

        self.root.after(2000, self.reset)

    def reset(self):
        self.label.config(text="Oczekiwanie na kod QR...")
        self.scan_loop()

    def on_closing(self):
        self.running = False
        self.cap.release()
        self.root.destroy()

if __name__ == '__main__':
    with app.app_context():
        root = tk.Tk()
        app = FaceRecognitionApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
