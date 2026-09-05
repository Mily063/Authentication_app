# Dlib Pre-trained Models

This directory holds the pre-trained neural network weights required by the terminal and facial recognition modules (`terminal/face_utils.py` and `terminal/main_terminal.py`).

Due to large binary file sizes (~116 MB total) and upstream licensing restrictions, these models are not tracked in this repository and must be downloaded before running face recognition.

---

## Required Models

1. **`shape_predictor_68_face_landmarks.dat`** (~99.7 MB uncompressed)
   - 68-point facial landmark detector used for face localization and alignment.
2. **`dlib_face_recognition_resnet_model_v1.dat`** (~22.5 MB uncompressed)
   - ResNet-34 29-layer deep convolutional network mapping aligned face images into 128-dimensional embedding vectors.

---

## Download Instructions

You can download and extract both models using either `curl` or `wget` and `bunzip2`.

### Using `curl`

Run the following commands from the repository root:

```bash
mkdir -p models
cd models

# Download archives
curl -L -O https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
curl -L -O https://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2

# Extract archives
bunzip2 -k shape_predictor_68_face_landmarks.dat.bz2
bunzip2 -k dlib_face_recognition_resnet_model_v1.dat.bz2

cd ..
```

### Using `wget`

```bash
mkdir -p models
cd models

# Download archives
wget https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
wget https://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2

# Extract archives
bunzip2 -k shape_predictor_68_face_landmarks.dat.bz2
bunzip2 -k dlib_face_recognition_resnet_model_v1.dat.bz2

cd ..
```

*(Note: The `-k` flag preserves the `.bz2` archive after decompression. You may remove the `.bz2` files once extracted).*

---

## License note

The model `shape_predictor_68_face_landmarks.dat` was trained on the iBUG 300-W dataset. The creator of dlib distributes this model with a restriction to non-commercial research and educational use only, adhering to the original dataset terms. For this reason, the model cannot be bundled or redistributed directly in the git repository.

For additional information on the license and training data, refer to:
- [iBUG 300-W Dataset Page](https://ibug.doc.ic.ac.uk/resources/300-W/)
- [dlib C++ Library Models](https://github.com/davisking/dlib-models)
- [dlib Official Documentation](http://dlib.net/)
