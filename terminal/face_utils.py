import numpy as np
import dlib
import cv2
import os
from config import BASE_DIR

# Load the dlib face detector and face recognition model
face_detector = dlib.get_frontal_face_detector()
face_rec_model = dlib.face_recognition_model_v1(os.path.join(BASE_DIR, 'models', 'dlib_face_recognition_resnet_model_v1.dat'))
shape_predictor = dlib.shape_predictor(os.path.join(BASE_DIR, 'models', 'shape_predictor_68_face_landmarks.dat'))

def save_face_embedding(image_path, save_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Image not found or invalid format!")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_detector(gray)
    if not faces:
        raise ValueError('Brak twarzy na zdjęciu!')

    # Use the first detected face
    shape = shape_predictor(image, faces[0])
    face_descriptor = np.array(face_rec_model.compute_face_descriptor(image, shape))
    np.save(save_path, face_descriptor)
    return save_path

def load_face_embedding(embedding_path):
    return np.load(embedding_path)

def compare_faces(known_embedding_path, unknown_image, tolerance=0.6):
    known_embedding = load_face_embedding(known_embedding_path)
    gray = cv2.cvtColor(unknown_image, cv2.COLOR_BGR2GRAY)
    faces = face_detector(gray)
    if not faces:
        return False, None

    # Use the first detected face
    shape = shape_predictor(unknown_image, faces[0])
    unknown_embedding = np.array(face_rec_model.compute_face_descriptor(unknown_image, shape))
    distance = np.linalg.norm(known_embedding - unknown_embedding)
    match = distance < tolerance
    return match, float(distance)

def save_face_embedding_from_video(video_path, save_path, max_frames=20):
    cap = cv2.VideoCapture(video_path)
    embeddings = []
    frame_count = 0
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector(gray)
        if faces:
            shape = shape_predictor(frame, faces[0])
            face_descriptor = np.array(face_rec_model.compute_face_descriptor(frame, shape))
            embeddings.append(face_descriptor)
        frame_count += 1
    cap.release()
    if not embeddings:
        raise ValueError('Brak twarzy na nagraniu!')
    mean_embedding = np.mean(embeddings, axis=0)
    np.save(save_path, mean_embedding)
    return save_path
