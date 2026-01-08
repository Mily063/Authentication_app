import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is on sys.path so `admin_panel` imports resolve when running as a script.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask import Flask
from sqlalchemy.pool import NullPool

from admin_panel.db import db
from admin_panel.models import KodyQR, Pracownicy, StatusKoduEnum

# Avoid importing heavy dlib dependencies during tests by stubbing terminal.face_utils
# before admin_panel.views pulls it in.
if 'terminal' not in sys.modules:
    sys.modules['terminal'] = types.ModuleType('terminal')
if 'terminal.face_utils' not in sys.modules:
    fake_face_utils = types.ModuleType('terminal.face_utils')

    def _placeholder_save_face_embedding(src_path: str, dst_path: str):
        Path(dst_path).touch()
        return dst_path

    fake_face_utils.save_face_embedding = _placeholder_save_face_embedding
    sys.modules['terminal.face_utils'] = fake_face_utils

# Provide a lightweight qrcode stub so admin_panel.views can import without the real package.
if 'qrcode' not in sys.modules:
    sys.modules['qrcode'] = types.SimpleNamespace(make=lambda *args, **kwargs: None)


def create_test_app(db_path: str) -> Flask:
    """Build a Flask app wired to an isolated SQLite DB for tests."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    # NullPool closes connections immediately; avoids locked SQLite files on Windows.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'poolclass': NullPool}
    app.secret_key = 'test-secret-key'
    db.init_app(app)

    with app.app_context():
        # Import here to avoid circular imports during app setup.
        from admin_panel.views import views as views_blueprint
        db.create_all()
        app.register_blueprint(views_blueprint)

    return app


class AdminPanelViewTests(unittest.TestCase):
    def setUp(self):
        # Create a temp directory per test to isolate DB file and artifacts.
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.app = create_test_app(self.db_path)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        # Keep a handle to the engine so we can dispose it in tearDown.
        self.engine = db.engine

    def tearDown(self):
        # Clean up DB session and temp files between tests.
        db.session.close()
        db.session.remove()
        db.drop_all()
        self.engine.dispose()
        self.ctx.pop()
        self.client = None
        self.tmpdir.cleanup()

    @patch('admin_panel.views.save_face_embedding')
    def test_add_employee_creates_record(self, mock_save_embedding):
        """Verify POST /pracownik/dodaj saves embedding path and inserts a Pracownicy row."""
        face_dir = os.path.join(self.tmpdir.name, 'faces')
        os.makedirs(face_dir, exist_ok=True)

        # Make the mock create the destination file that the route passes in.
        def _write_embedding(temp_src, dest_path):
            Path(dest_path).touch()
            return dest_path

        mock_save_embedding.side_effect = _write_embedding

        with patch('admin_panel.views.FACE_EMBEDDINGS_DIR', face_dir):
            # Minimal fake image upload; content is unused because save_face_embedding is mocked.
            data = {
                'imie': 'Jan',
                'nazwisko': 'Kowalski',
                'wizerunek': (io.BytesIO(b'fake-image-bytes'), 'face.jpg'),
            }
            resp = self.client.post('/pracownik/dodaj', data=data, content_type='multipart/form-data', follow_redirects=False)

        # Expect a redirect back to index after successful creation.
        self.assertEqual(resp.status_code, 302)
        employee = Pracownicy.query.filter_by(imie='Jan', nazwisko='Kowalski').first()
        self.assertIsNotNone(employee, 'Employee should be created in the test DB')
        # The view assigns a UUID filename; just assert it lives in FACE_EMBEDDINGS_DIR and exists.
        self.assertTrue(employee.wzorzec_twarzy.startswith(face_dir))
        self.assertEqual(Path(employee.wzorzec_twarzy).suffix, '.npy')
        self.assertTrue(Path(employee.wzorzec_twarzy).exists(), 'Saved embedding file should exist')

    def test_generate_qr_creates_code_entry_and_file(self):
        """Ensure /qr/generuj issues a QR code and persists KodyQR with active status."""
        from admin_panel import views  # Import here to patch module-level constants.

        face_dir = os.path.join(self.tmpdir.name, 'faces')
        os.makedirs(face_dir, exist_ok=True)

        # Seed one employee to select in the form.
        worker = Pracownicy(imie='Anna', nazwisko='Nowak', wzorzec_twarzy='stub.npy')
        db.session.add(worker)
        db.session.commit()

        class DummyQR:
            def save(self, path):
                # Touch the path so send_file can locate it.
                Path(path).touch()

        with patch.object(views, 'FACE_EMBEDDINGS_DIR', face_dir), patch.object(views, 'qrcode') as mock_qrcode:
            mock_qrcode.make.return_value = DummyQR()
            resp = self.client.post(
                '/qr/generuj',
                data={'id_pracownika': str(worker.id_pracownika), 'dni': '3'},
            )

        # Route returns a QR file; expect 200 OK even without following redirects.
        self.assertEqual(resp.status_code, 200)

        # The newly created QR code should be stored with active status.
        qr_entry = KodyQR.query.filter_by(id_pracownika=worker.id_pracownika).first()
        self.assertIsNotNone(qr_entry, 'QR entry should be persisted')
        self.assertEqual(qr_entry.status_kodu, StatusKoduEnum.Aktywny)

        # The QR image file should exist in the patched directory.
        expected_png = Path(face_dir) / f'{qr_entry.id_kodu_qr}.png'
        self.assertTrue(expected_png.exists(), 'QR PNG should be written to FACE_EMBEDDINGS_DIR')


if __name__ == '__main__':
    unittest.main()
