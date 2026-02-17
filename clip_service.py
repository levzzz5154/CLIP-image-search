import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
import os


class CLIPService:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self.model = None
        self.processor = None

    def set_model(self, model_name: str):
        if model_name != self.model_name:
            self.model_name = model_name
            self.model = None
            self.processor = None

    def load(self):
        if self.model is None:
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.model.eval()
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")

    def get_image_embedding(self, image_path: str) -> torch.Tensor:
        if self.model is None:
            self.load()
        
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        
        return image_features.squeeze().cpu().numpy()

    def get_text_embedding(self, text: str) -> torch.Tensor:
        if self.model is None:
            self.load()
        
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
        
        return text_features.squeeze().cpu().numpy()

    def batch_process_images(self, image_paths: list, progress_callback=None) -> dict:
        if self.model is None:
            self.load()
        
        results = {}
        total = len(image_paths)
        
        for i, img_path in enumerate(image_paths):
            try:
                embedding = self.get_image_embedding(img_path)
                results[img_path] = embedding
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
