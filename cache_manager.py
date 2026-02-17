import json
import os
import numpy as np
import hashlib
from typing import Dict, List, Optional


class CacheManager:
    def __init__(self, cache_dir: str = "cache", model_name: str = "clip-vit-base-patch32"):
        self.cache_dir = cache_dir
        self.base_cache_dir = cache_dir
        self.model_name = model_name
        self._migrate_if_needed()
        self._set_model_dir()

    def _migrate_if_needed(self):
        old_manifest = os.path.join(self.cache_dir, "manifest.json")
        if os.path.exists(old_manifest):
            model_dir = os.path.join(self.cache_dir, self.model_name)
            os.makedirs(model_dir, exist_ok=True)
            old_emb_dir = os.path.join(self.cache_dir, "embeddings")
            new_emb_dir = os.path.join(model_dir, "embeddings")
            os.makedirs(new_emb_dir, exist_ok=True)
            if os.path.exists(old_emb_dir):
                for f in os.listdir(old_emb_dir):
                    src = os.path.join(old_emb_dir, f)
                    dst = os.path.join(new_emb_dir, f)
                    if not os.path.exists(dst):
                        os.rename(src, dst)
            old_manifest_new = os.path.join(model_dir, "manifest.json")
            if not os.path.exists(old_manifest_new):
                os.rename(old_manifest, old_manifest_new)

    def _set_model_dir(self):
        self.model_cache_dir = os.path.join(self.base_cache_dir, self.model_name)
        self.embeddings_dir = os.path.join(self.model_cache_dir, "embeddings")
        self.manifest_path = os.path.join(self.model_cache_dir, "manifest.json")
        os.makedirs(self.embeddings_dir, exist_ok=True)

    def set_model(self, model_name: str):
        if model_name != self.model_name:
            self.model_name = model_name
            self._set_model_dir()

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

    def get_stats(self) -> dict:
        manifest = self._load_manifest()
        image_count = len(manifest)
        
        total_size = 0
        if os.path.exists(self.embeddings_dir):
            for f in os.listdir(self.embeddings_dir):
                fpath = os.path.join(self.embeddings_dir, f)
                if os.path.isfile(fpath):
                    total_size += os.path.getsize(fpath)
        
        folders = set()
        for img_path in manifest.keys():
            folders.add(os.path.dirname(img_path))
        
        return {
            "image_count": image_count,
            "cache_size_mb": total_size / (1024 * 1024),
            "folders": sorted(folders)
        }
