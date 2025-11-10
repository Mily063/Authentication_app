import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import time
from terminal.qr_utils import read_qr_from_frame
from terminal.face_utils import compare_faces
from admin_panel.models import Pracownicy, KodyQR, RejestrWejsc, StatusKoduEnum, WynikProbyEnum
from admin_panel.db import db
from admin_panel.app import create_app
from config import FACE_MATCH_TOLERANCE, READER_ID

app = create_app()

def log_entry(timestamp, qr_id, pracownik_id, wynik_twarzy, wynik_proby):
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

def main_loop():
    cap = cv2.VideoCapture(0)
    print('System SKD: Oczekiwanie na kod QR...')
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        qr_id = read_qr_from_frame(frame)
        if qr_id:
            print(f"DEBUG: Wykryto kod QR: {qr_id}")
            now = int(time.time())
            kod = db.session.query(KodyQR).filter_by(id_kodu_qr=qr_id).first()
            if not kod or kod.status_kodu != StatusKoduEnum.Aktywny or kod.data_waznosci < now:
                log_entry(now, qr_id, None, None, WynikProbyEnum.OdmowaKodNiewazny)
                print('ODMOWA - kod nieważny')
                time.sleep(2)
                continue
            pracownik = db.session.query(Pracownicy).filter_by(id_pracownika=kod.id_pracownika).first()
            if not pracownik or not pracownik.status_uprawnien:
                log_entry(now, qr_id, kod.id_pracownika, None, WynikProbyEnum.OdmowaBrakUprawnien)
                print('ODMOWA - brak uprawnień')
                time.sleep(2)
                continue
            print('Zeskanowano QR. Masz 5 sekund na ustawienie twarzy przed kamerą...')
            time.sleep(5)
            print('Rejestracja twarzy...')
            start = time.time()
            match, distance = None, None
            found = False
            while time.time() - start < 5:
                ret2, frame2 = cap.read()
                if not ret2:
                    continue
                match, distance = compare_faces(pracownik.wzorzec_twarzy, frame2, tolerance=FACE_MATCH_TOLERANCE)
                if match is not None:
                    found = True
                    break
            if found and match:
                log_entry(now, qr_id, pracownik.id_pracownika, distance, WynikProbyEnum.Zezwolono)
                print('ZEZWOLONO')
            else:
                log_entry(now, qr_id, pracownik.id_pracownika, distance, WynikProbyEnum.OdmowaNiezgodnosc)
                print('ODMOWA - Niezgodność Twarzy')
            time.sleep(2)
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    with app.app_context():
        main_loop()
