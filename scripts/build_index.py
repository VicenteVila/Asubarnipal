"""Build wiki index and graph - Standalone script."""

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
WIKI_DIR = Path("/mnt/c/Obsidian/wiki")
GRAPH_STORE_PATH = Path("/mnt/c/Obsidian/graph_store")
RAG_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RAG_DEVICE = "cpu"


def build_wiki_index():
    """Build vector index + knowledge graph from wiki."""
    
    if not WIKI_DIR.exists():
        logger.error(f"Wiki directory not found: {WIKI_DIR}")
        return {"error": "Wiki not found"}
    
    GRAPH_STORE_PATH.mkdir(parents=True, exist_ok=True)
    
    notes = list(WIKI_DIR.glob("*.md"))
    logger.info(f"Found {len(notes)} notes")
    
    # Load embeddings model
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        import faiss
        
        logger.info("Loading sentence-transformers model...")
        model = SentenceTransformer(RAG_MODEL, device=RAG_DEVICE)
    except Exception as e:
        logger.error(f"Could not load model: {e}")
        return {"error": str(e)}
    
    # Extract all text content
    texts = []
    filenames = []
    metadatas = []
    
    for note in notes:
        try:
            content = note.read_text(encoding="utf-8")
            
            # Parse frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        import yaml
                        fm = yaml.safe_load(parts[1]) or {}
                    except:
                        fm = {}
                    body = parts[2]
                else:
                    body = content
            else:
                fm = {}
                body = content
            
            texts.append(body[:2000])
            filenames.append(note.stem)
            metadatas.append({
                "title": fm.get("title", note.stem),
                "tipo": fm.get("tipo", "unknown"),
                "tags": fm.get("tags", []),
            })
        except Exception:
            pass
    
    logger.info(f"Processing {len(texts)} documents...")
    
    # Generate embeddings
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Save FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    
    index_path = GRAPH_STORE_PATH / "embeddings.pkl"
    faiss.write_index(index, str(index_path))
    
    docs_path = GRAPH_STORE_PATH / "documents.json"
    docs_path.write_text(json.dumps(filenames, indent=2))
    
    # Build knowledge graph from links
    logger.info("Building knowledge graph...")
    
    nodes = set()
    edges = []
    links_by_note = defaultdict(list)
    
    for note in notes:
        try:
            content = note.read_text(encoding="utf-8")
            nodes.add(note.stem)
            
            # Find [[links]]
            links = re.findall(r"\[\[(.+?)\]\]", content)
            for link in links:
                edges.append((note.stem, link))
                nodes.add(link)
                links_by_note[note.stem].append(link)
        except Exception:
            pass
    
    # Calculate centrality (simple degree centrality)
    degree = defaultdict(int)
    for src, dst in edges:
        degree[src] += 1
        degree[dst] += 1
    
    hubs = sorted(degree.items(), key=lambda x: -x[1])[:20]
    
    # Detect communities (simple - by shared links)
    communities = {}
    community_id = 0
    
    for node in nodes:
        if node in communities:
            continue
        
        community = {node}
        for src, dst in edges:
            if src == node:
                community.add(dst)
            elif dst == node:
                community.add(src)
        
        if len(community) > 1:
            for n in community:
                communities[n] = community_id
            community_id += 1
    
    # Save metadata
    metadata = {
        "total_nodos": len(nodes),
        "total_aristas": len(edges),
        "hubs": hubs,
        "comunidades": communities,
        "indexed_at": datetime.now().isoformat(),
    }
    
    meta_path = GRAPH_STORE_PATH / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    # Save graph as adjacency list
    graph_data = {
        "nodes": list(nodes),
        "edges": edges,
        "links_by_note": dict(links_by_note),
    }
    
    graph_path = GRAPH_STORE_PATH / "graph.json"
    graph_path.write_text(json.dumps(graph_data, indent=2, ensure_ascii=False))
    
    # Generate report
    report = f"""# 📊 Graph Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Resumen

| Métrica | Valor |
|---------|-------|
| Notas procesadas | {len(texts)} |
| Nodos en grafo | {len(nodes)} |
| Aristas (enlaces) | {len(edges)} |
| Comunidades | {community_id} |
| Hubs identificados | {len(hubs)} |

## 🏛️ Hubs (Top 20)

"""
    for i, (hub, score) in enumerate(hubs[:20], 1):
        report += f"{i}. **{hub}** - {score} conexiones\n"
    
    report += "\n## 📊 Comunidades\n\n"
    comm_groups = defaultdict(list)
    for node, cid in communities.items():
        comm_groups[cid].append(node)
    
    for cid, members in sorted(comm_groups.items())[:10]:
        report += f"- Comunidad {cid}: {', '.join(members[:5])}{'...' if len(members) > 5 else ''}\n"
    
    report += f"""
## 🎯 Próximos Pasos

1. Explorar los hubs más conectados
2. Unir comunidades relacionadas
3. Añadir notas que conecten topics aislados
4. Ejecutar `/hubs` para ver análisis centrality
5. Ejecutar `/clusters` para ver comunidades

---
*Generado por Asubarnipal /indexar_wiki*
"""
    
    report_path = GRAPH_STORE_PATH / "graph_report.md"
    report_path.write_text(report)
    
    logger.info(f"✅ Index completado!")
    logger.info(f"  Nodos: {len(nodes)}")
    logger.info(f"  Aristas: {len(edges)}")
    logger.info(f"  Comunidades: {community_id}")
    
    return {
        "indexed": len(texts),
        "nodes": len(nodes),
        "edges": len(edges),
        "communities": community_id,
    }


if __name__ == "__main__":
    result = build_wiki_index()
    print(f"\n✅ Resultado: {result}")