import numpy as np
import face_recognition
import os
import cv2

def save_face_embedding(image_path, save_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        raise ValueError('Brak twarzy na zdjęciu!')
    np.save(save_path, encodings[0])
    return save_path

def load_face_embedding(embedding_path):
    return np.load(embedding_path)

def compare_faces(known_embedding_path, unknown_image, tolerance=0.6):
    known_embedding = load_face_embedding(known_embedding_path)
    unknown_encodings = face_recognition.face_encodings(unknown_image)
    if not unknown_encodings:
        return False, None
    distance = np.linalg.norm(known_embedding - unknown_encodings[0])
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
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_frame)
        if encodings:
            embeddings.append(encodings[0])
        frame_count += 1
    cap.release()
    if not embeddings:
        raise ValueError('Brak twarzy na nagraniu!')
    mean_embedding = np.mean(embeddings, axis=0)
    np.save(save_path, mean_embedding)
    return save_path
