"""RAG Engine - Hybrid search with FAISS (dense) + BM25 (sparse) + re-ranking."""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)

_embeddings_model = None
_bm25_model = None


def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import os
            from dotenv import load_dotenv

            load_dotenv()

            model_name = config.RAG_MODEL
            device = config.RAG_DEVICE

            hf_token = os.environ.get("HF_TOKEN", "")

            logger.info(f"Loading SentenceTransformer model: {model_name}")
            logger.info(f"HF_TOKEN available: {bool(hf_token)}")

            if hf_token:
                from huggingface_hub import login

                login(token=hf_token)
                logger.info("HuggingFace authenticated")

            _embeddings_model = SentenceTransformer(model_name, device=device)
            logger.info("SentenceTransformer model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load RAG model: {e}")
            _embeddings_model = None
    return _embeddings_model


def get_bm25_model():
    global _bm25_model
    if _bm25_model is None:
        try:
            from rank_bm25 import BM25Okapi

            _bm25_model = BM25Okapi
            logger.info("BM25 model loaded")
        except Exception as e:
            logger.warning(f"Could not load BM25: {e}")
            _bm25_model = None
    return _bm25_model


def tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, remove punctuation, split."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how", "all",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "because", "but", "and", "or", "if", "while", "about", "against",
        "this", "that", "these", "those", "i", "me", "my", "myself", "we",
        "our", "ours", "ourselves", "you", "your", "yours", "yourself",
        "he", "him", "his", "himself", "she", "her", "hers", "it", "its",
        "they", "them", "their", "theirs", "what", "which", "who", "whom",
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
        "al", "en", "con", "sin", "por", "para", "sobre", "tras", "entre",
        "es", "son", "fue", "ser", "estar", "tiene", "tienen", "que", "se",
        "no", "si", "como", "cuando", "donde", "muy", "mas", "pero", "o",
        "y", "lo", "le", "les", "sus", "su", "este", "esta", "estos", "estas",
    }
    return [t for t in tokens if t and t not in stop_words and len(t) > 2]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_length = 0
    chunk_idx = 0

    for line in lines:
        line_length = len(line)
        if current_length + line_length > chunk_size and current_chunk:
            chunk_text_content = "\n".join(current_chunk)
            chunks.append({
                "text": chunk_text_content,
                "chunk_idx": chunk_idx,
                "start_line": chunk_idx,
                "tokens": tokenize(chunk_text_content),
            })
            chunk_idx += 1

            overlap_lines = []
            overlap_length = 0
            for prev_line in reversed(current_chunk):
                if overlap_length + len(prev_line) > overlap:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_length += len(prev_line)
            current_chunk = overlap_lines
            current_length = overlap_length

        current_chunk.append(line)
        current_length += line_length

    if current_chunk:
        chunk_text_content = "\n".join(current_chunk)
        chunks.append({
            "text": chunk_text_content,
            "chunk_idx": chunk_idx,
            "start_line": chunk_idx,
            "tokens": tokenize(chunk_text_content),
        })

    return chunks


