import numpy as np
from typing import List, Tuple, Dict
from clip_service import CLIPService
from cache_manager import CacheManager


class SearchEngine:
    def __init__(self, cache_manager: CacheManager, clip_service: CLIPService):
        self.cache_manager = cache_manager
        self.clip_service = clip_service

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        text_embedding = self.clip_service.get_text_embedding(query)
        
        embeddings = self.cache_manager.get_all_embeddings()
        
        if not embeddings:
            return []
        
        results = []
        
        for img_path, img_embedding in embeddings.items():
            similarity = self._cosine_similarity(text_embedding, img_embedding)
            results.append((img_path, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        a = a / np.linalg.norm(a)
        b = b / np.linalg.norm(b)
        return float(np.dot(a, b))
