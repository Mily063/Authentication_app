#!/usr/bin/env python3
"""
Seed script to create a clean SQLite database and generate synthetic demo
employees with pseudo-random 128-D face embeddings and sample QR codes.

This script operates completely offline:
- No physical camera required
- No pre-trained dlib .dat models required
- All biometric vectors and user data are 100% synthetic
"""

import os
import sys
import time
import uuid
import types
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Stub terminal.face_utils to prevent dlib model loading errors when importing models/views
if 'terminal' not in sys.modules:
    sys.modules['terminal'] = types.ModuleType('terminal')
if 'terminal.face_utils' not in sys.modules:
    fake_face_utils = types.ModuleType('terminal.face_utils')
    fake_face_utils.save_face_embedding = lambda *args, **kwargs: None
    fake_face_utils.load_face_embedding = lambda *args, **kwargs: None
    fake_face_utils.compare_faces = lambda *args, **kwargs: (False, 0.0)
    fake_face_utils.save_face_embedding_from_video = lambda *args, **kwargs: None
    sys.modules['terminal.face_utils'] = fake_face_utils

import numpy as np
from flask import Flask
from config import DB_PATH, FACE_EMBEDDINGS_DIR
from admin_panel.db import db
from admin_panel.models import Pracownicy, KodyQR, RejestrWejsc, StatusKoduEnum, WynikProbyEnum


def init_db(app: Flask):
    """Ensure directory exists and create all tables according to SQLAlchemy schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(FACE_EMBEDDINGS_DIR, exist_ok=True)

    with app.app_context():
        # Remove existing SQLite DB if present to ensure clean seed
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        db.create_all()


def seed_data(app: Flask):
    """Seed synthetic employees, 128-D numpy embeddings, and active QR codes."""
    # Deterministic RNG seed for reproducible demo data
    rng = np.random.default_rng(seed=42)

    demo_employees = [
        {"imie": "Jan", "nazwisko": "Testowy", "status": True},
        {"imie": "Anna", "nazwisko": "Przykładowa", "status": True},
        {"imie": "Piotr", "nazwisko": "Demonstracyjny", "status": True},
    ]

    created_records = []

    with app.app_context():
        now = int(time.time())

        for idx, emp_info in enumerate(demo_employees, start=1):
            # Generate deterministic 128-D unit vector
            vector = rng.standard_normal(128).astype(np.float64)
            vector = vector / np.linalg.norm(vector)

            embedding_filename = f"demo_embedding_emp_{idx}_{uuid.uuid5(uuid.NAMESPACE_DNS, f'demo-{idx}').hex[:8]}.npy"
            embedding_path = os.path.join(FACE_EMBEDDINGS_DIR, embedding_filename)
            np.save(embedding_path, vector)

            pracownik = Pracownicy(
                imie=emp_info["imie"],
                nazwisko=emp_info["nazwisko"],
                wzorzec_twarzy=embedding_path,
                status_uprawnien=emp_info["status"]
            )
            db.session.add(pracownik)
            db.session.flush()  # Populates id_pracownika

            # Create sample QR code token valid for 30 days
            qr_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-qr-token-{idx}"))
            valid_until = now + (30 * 86400)
            kod_qr = KodyQR(
                id_kodu_qr=qr_id,
                id_pracownika=pracownik.id_pracownika,
                data_waznosci=valid_until,
                status_kodu=StatusKoduEnum.Aktywny
            )
            db.session.add(kod_qr)

            created_records.append({
                "id": pracownik.id_pracownika,
                "name": f"{pracownik.imie} {pracownik.nazwisko}",
                "embedding_path": embedding_path,
                "qr_id": qr_id
            })

        # Add sample entry history in RejestrWejsc
        sample_log_1 = RejestrWejsc(
            timestamp=now - 3600,
            id_kodu_qr_zeskanowany=created_records[0]["qr_id"],
            id_pracownika_zidentyfikowany=created_records[0]["id"],
            wynik_weryfikacji_twarzy="0.32",
            wynik_proby_wejscia=WynikProbyEnum.Zezwolono,
            id_czytnika=1
        )
        sample_log_2 = RejestrWejsc(
            timestamp=now - 1800,
            id_kodu_qr_zeskanowany="invalid-token-xyz-999",
            id_pracownika_zidentyfikowany=None,
            wynik_weryfikacji_twarzy=None,
            wynik_proby_wejscia=WynikProbyEnum.OdmowaKodNiewazny,
            id_czytnika=1
        )
        db.session.add_all([sample_log_1, sample_log_2])
        db.session.commit()

    return created_records


def main():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    print("[*] Initializing SQLite database schema from admin_panel models...")
    init_db(app)

    print("[*] Generating synthetic employees and 128-D face embeddings...")
    records = seed_data(app)

    print("\n" + "=" * 70)
    print("SUCCESS: Demo environment successfully seeded!")
    print("=" * 70)
    print(f"Database location : {DB_PATH}")
    print(f"Embeddings folder : {FACE_EMBEDDINGS_DIR}\n")
    print("Seeded demo employees:")
    for rec in records:
        print(f"  - [{rec['id']}] {rec['name']}")
        print(f"      QR Token  : {rec['qr_id']}")
        print(f"      Embedding : {os.path.basename(rec['embedding_path'])}")

    print("\n" + "-" * 70)
    print("LEGAL & PRIVACY NOTICE:")
    print("All employee names, identifiers, and 128-D face embeddings generated")
    print("by this script are 100% SYNTHETIC and intended strictly for testing")
    print("and demonstration purposes. No actual biometric or personal data is")
    print("stored or processed.")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
