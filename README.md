# detection-assistant
The current project aims at providing a mobile application that uses the camera to activate detection of some anomalies in medical images.

## technology
The project uses the google techstack based on Flutter (+ TensorFlow/keras for classification)
The project can embed a light model for instant and offline classification  
The project can send images to a more capable hosted model

## classification model
There are two types of models that can be trained 
- Embedded localization and classification using yolo (ligh version)
- Hosted classification model (based on EfficientNet)
The training will be based on :
- Database images provided by the medical team
- Other public images reviewed by the medical team
- Augmented images 
