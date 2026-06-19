# Medical Detection assistant
The current project aims at providing a mobile application that uses the camera to help practicians with the detection of some anomalies in medical images.

## technology
The project uses the google techstack based on Flutter (+ TensorFlow/keras for classification)
The project can embed a light model for instant and offline classification  
The project can send images to a more capable hosted model

## classification model
There are two types of models that can be trained 
- Embedded localization and classification using yolo (ligh version)
- Hosted classification model (based on Swin Transformer, Vision Transformer, EfficientNet or ... )
The training will be based on :
- Database images provided by the medical team
- Other public images reviewed by the medical team
- Augmented images 

## the Polyps use case
A polyp is an abnormal growth of tissue that projects from the lining of a mucous membrane. There are many benefits in studying plolyps :
- polyps can be found in many tissues  (colon, stomach, nose, uterus ...) 
- Its a well documented subject with available image databases
- It can be ganeralized to other abnormalities
- The detection can indicate treatments that has life changing impacts on patients (prevention of obstructions and cancers)
