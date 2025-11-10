import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import pandas as pd
import uuid
import time
from models import Pracownicy, KodyQR, RejestrWejsc, StatusKoduEnum, WynikProbyEnum
from db import db
from config import DB_PATH, FACE_EMBEDDINGS_DIR
from terminal.face_utils import save_face_embedding_from_video
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import qrcode

# Ustawienia bazy
engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)
session = Session()

st.set_page_config(page_title="System Kontroli Dostępu", layout="wide")
st.title("System Kontroli Dostępu - Panel Administracyjny")

menu = ["Pracownicy", "Dodaj pracownika", "Generuj QR", "Raport", "Raport niepoprawne"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Pracownicy":
    st.header("Lista pracowników")
    pracownicy = session.query(Pracownicy).all()
    df = pd.DataFrame([
        {"ID": p.id_pracownika, "Imię": p.imie, "Nazwisko": p.nazwisko, "Status": "Aktywny" if p.status_uprawnien else "Zablokowany"}
        for p in pracownicy
    ])
    st.dataframe(df)
    st.subheader("Usuń pracownika")
    pracownik_id = st.selectbox("Wybierz pracownika do usunięcia", [p.id_pracownika for p in pracownicy])
    if st.button("Usuń pracownika"):
        pracownik = session.query(Pracownicy).get(pracownik_id)
        session.delete(pracownik)
        session.commit()
        st.success("Pracownik usunięty!")
        st.rerun()

if choice == "Dodaj pracownika":
    st.header("Dodaj nowego pracownika")
    imie = st.text_input("Imię")
    nazwisko = st.text_input("Nazwisko")
    video_file = st.file_uploader("Nagranie wideo (mp4/webm)", type=["mp4", "webm"])
    if st.button("Dodaj pracownika"):
        if not (imie and nazwisko and video_file):
            st.error("Wszystkie pola są wymagane!")
        else:
            temp_path = os.path.join(FACE_EMBEDDINGS_DIR, f'temp_{uuid.uuid4()}.mp4')
            with open(temp_path, 'wb') as f:
                f.write(video_file.read())
            embedding_path = os.path.join(FACE_EMBEDDINGS_DIR, f'{uuid.uuid4()}.npy')
            try:
                save_face_embedding_from_video(temp_path, embedding_path)
                p = Pracownicy(imie=imie, nazwisko=nazwisko, wzorzec_twarzy=embedding_path)
                session.add(p)
                session.commit()
                st.success("Dodano pracownika!")
            except Exception as e:
                st.error(f"Błąd przetwarzania wideo: {e}")
            os.remove(temp_path)

if choice == "Generuj QR":
    st.header("Generuj przepustkę QR")
    pracownicy = session.query(Pracownicy).all()
    pracownik_id = st.selectbox("Wybierz pracownika", [p.id_pracownika for p in pracownicy])
    dni = st.number_input("Ważność (dni)", min_value=1, max_value=365, value=30)
    if st.button("Generuj QR"):
        kod_id = str(uuid.uuid4())
        data_waznosci = int(time.time()) + dni * 86400
        k = KodyQR(id_kodu_qr=kod_id, id_pracownika=pracownik_id, data_waznosci=data_waznosci, status_kodu=StatusKoduEnum.Aktywny)
        session.add(k)
        session.commit()
        qr = qrcode.make(kod_id)
        qr_path = os.path.join(FACE_EMBEDDINGS_DIR, f'{kod_id}.png')
        qr.save(qr_path)
        st.image(qr_path, caption="Kod QR do wydruku")

if choice == "Raport":
    st.header("Raport wejść")
    entries = session.query(RejestrWejsc).order_by(RejestrWejsc.timestamp.desc()).all()
    df = pd.DataFrame([
        {"Czas": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.timestamp)),
         "ID QR": e.id_kodu_qr_zeskanowany,
         "ID Pracownika": e.id_pracownika_zidentyfikowany,
         "Wynik twarzy": e.wynik_weryfikacji_twarzy,
         "Wynik próby": e.wynik_proby_wejscia,
         "Czytnik": e.id_czytnika}
        for e in entries
    ])
    st.dataframe(df)

if choice == "Raport niepoprawne":
    st.header("Raport prób niepoprawnych")
    niepoprawne = [WynikProbyEnum.OdmowaNiezgodnosc, WynikProbyEnum.OdmowaBrakUprawnien, WynikProbyEnum.OdmowaKodNiewazny]
    entries = session.query(RejestrWejsc).filter(RejestrWejsc.wynik_proby_wejscia.in_(niepoprawne)).order_by(RejestrWejsc.timestamp.desc()).all()
    df = pd.DataFrame([
        {"Czas": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.timestamp)),
         "ID QR": e.id_kodu_qr_zeskanowany,
         "ID Pracownika": e.id_pracownika_zidentyfikowany,
         "Wynik twarzy": e.wynik_weryfikacji_twarzy,
         "Wynik próby": e.wynik_proby_wejscia,
         "Czytnik": e.id_czytnika}
        for e in entries
    ])
    st.dataframe(df)
