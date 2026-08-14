"""Semantic retrieval over the NYSC corpus."""
import hashlib
import os
import numpy as np
from sentence_transformers import SentenceTransformer

from app.preprocess import build_vocab, correct_typos, normalize

MODEL_NAME = "all-MiniLM-L6-v2"
CONFIDENCE_LOW = 0.45              # below this: refuse
CONFIDENCE_HIGH = 0.60             # at/above this: answer directly; between: hedge
CACHE_PATH = "data/embeddings_cache.npz"


class Retriever:
    def __init__(self, docs: list[dict], use_cache: bool = True):
        self.docs = docs
        self.model = SentenceTransformer(MODEL_NAME)
        self.vocab = build_vocab(docs)
        texts = [d.get("embed_text", d["text"]) for d in docs]
        corpus_hash = self._corpus_hash(texts)

        if use_cache and os.path.exists(CACHE_PATH):
            cached = np.load(CACHE_PATH, allow_pickle=False)
            if cached["hash"].item() == corpus_hash:    # corpus unchanged → reuse
                self.embeddings = cached["embeddings"]
            else:
                self.embeddings = self._encode_and_cache(texts, corpus_hash)
        else:
            self.embeddings = self._encode_and_cache(texts, corpus_hash)

    @staticmethod
    def _corpus_hash(texts) -> str:
        h = hashlib.sha256()
        for t in texts:
            h.update(t.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def _encode_and_cache(self, texts, corpus_hash):
        emb = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        np.savez(CACHE_PATH, embeddings=emb, hash=corpus_hash)
        return emb

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.docs:
            return []
        query = correct_typos(normalize(query), self.vocab)
        q_vec = self.model.encode([query], normalize_embeddings=True)[0]
        scores = self.embeddings @ q_vec
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [{**self.docs[i], "score": float(scores[i])} for i in top_idx]