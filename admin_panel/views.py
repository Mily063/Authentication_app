from flask import render_template, request, redirect, url_for, flash, send_file
from .db import db
from .models import Pracownicy, KodyQR, RejestrWejsc, StatusKoduEnum, WynikProbyEnum
from config import FACE_EMBEDDINGS_DIR
import os
import uuid
import time
import qrcode

from werkzeug.utils import secure_filename
from terminal.face_utils import save_face_embedding

from flask import Blueprint
views = Blueprint('views', __name__)

# Pracownicy CRUD
@views.route('/')
def index():
    pracownicy = db.session.query(Pracownicy).all()
    return render_template('index.html', pracownicy=pracownicy)

@views.route('/pracownik/dodaj', methods=['GET', 'POST'])
def dodaj_pracownika():
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        file = request.files['wizerunek']
        if not file:
            flash('Brak pliku ze zdjęciem!')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        temp_path = os.path.join(FACE_EMBEDDINGS_DIR, 'temp_' + filename)
        file.save(temp_path)
        embedding_path = os.path.join(FACE_EMBEDDINGS_DIR, f'{uuid.uuid4()}.npy')
        try:
            save_face_embedding(temp_path, embedding_path)
        except Exception as e:
            os.remove(temp_path)
            flash(f'Błąd przetwarzania zdjęcia: {e}')
            return redirect(request.url)
        os.remove(temp_path)
        p = Pracownicy(imie=imie, nazwisko=nazwisko, wzorzec_twarzy=embedding_path)
        db.session.add(p)
        db.session.commit()
        flash('Dodano pracownika!')
        return redirect(url_for('views.index'))
    return render_template('dodaj_pracownika.html')

@views.route('/pracownik/edytuj/<int:id>', methods=['GET', 'POST'])
def edytuj_pracownika(id):
    p = db.session.query(Pracownicy).get(id)
    if request.method == 'POST':
        p.imie = request.form['imie']
        p.nazwisko = request.form['nazwisko']
        db.session.commit()
        flash('Zaktualizowano dane!')
        return redirect(url_for('views.index'))
    return render_template('edytuj_pracownika.html', pracownik=p)

@views.route('/pracownik/status/<int:id>')
def zmien_status_pracownika(id):
    p = db.session.query(Pracownicy).get(id)
    p.status_uprawnien = not p.status_uprawnien
    db.session.commit()
    flash('Zmieniono status uprawnień!')
    return redirect(url_for('views.index'))

# Generowanie QR
@views.route('/qr/generuj', methods=['GET', 'POST'])
def generuj_qr():
    pracownicy = Pracownicy.query.all()
    if request.method == 'POST':
        id_pracownika = int(request.form['id_pracownika'])
        dni = int(request.form['dni'])
        kod_id = str(uuid.uuid4())
        data_waznosci = int(time.time()) + dni * 86400
        k = KodyQR(id_kodu_qr=kod_id, id_pracownika=id_pracownika, data_waznosci=data_waznosci, status_kodu=StatusKoduEnum.Aktywny)
        db.session.add(k)
        db.session.commit()
        qr = qrcode.make(kod_id)
        qr_path = os.path.join(FACE_EMBEDDINGS_DIR, f'{kod_id}.png')
        qr.save(qr_path)
        return send_file(qr_path, as_attachment=True)
    return render_template('generuj_qr.html', pracownicy=pracownicy)

# Raporty
@views.route('/raport', methods=['GET'])
def raport():
    filtr = request.args.get('filtr', None)
    pracownik_id = request.args.get('pracownik_id', None)
    query = RejestrWejsc.query
    if pracownik_id:
        query = query.filter_by(id_pracownika_zidentyfikowany=pracownik_id)
    if filtr:
        query = query.filter_by(wynik_proby_wejscia=filtr)
    entries = query.order_by(RejestrWejsc.timestamp.desc()).all()
    return render_template('raport.html', entries=entries)

@views.route('/raport/niepoprawne')
def raport_niepoprawne():
    niepoprawne = [WynikProbyEnum.OdmowaNiezgodnosc, WynikProbyEnum.OdmowaBrakUprawnien, WynikProbyEnum.OdmowaKodNiewazny]
    entries = RejestrWejsc.query.filter(RejestrWejsc.wynik_proby_wejscia.in_(niepoprawne)).order_by(RejestrWejsc.timestamp.desc()).all()
    return render_template('raport_niepoprawne.html', entries=entries)

@views.route('/demo')
def demo():
    # Dodaj przykładowych pracowników jeśli nie istnieją
    if not db.session.query(Pracownicy).first():
        p1 = Pracownicy(imie='Jan', nazwisko='Kowalski', wzorzec_twarzy='demo1.npy')
        p2 = Pracownicy(imie='Anna', nazwisko='Nowak', wzorzec_twarzy='demo2.npy', status_uprawnien=False)
        db.session.add_all([p1, p2])
        db.session.commit()
        # Dodaj przykładowe kody QR
        import uuid, time
        k1 = KodyQR(id_kodu_qr=str(uuid.uuid4()), id_pracownika=p1.id_pracownika, data_waznosci=int(time.time())+86400, status_kodu=StatusKoduEnum.Aktywny)
        k2 = KodyQR(id_kodu_qr=str(uuid.uuid4()), id_pracownika=p2.id_pracownika, data_waznosci=int(time.time())+86400, status_kodu=StatusKoduEnum.Zablokowany)
        db.session.add_all([k1, k2])
        db.session.commit()
        flash('Dodano przykładowych pracowników i kody QR!')
    else:
        flash('Przykładowi pracownicy już istnieją!')
    return redirect(url_for('views.index'))
