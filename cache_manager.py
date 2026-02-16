import json
import os
import numpy as np
import hashlib
from typing import Dict, List, Optional


class CacheManager:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.embeddings_dir = os.path.join(cache_dir, "embeddings")
        self.manifest_path = os.path.join(cache_dir, "manifest.json")
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.embeddings_dir, exist_ok=True)

    def _get_embedding_filename(self, image_path: str) -> str:
        path_hash = hashlib.md5(image_path.encode()).hexdigest()
        return f"{path_hash}.npy"

    def _load_manifest(self) -> Dict:
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_manifest(self, manifest: Dict):
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    def get_embedding_path(self, image_path: str) -> Optional[str]:
        manifest = self._load_manifest()
        if image_path in manifest:
            emb_path = os.path.join(self.embeddings_dir, manifest[image_path])
            if os.path.exists(emb_path):
                return emb_path
        return None

    def has_embedding(self, image_path: str) -> bool:
        return self.get_embedding_path(image_path) is not None

    def save_embedding(self, image_path: str, embedding: np.ndarray):
        manifest = self._load_manifest()
        
        filename = self._get_embedding_filename(image_path)
        emb_path = os.path.join(self.embeddings_dir, filename)
        
        np.save(emb_path, embedding)
        
        manifest[image_path] = filename
        self._save_manifest(manifest)

    def load_embedding(self, image_path: str) -> Optional[np.ndarray]:
        emb_path = self.get_embedding_path(image_path)
        if emb_path:
            return np.load(emb_path)
        return None

    def get_all_embeddings(self) -> Dict[str, np.ndarray]:
        manifest = self._load_manifest()
        embeddings = {}
        
        for img_path, filename in manifest.items():
            emb_path = os.path.join(self.embeddings_dir, filename)
            if os.path.exists(emb_path):
                embeddings[img_path] = np.load(emb_path)
        
        return embeddings

    def get_all_image_paths(self) -> List[str]:
        manifest = self._load_manifest()
        return list(manifest.keys())

    def remove_embedding(self, image_path: str):
        manifest = self._load_manifest()
        
        if image_path in manifest:
            emb_path = os.path.join(self.embeddings_dir, manifest[image_path])
            if os.path.exists(emb_path):
                os.remove(emb_path)
            del manifest[image_path]
            self._save_manifest(manifest)

    def clear_all(self):
        if os.path.exists(self.embeddings_dir):
            for f in os.listdir(self.embeddings_dir):
                os.remove(os.path.join(self.embeddings_dir, f))
        self._save_manifest({})
