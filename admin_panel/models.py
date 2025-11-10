from admin_panel.db import db
from sqlalchemy import Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class StatusKoduEnum(str, enum.Enum):
    Aktywny = "Aktywny"
    Zablokowany = "Zablokowany"

class WynikProbyEnum(str, enum.Enum):
    Zezwolono = "Zezwolono"
    OdmowaNiezgodnosc = "Odmowa - niezgodność"
    OdmowaBrakUprawnien = "Odmowa - brak uprawnień"
    OdmowaKodNiewazny = "Odmowa - kod nieważny"

class Pracownicy(db.Model):
    __tablename__ = 'pracownicy'
    id_pracownika = db.Column(Integer, primary_key=True, unique=True)
    imie = db.Column(String, nullable=False)
    nazwisko = db.Column(String, nullable=False)
    wzorzec_twarzy = db.Column(String, nullable=False)
    status_uprawnien = db.Column(Boolean, default=True)
    kody_qr = db.relationship('KodyQR', back_populates='pracownik')

class KodyQR(db.Model):
    __tablename__ = 'kodyqr'
    id_kodu_qr = db.Column(String, primary_key=True, unique=True)
    id_pracownika = db.Column(Integer, db.ForeignKey('pracownicy.id_pracownika'))
    data_waznosci = db.Column(Integer, nullable=False)
    status_kodu = db.Column(Enum(StatusKoduEnum), nullable=False)
    pracownik = db.relationship('Pracownicy', back_populates='kody_qr')

class RejestrWejsc(db.Model):
    __tablename__ = 'rejestrwejsc'
    id_wpisu = db.Column(Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(Integer, nullable=False)
    id_kodu_qr_zeskanowany = db.Column(String, nullable=False)
    id_pracownika_zidentyfikowany = db.Column(Integer, nullable=True)
    wynik_weryfikacji_twarzy = db.Column(String, nullable=True)
    wynik_proby_wejscia = db.Column(Enum(WynikProbyEnum), nullable=False)
    id_czytnika = db.Column(Integer, default=1)
