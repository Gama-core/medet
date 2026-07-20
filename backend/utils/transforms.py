"""Transformation d'image partagee par les deux modeles EfficientNet (binaire + type)."""

from torchvision import transforms

classification_transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)