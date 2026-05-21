"""H-Mem Hybrid Retriever - Combines tree and graph for memory retrieval."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Self, Any

import config

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    H-Mem hybrid retrieval combining tree and graph structures.
    
    Retrieval steps:
    1. Retrieval Planning - Decompose query, infer temporal scope
    2. Evidence Retrieval - Graph expansion + Tree bottom-up search
    3. Ranking - Combine semantic, temporal, and robustness scores
    """
    
    DEFAULT_WEIGHTS = {
        "theta1_semantic": 0.4,
        "theta2_temporal": 0.3,
        "theta3_robustness": 0.3,
        "lambda_temporal": 0.5,
    }
    
    def __init__(self, vault_name: Optional[str] = None) -> None:
        self.vault_name = vault_name
        self.memory_tree = None
        self.entity_graph = None
        self.llm_router = None
        self.weights = self.DEFAULT_WEIGHTS.copy()
    
    def _get_tree(self) -> Any:
        if self.memory_tree is None:
            from core.memory_tree import MemoryTree
            self.memory_tree = MemoryTree(vault_name=self.vault_name)
        return self.memory_tree
    
    def _get_graph(self) -> Any:
        if self.entity_graph is None:
            from core.entity_graph import EntityGraph
            self.entity_graph = EntityGraph(vault_name=self.vault_name)
        return self.entity_graph
    
    def _get_llm(self) -> Any:
        if self.llm_router is None:
            from core.llm_router import LLMRouter
            self.llm_router = LLMRouter()
        return self.llm_router
    
    def retrieve(
        self,
        query: str,
        time_range: tuple = None,
        scope: str = "mixed",
        max_results: int = 10
    ) -> dict:
        """
        Main retrieval method following H-Mem 3-step approach.
        
        Returns dict with:
        - sub_queries: list of decomposed queries
        - entities: seed and expanded entities
        - evidence: ranked memory evidence
        - final_answer: synthesized answer
        """
        plan = self._plan_retrieval(query)
        
        tree_results = []
        graph_entities = []
        
        for sq in plan["sub_queries"]:
            sq_scope = sq.get("scope", scope)
            sq_time_range = sq.get("time_range") or time_range
            
            tree_res = self._retrieve_tree(sq["query"], sq_scope, sq_time_range, max_results // 2)
            tree_results.extend(tree_res)
            
            seed_ents = sq.get("entities", [])
            if seed_ents:
                expanded = self._get_graph().expand(seed_ents, hops=2)
                graph_entities.extend(expanded)
        
        if graph_entities:
            for ent_data in graph_entities:
                ent = ent_data["entity"]
                self._get_tree().insert(
                    content=f"Entidad: {ent['name']} - {ent.get('profile', '')}",
                    metadata={"source": "entity_graph", "entity_type": ent.get("entity_type")}
                )
        
        ranked = self._rank_evidence(tree_results, query)
        
        return {
            "plan": plan,
            "tree_results": tree_results[:max_results],
            "graph_entities": graph_entities[:20],
            "ranked_evidence": ranked[:max_results],
            "query_time": datetime.now().isoformat(),
        }
    
    def _plan_retrieval(self, query: str) -> dict:
        """Step 1: Decompose query and generate retrieval plan."""
        llm = self._get_llm()
        
        prompt = f"""Analiza la siguiente query y genera un plan de recuperación:

Query: {query}

Devuelve en JSON:
{{
  "sub_queries": [
    {{
      "query": "sub-query text",
      "scope": "short|long|mixed",
      "time_range": ["YYYY-MM-DD", "YYYY-MM-DD"] o null,
      "entities": ["entity1", "entity2"] o []
    }}
  ],
  "temporal_hints": ["hint1", "hint2"] o [],
  "focus": "breve descripción del foco de la query"
}}

Reglas:
- scope "short" = memoria reciente (días), "long" = memoria histórica (meses+), "mixed" = ambas
- time_range null = cualquier tiempo, o especifica rango con fechas
- entities = personas, lugares, conceptos mencionados en la sub-query

Solo devuelve JSON válido:"""
        
        try:
            result = llm.generate(prompt)
            
            result = result.strip()
            if result.startswith("```"):
                lines = result.split("\n")[1:]
                result = "\n".join(lines)
                if result.endswith("```"):
                    result = result[:-3]
            
            plan = json.loads(result)
            
            if "sub_queries" not in plan:
                plan["sub_queries"] = [{
                    "query": query,
                    "scope": scope if "scope" in dir() else "mixed",
                    "time_range": None,
                    "entities": []
                }]
            
            return plan
            
        except json.JSONDecodeError:
            logger.warning("Query planning JSON parse failed, using fallback")
            return {
                "sub_queries": [{
                    "query": query,
                    "scope": "mixed",
                    "time_range": None,
                    "entities": []
                }],
                "temporal_hints": [],
                "focus": query[:100]
            }
        except Exception as e:
            logger.warning(f"Query planning failed: {e}")
            return {
                "sub_queries": [{
                    "query": query,
                    "scope": "mixed",
                    "time_range": None,
                    "entities": []
                }],
                "temporal_hints": [],
                "focus": query[:100]
            }
    
    def _retrieve_tree(
        self,
        query: str,
        scope: str,
        time_range: tuple,
        limit: int
    ) -> list[dict]:
        """Step 2: Retrieve from tree structure."""
        tree = self._get_tree()
        
        if time_range:
            return tree.query(query, time_range=time_range, scope=scope, limit=limit)
        else:
            now = datetime.now()
            
            if scope == "short":
                start = (now - timedelta(days=7)).isoformat()
                end = now.isoformat()
            elif scope == "long":
                start = (now - timedelta(days=365)).isoformat()
                end = (now - timedelta(days=30)).isoformat()
            else:
                start = (now - timedelta(days=90)).isoformat()
                end = now.isoformat()
            
            return tree.query(query, time_range=(start, end), scope=scope, limit=limit)
    
    def _rank_evidence(self, results: list[dict], query: str) -> list[dict]:
        """Step 3: Rank evidence by combined scores."""
        theta1 = self.weights["theta1_semantic"]
        theta2 = self.weights["theta2_temporal"]
        theta3 = self.weights["theta3_robustness"]
        
        for r in results:
            semantic = r.get("semantic_sim", 0.5)
            temporal = r.get("temporal_relevance", 0.5)
            robustness = r.get("robustness", 0.5)
            
            r["combined_score"] = (
                theta1 * semantic +
                theta2 * temporal +
                theta3 * robustness
            )
        
        seen = set()
        unique = []
        for r in results:
            node_id = r.get("node", {}).get("node_id", "")
            if node_id and node_id not in seen:
                seen.add(node_id)
                unique.append(r)
        
        return sorted(unique, key=lambda x: x["combined_score"], reverse=True)
    
    def answer(
        self,
        query: str,
        context: str = None,
        max_context_len: int = 4000
    ) -> dict:
        """
        Full retrieval + answer generation.
        
        Args:
            query: User question
            context: Additional context (optional)
            max_context_len: Max characters for evidence context
            
        Returns:
            {"answer": str, "evidence": list, "sources": list}
        """
        retrieval = self.retrieve(query, max_results=10)
        
        evidence_texts = []
        sources = []
        
        for ev in retrieval["ranked_evidence"][:5]:
            node = ev.get("node", {})
            content = (node.get("summary") or node.get("content", ""))[:500]
            if content and content not in evidence_texts:
                evidence_texts.append(content)
                sources.append({
                    "type": f"L{node.get('level', 0)}",
                    "timestamp": node.get("timestamp", ""),
                    "score": ev.get("combined_score", 0),
                })
        
        if context:
            evidence_texts.insert(0, f"Contexto adicional: {context}")
        
        evidence_combined = "\n---\n".join(evidence_texts)[:max_context_len]
        
        for ent in retrieval.get("graph_entities", [])[:3]:
            ent_name = ent["entity"]["name"]
            ent_profile = ent["entity"].get("profile", "")[:200]
            if ent_profile:
                evidence_combined += f"\n\n[Entidad: {ent_name}] {ent_profile}"
        
        llm = self._get_llm()
        
        prompt = f"""Basándote en la siguiente evidencia del sistema de memoria, responde la pregunta.
Si la evidencia no es suficiente para responder, indícalo claramente.

EVIDENCIA:
{evidence_combined}

PREGUNTA: {query}

RESPUESTA:"""
        
        try:
            answer = llm.generate(prompt)
            
            return {
                "answer": answer,
                "evidence": evidence_texts,
                "sources": sources,
                "entities": [e["entity"]["name"] for e in retrieval.get("graph_entities", [])[:5]],
                "plan": retrieval.get("plan", {}),
            }
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return {
                "answer": "Error al generar respuesta.",
                "evidence": evidence_texts,
                "sources": sources,
                "error": str(e),
            }
    
    def ingest_memory(
        self,
        content: str,
        metadata: dict = None,
        auto_extract_entities: bool = True
    ) -> dict:
        """
        Ingest new memory fragment into the hybrid system.
        
        1. Insert into memory tree
        2. Optionally extract and link entities to graph
        """
        tree = self._get_tree()
        
        node = tree.insert(content, metadata=metadata)
        
        graph_result = {"entities_extracted": 0}
        
        if auto_extract_entities and len(content) > 100:
            graph = self._get_graph()
            graph_result = graph.ingest_with_entities(
                content=content,
                source=metadata.get("source", "manual") if metadata else "manual",
                content_type=metadata.get("type", "memory") if metadata else "memory"
            )
        
        return {
            "tree_node_id": node.get("node_id"),
            "tree_level": node.get("level"),
            "graph_ingest": graph_result,
        }
    
    def get_memory_context(self, query: str, max_len: int = 2000) -> str:
        """
        Get memory context for augmenting prompts.
        Returns concatenated evidence as context string.
        """
        retrieval = self.retrieve(query, max_results=5)
        
        contexts = []
        
        for ev in retrieval["ranked_evidence"][:3]:
            node = ev.get("node", {})
            content = (node.get("summary") or node.get("content", ""))[:300]
            if content:
                ts = node.get("timestamp", "")
                contexts.append(f"[{ts[:10]}] {content}")
        
        for ent in retrieval.get("graph_entities", [])[:2]:
            name = ent["entity"]["name"]
            profile = ent["entity"].get("profile", "")[:150]
            if profile:
                contexts.append(f"Entidad: {name} - {profile}")
        
        return "\n".join(contexts)[:max_len]
    
    def get_stats(self) -> dict:
        """Get combined stats from tree and graph."""
        tree = self._get_tree()
        graph = self._get_graph()
        
        return {
            "tree": tree.get_stats(),
            "graph": graph.get_stats(),
            "weights": self.weights,
        }
    
    def close(self) -> None:
        """Close all connections."""
        if self.memory_tree:
            self.memory_tree.close()
        if self.entity_graph:
            self.entity_graph.close()


class HMemManager:
    """
    High-level manager for H-Mem system.
    Coordinates tree, graph, and retrieval components.
    """
    
    _instance: Optional[HMemManager] = None
    
    def __new__(cls, vault_name: Optional[str] = None) -> HMemManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, vault_name: Optional[str] = None) -> None:
        if self._initialized:
            return
        
        self.vault_name = vault_name
        self.retriever = HybridRetriever(vault_name=vault_name)
        self._initialized = True
    
    def remember(self, content: str, metadata: dict = None) -> dict:
        """Add a memory to the system."""
        return self.retriever.ingest_memory(content, metadata)
    
    def recall(self, query: str, time_range: tuple = None) -> dict:
        """Recall memories matching query."""
        return self.retriever.retrieve(query, time_range=time_range, max_results=10)
    
    def think(self, query: str, context: str = None) -> str:
        """Full retrieval + answer for a query."""
        result = self.retriever.answer(query, context)
        return result.get("answer", "")
    
    def get_context(self, query: str) -> str:
        """Get memory context for prompts."""
        return self.retriever.get_memory_context(query)
    
    def stats(self) -> dict:
        """Get system statistics."""
        return self.retriever.get_stats()
    
    def get_recent_memories(self, limit: int = 10) -> list:
        """Get recent memories from the tree."""
        return self.retriever.memory_tree.get_recent(limit=limit)
    
    def close(self) -> None:
        """Clean shutdown."""
        self.retriever.close()


def get_hmem_manager(vault_name: str = None) -> HMemManager:
    return HMemManager(vault_name=vault_name)


def get_hybrid_retriever(vault_name: str = None) -> HybridRetriever:
    return HybridRetriever(vault_name=vault_name)