class RAGEngine:
    def __init__(self, index_path: Optional[Path] = None, vault_name: Optional[str] = None):
        self.model = None
        self.index = None
        self.bm25 = None
        self.corpus_tokens = []
        self.index_path = index_path or config.VECTOR_INDEX
        self.documents = []
        self.chunks = []
        self.vault_name = vault_name or self._get_active_vault_name()
        self._load_index(self.index_path)

    def _get_active_vault_name(self) -> Optional[str]:
        try:
            from core.vault_manager import get_vault_manager

            active = get_vault_manager().get_active()
            if active:
                return active.get("name")
        except Exception:
            pass
        return None

    def _get_vault_index_path(self, vault_name: str) -> Path:
        safe_name = vault_name.replace(" ", "_").lower()
        return config.DATA_DIR / f"index_{safe_name}.faiss"

    def _load_index(self, index_path: Optional[Path]):
        if index_path and index_path.exists():
            try:
                import faiss

                self.index = faiss.read_index(str(index_path))
                docs_file = index_path.with_suffix(".docs.json")
                if docs_file.exists():
                    self.documents = json.loads(docs_file.read_text())
                chunks_file = index_path.with_suffix(".chunks.json")
                if chunks_file.exists():
                    self.chunks = json.loads(chunks_file.read_text())
                bm25_file = index_path.with_suffix(".bm25.json")
                if bm25_file.exists():
                    bm25_data = json.loads(bm25_file.read_text())
                    self.corpus_tokens = bm25_data.get("tokens", [])
                logger.info(f"Loaded index with {len(self.documents)} documents, {len(self.chunks)} chunks")
            except Exception as e:
                logger.warning(f"Could not load index: {e}")
        elif self.vault_name:
            vault_index = self._get_vault_index_path(self.vault_name)
            if vault_index.exists():
                try:
                    import faiss

                    self.index = faiss.read_index(str(vault_index))
                    docs_file = vault_index.with_suffix(".docs.json")
                    if docs_file.exists():
                        self.documents = json.loads(docs_file.read_text())
                    chunks_file = vault_index.with_suffix(".chunks.json")
                    if chunks_file.exists():
                        self.chunks = json.loads(chunks_file.read_text())
                    bm25_file = vault_index.with_suffix(".bm25.json")
                    if bm25_file.exists():
                        bm25_data = json.loads(bm25_file.read_text())
                        self.corpus_tokens = bm25_data.get("tokens", [])
                    logger.info(
                        f"Loaded vault index: {self.vault_name} with {len(self.documents)} documents"
                    )
                except Exception as e:
                    logger.warning(f"Could not load vault index: {e}")

    def index_directory(self, directory: Path, glob_pattern: str = "*.py"):
        self.model = get_embeddings_model()
        if not self.model:
            return {"error": "RAG model not available"}

        dir_path = Path(directory) if isinstance(directory, str) else directory

        files = list(dir_path.glob(glob_pattern))
        texts = []
        all_chunks = []
        all_tokens = []

        for f in files:
            try:
                content = f.read_text(encoding="utf-8")[:10000]
                texts.append(content)
                file_chunks = chunk_text(content, chunk_size=500, overlap=100)
                for chunk in file_chunks:
                    chunk["source"] = str(f)
                    all_chunks.append(chunk)
                    all_tokens.append(chunk["tokens"])
            except Exception as e:
                logger.warning(f"Could not read {f}: {e}")

        if not texts:
            return {"error": "No files found", "indexed": 0}

        embeddings = self.model.encode(texts, show_progress_bar=False)

        try:
            import faiss

            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(embeddings)
            self.documents = [str(f) for f in files]
            self.chunks = all_chunks
            self.corpus_tokens = all_tokens

            bm25_cls = get_bm25_model()
            if bm25_cls and all_tokens:
                self.bm25 = bm25_cls(all_tokens)

            faiss.write_index(self.index, str(self.index_path))
            docs_file = Path(str(self.index_path).replace(".faiss", ".docs.json"))
            docs_file.write_text(json.dumps(self.documents))
            chunks_file = Path(str(self.index_path).replace(".faiss", ".chunks.json"))
            chunks_file.write_text(json.dumps(all_chunks))
            bm25_file = Path(str(self.index_path).replace(".faiss", ".bm25.json"))
            bm25_file.write_text(json.dumps({"tokens": all_tokens}))

            logger.info(
                f"Indexed {len(texts)} files, {len(all_chunks)} chunks to {self.index_path}"
            )
            return {"indexed": len(texts), "chunks": len(all_chunks), "documents": [str(f) for f in files]}
        except Exception as e:
            logger.error(f"Index error: {e}")
            return {"error": str(e)}

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.model or not self.index:
            return []

        query_tokens = tokenize(query)

        dense_results = self._dense_search(query, top_k * 3)
        sparse_results = self._sparse_search(query_tokens, top_k * 3)

        combined = self._combine_results(dense_results, sparse_results, top_k)

        reranked = self._rerank(query, combined)

        return reranked[:top_k]

    def _dense_search(self, query: str, top_k: int) -> list[dict]:
        try:
            query_embedding = self.model.encode([query])
            distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if 0 <= idx < len(self.documents):
                    results.append({
                        "document": self.documents[idx],
                        "dense_score": 1.0 / (1.0 + float(dist)),
                        "sparse_score": 0.0,
                        "chunk": None,
                    })
            return results
        except Exception as e:
            logger.error(f"Dense search error: {e}")
            return []

    def _sparse_search(self, query_tokens: list[str], top_k: int) -> list[dict]:
        if not self.bm25 or not self.corpus_tokens:
            return []

        try:
            scores = self.bm25.get_scores(query_tokens)
            indexed_scores = [(i, score) for i, score in enumerate(scores) if score > 0]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, score in indexed_scores[:top_k]:
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    results.append({
                        "document": chunk.get("source", "unknown"),
                        "dense_score": 0.0,
                        "sparse_score": float(score),
                        "chunk": chunk.get("text", ""),
                    })
            return results
        except Exception as e:
            logger.error(f"Sparse search error: {e}")
            return []

    def _combine_results(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
        top_k: int,
        alpha: float = 0.6,
    ) -> list[dict]:
        doc_scores = {}

        for r in dense_results:
            doc = r["document"]
            if doc not in doc_scores:
                doc_scores[doc] = {"document": doc, "dense_score": 0.0, "sparse_score": 0.0, "chunk": None}
            doc_scores[doc]["dense_score"] = max(doc_scores[doc]["dense_score"], r["dense_score"])

        for r in sparse_results:
            doc = r["document"]
            if doc not in doc_scores:
                doc_scores[doc] = {"document": doc, "dense_score": 0.0, "sparse_score": 0.0, "chunk": r.get("chunk")}
            doc_scores[doc]["sparse_score"] = max(doc_scores[doc]["sparse_score"], r["sparse_score"])
            if r.get("chunk") and not doc_scores[doc]["chunk"]:
                doc_scores[doc]["chunk"] = r["chunk"]

        for doc in doc_scores:
            d = doc_scores[doc]["dense_score"]
            s = doc_scores[doc]["sparse_score"]
            doc_scores[doc]["combined_score"] = alpha * d + (1 - alpha) * s

        sorted_results = sorted(doc_scores.values(), key=lambda x: x["combined_score"], reverse=True)
        return sorted_results[:top_k]

    def _rerank(self, query: str, results: list[dict], top_k: int = None) -> list[dict]:
        if not results:
            return results

        try:
            from sentence_transformers import CrossEncoder

            cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query, r.get("chunk", r["document"])) for r in results]
            scores = cross_encoder.predict(pairs)

            for i, r in enumerate(results):
                r["rerank_score"] = float(scores[i])

            results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            logger.info(f"Re-ranked {len(results)} results")
        except Exception as e:
            logger.warning(f"Re-ranking failed (using combined scores): {e}")
            results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

        return results[:top_k] if top_k else results
