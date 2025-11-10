import os

# Ścieżki
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'database.db')
FACE_EMBEDDINGS_DIR = os.path.join(BASE_DIR, 'data', 'face_embeddings')

# Próg rozpoznawania twarzy (dla face_recognition)
FACE_MATCH_TOLERANCE = 0.6  # odpowiada ok. 90% pewności

# Inne ustawienia
READER_ID = 1
REPORT_RETENTION_MONTHS = 6

