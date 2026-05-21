"""WikiEngine - Karpathy Pattern for Asubarnipal."""

import datetime
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

import config

logger = logging.getLogger(__name__)

WIKI_SCHEMA = """
# SCHEMA ASUBARNIPAL WIKI v3.0

## Convenciones de archivo
- Fuentes crudas: `/raw/` - INMUTABLES. El agente nunca modifica.
- Wiki generado: `/wiki/` - El agente tiene control total.
- Notas de fuente: `source_<hash>.md` - Resumen de una fuente específica.
- Páginas de entidad: `entity_<nombre>.md` - Conceptos/entidades que evolucionan.
- Páginas de concepto: `concept_<nombre>.md` - Ideas abstractas que se refinan.
- Síntesis: `synthesis_<tema>.md` - Artículos que conectan múltiples fuentes.
- Mapas: `_MAPA_MAESTRO.md` - MOC maestro.

## Reglas de integración
1. ANTES de crear una nueva nota, buscar entidades/conceptos existentes relacionados.
2. SI una fuente contradice una entidad existente, DOCUMENTAR la contradicción con fecha.
3. ACTUALIZAR el index.md después de CADA operación de ingesta.
4. CROSS-REFERENCIAR: toda nota debe tener al menos 2 wikilinks salientes o entrantes.
5. NUNCA dejar una nota huérfana (sin links) después de la ingesta.

## Frontmatter obligatorio
---
tipo: source|entity|concept|synthesis|moc
titulo: "Nombre"
fuente: "nombre de la fuente o N/A"
fecha_ingesta: YYYY-MM-DD
fecha_actualizacion: YYYY-MM-DD
estado: draft|review|final
tags: [tag1, tag2]
relacionados: [[Nota1]], [[Nota2]]
---
"""

SCHEMA_PATH = config.OBSIDIAN_PATH / "CLAUDE.md"


def guardar_schema() -> None:
    """Persiste el schema en el vault de Obsidian."""
    try:
        config.OBSIDIAN_PATH.mkdir(parents=True, exist_ok=True)
        with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
            f.write(WIKI_SCHEMA)
    except Exception as e:
        logger.warning(f"No se pudo guardar schema: {e}")


class WikiEngine:
    """Motor de wiki Karpathy-style."""
    
    def __init__(self, obsidian_path: str = None):
        self.path = Path(obsidian_path) if obsidian_path else config.OBSIDIAN_PATH
        self.raw_path = self.path / "raw"
        self.wiki_path = self.path / "wiki"
        self.index_path = self.path / "index.md"
        self.log_path = self.path / "log.md"
        
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.wiki_path.mkdir(parents=True, exist_ok=True)
    
    def _hash_fuente(self, contenido: str) -> str:
        """Genera hash único para una fuente."""
        return hashlib.md5(contenido.encode()).hexdigest()[:12]
    
    def _extraer_frontmatter(self, contenido: str) -> Tuple[Dict, str]:
        """Extrae frontmatter YAML de una nota."""
        if contenido.startswith("---"):
            parts = contenido.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}, parts[2]
                except yaml.YAMLError:
                    return {}, contenido
        return {}, contenido
    
    def _buscar_notas_existentes(self) -> List[Dict]:
        """Escanea todas las notas del wiki."""
        notas = []
        if not self.wiki_path.exists():
            return notas
        
        for file_path in self.wiki_path.rglob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                fm, body = self._extraer_frontmatter(content)
                notas.append({
                    "id": file_path.stem,
                    "path": str(file_path),
                    "tipo": fm.get("tipo", "unknown"),
                    "titulo": fm.get("titulo", file_path.stem),
                    "tags": fm.get("tags", []),
                    "relacionados": fm.get("relacionados", []),
                    "fecha_ingesta": fm.get("fecha_ingesta", ""),
                    "fecha_actualizacion": fm.get("fecha_actualizacion", ""),
                    "fuente": fm.get("fuente", "N/A"),
                    "contenido": body[:500],
                })
            except Exception:
                continue
        return notas
    
    def _encontrar_relacionadas(self, tema: str, notas: List[Dict]) -> List[Dict]:
        """Busca notas existentes relacionadas."""
        tema_lower = tema.lower()
        relacionadas = []
        
        for nota in notas:
            score = 0
            if tema_lower in nota["titulo"].lower():
                score += 3
            for tag in nota["tags"]:
                if tema_lower in str(tag).lower():
                    score += 2
            if tema_lower in nota["contenido"].lower():
                score += 1
            
            if score > 0:
                relacionadas.append({**nota, "score": score})
        
        return sorted(relacionadas, key=lambda x: x["score"], reverse=True)[:5]
    
    def _actualizar_index(self, notas: List[Dict]):
        """Regenera el index.md."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        lines = [
            "# 📇 Index del Wiki Asubarnipal",
            f"",
            f"*Última actualización: {timestamp}*",
            "",
            "## 📊 Estadísticas",
            f"- Total notas: {len(notas)}",
            f"- Fuentes: {sum(1 for n in notas if n['tipo'] == 'source')}",
            f"- Entidades: {sum(1 for n in notas if n['tipo'] == 'entity')}",
            f"- Conceptos: {sum(1 for n in notas if n['tipo'] == 'concept')}",
            f"- Síntesis: {sum(1 for n in notas if n['tipo'] == 'synthesis')}",
            "",
            "---",
            "",
        ]
        
        por_tipo = {}
        for nota in notas:
            t = nota["tipo"]
            if t not in por_tipo:
                por_tipo[t] = []
            por_tipo[t].append(nota)
        
        tipo_nombres = {
            "source": "📄 Fuentes",
            "entity": "🏛️ Entidades",
            "concept": "💡 Conceptos",
            "synthesis": "🔗 Síntesis",
            "moc": "🗺️ Mapas de Contenido",
        }
        
        for tipo, nombre in tipo_nombres.items():
            if tipo in por_tipo:
                lines.append(f"## {nombre}")
                lines.append("")
                for nota in sorted(por_tipo[tipo], key=lambda x: x["titulo"]):
                    lines.append(f"- [[{nota['id']}]] | {nota['titulo']} | Tags: {', '.join(str(t) for t in nota['tags'][:3])}")
                lines.append("")
        
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info(f"📇 Index actualizado: {len(notas)} notas")
        except Exception as e:
            logger.warning(f"Error actualizando index: {e}")
    
    def log_ingest(self, fuente: str, paginas: int, accion: str = "ingest"):
        """Log estructurado en log.md."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## [{timestamp}] {accion} | {fuente} | Páginas: {paginas}\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning(f"Error en log.md: {e}")
    
    def ingestar(self, fuente_nombre: str, contenido: str, tipo_fuente: str = "web") -> Dict[str, Any]:
        """
        Pipeline de ingesta Karpathy-style:
        1. Guardar fuente cruda
        2. Buscar entidades existentes
        3. Crear/actualizar páginas de entidad
        4. Crear nota de fuente
        5. Actualizar index
        """
        from core.llm_router import LLMRouter
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        hash_id = self._hash_fuente(contenido)
        
        raw_file = self.raw_path / f"{tipo_fuente}_{hash_id}.md"
        try:
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(f"# Fuente: {fuente_nombre}\n")
                f.write(f"*Tipo: {tipo_fuente} | Hash: {hash_id} | Fecha: {timestamp}*\n\n")
                f.write(contenido[:50000])
        except Exception as e:
            logger.warning(f"Error guardando fuente cruda: {e}")
        
        notas_existentes = self._buscar_notas_existentes()
        relacionadas = self._encontrar_relacionadas(fuente_nombre, notas_existentes)
        
        llm = LLMRouter()
        
        contexto_existente = ""
        if relacionadas:
            contexto_existente = "\n\nNOTAS EXISTENTES RELACIONADAS:\n"
            for nota in relacionadas:
                contexto_existente += f"- [[{nota['id']}]] ({nota['tipo']}): {nota['contenido'][:200]}...\n"
        
        prompt = f"""Analiza esta fuente y extrae entidades y conceptos.

Fuente: {fuente_nombre}
Contenido: {contenido[:8000]}
{contexto_existente}

Responde en formato:
ENTIDADES: nombre1, nombre2, ...
CONCEPTOS: concepto1, concepto2, ...
SINTESIS_TITULO: Título sugerido
"""
        
        try:
            analisis = llm.generate(prompt)
        except Exception as e:
            logger.warning(f"Error en análisis LLM: {e}")
            analisis = "ENTIDADES:\nCONCEPTOS:\nSINTESIS_TITULO:"
        
        entidades = []
        conceptos = []
        sintesis_titulo = fuente_nombre
        
        for line in analisis.split("\n"):
            if line.startswith("ENTIDADES:"):
                entidades = [e.strip() for e in line.replace("ENTIDADES:", "").split(",") if e.strip()]
            elif line.startswith("CONCEPTOS:"):
                conceptos = [c.strip() for c in line.replace("CONCEPTOS:", "").split(",") if c.strip()]
            elif line.startswith("SINTESIS_TITULO:"):
                sintesis_titulo = line.replace("SINTESIS_TITULO:", "").strip() or fuente_nombre
        
        paginas_tocadas = []
        
        for entidad in entidades[:10]:
            entidad_id = f"entity_{entidad.replace(' ', '_').lower()[:30]}"
            entidad_path = self.wiki_path / f"{entidad_id}.md"
            
            nuevo_fm = {
                "tipo": "entity",
                "titulo": entidad,
                "fecha_ingesta": timestamp,
                "fecha_actualizacion": timestamp,
                "fuente": fuente_nombre,
                "estado": "draft",
                "tags": [tipo_fuente],
                "relacionados": [hash_id],
            }
            
            prompt_entity = f"""Crea página de entidad para: {entidad}

Contexto de fuente:
{contenido[:5000]}

Requisitos:
- Descripción clara
- Relación con la fuente [[{hash_id}]]
- 3-5 wikilinks a conceptos relacionados
"""
            try:
                nuevo_contenido = llm.generate(prompt_entity)
            except Exception:
                nuevo_contenido = f"Entidad: {entidad}\n\nContenido extraído de {fuente_nombre}."
            
            header = "---\n" + "\n".join(f"{k}: {json.dumps(v) if isinstance(v, list) else v}" for k, v in nuevo_fm.items()) + "\n---\n\n"
            try:
                with open(entidad_path, "w", encoding="utf-8") as f:
                    f.write(header + nuevo_contenido)
                paginas_tocadas.append(entidad_id)
                logger.info(f"📝 Entidad: [[{entidad_id}]]")
            except Exception as e:
                logger.warning(f"Error escribiendo entidad: {e}")
        
        source_id = f"source_{hash_id}"
        source_path = self.wiki_path / f"{source_id}.md"
        
        prompt_source = f"""Resume esta fuente y conecta con las entidades.

Fuente: {fuente_nombre}
Contenido: {contenido[:8000]}
Entidades: {', '.join(entidades)}
Conceptos: {', '.join(conceptos)}
"""
        try:
            source_content = llm.generate(prompt_source)
        except Exception:
            source_content = f"Resumen de {fuente_nombre}"
        
        source_fm = {
            "tipo": "source",
            "titulo": fuente_nombre,
            "fecha_ingesta": timestamp,
            "fuente_raw": str(raw_file),
            "estado": "final",
            "tags": [tipo_fuente] + entidades + conceptos,
            "relacionados": paginas_tocadas,
        }
        
        source_header = "---\n" + "\n".join(f"{k}: {json.dumps(v) if isinstance(v, list) else v}" for k, v in source_fm.items()) + "\n---\n\n"
        try:
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(source_header + source_content)
            paginas_tocadas.append(source_id)
        except Exception as e:
            logger.warning(f"Error escribiendo fuente: {e}")
        
        todas_notas = self._buscar_notas_existentes()
        self._actualizar_index(todas_notas)
        self.log_ingest(fuente_nombre, len(paginas_tocadas))
        
        return {
            "source_id": source_id,
            "entidades": entidades,
            "conceptos": conceptos,
            "paginas_tocadas": paginas_tocadas,
            "relacionadas_previas": [n["id"] for n in relacionadas],
        }
    
    def query_wiki(self, pregunta: str) -> str:
        """Consulta el wiki antes de generar respuesta."""
        from core.llm_router import LLMRouter
        
        notas = self._buscar_notas_existentes()
        
        if not notas:
            return "📚 El wiki está vacío. Usa /investigar para construir conocimiento."
        
        pregunta_lower = pregunta.lower()
        relevantes = []
        for nota in notas:
            score = 0
            if any(term in nota["titulo"].lower() for term in pregunta_lower.split()):
                score += 3
            for tag in nota["tags"]:
                if any(term in str(tag).lower() for term in pregunta_lower.split()):
                    score += 2
            if any(term in nota["contenido"].lower() for term in pregunta_lower.split()):
                score += 1
            if score > 0:
                relevantes.append({**nota, "score": score})
        
        relevantes = sorted(relevantes, key=lambda x: x["score"], reverse=True)[:5]
        
        if not relevantes:
            llm = LLMRouter()
            return llm.generate(pregunta)
        
        contexto = "CONTEXTO DEL WIKI:\n\n"
        for nota in relevantes:
            contexto += f"## [[{nota['id']}]] ({nota['tipo']})\n{nota['contenido'][:800]}...\n\n"
        
        prompt = f"""Responde usando SOLO el contexto del wiki.

PREGUNTA: {pregunta}
{contexto}

Requisitos:
1. Cita las notas [[id]]
2. Si no hay info, dilo explícitamente
3. Formato: Markdown
"""
        
        llm = LLMRouter()
        return llm.generate(prompt)
    
    def lint(self) -> List[str]:
        """Health-check del wiki."""
        notas = self._buscar_notas_existentes()
        problemas = []
        
        all_ids = {n["id"] for n in notas}
        linked_ids = set()
        for nota in notas:
            for rel in nota.get("relacionados", []):
                linked_ids.add(str(rel).replace("[[", "").replace("]]", ""))
        
        for nota in notas:
            if nota["id"] not in linked_ids and not nota.get("relacionados"):
                problemas.append(f"🏝️ HUÉRFANA: [[{nota['id']}]] - Sin conexiones")
        
        hoy = datetime.datetime.now()
        for nota in notas:
            try:
                fecha = datetime.datetime.strptime(nota.get("fecha_actualizacion", "2020-01-01"), "%Y-%m-%d")
                dias = (hoy - fecha).days
                if dias > 30 and nota["tipo"] in ["entity", "concept"]:
                    problemas.append(f"⏰ STALE: [[{nota['id']}]] - {dias} días sin actualizar")
            except Exception:
                pass
        
        for nota in notas:
            if not nota.get("tags"):
                problemas.append(f"🏷️ SIN_TAGS: [[{nota['id']}]]")
        
        return problemas


class WikiVectorIndex:
    """Indexador vectorial del wiki."""
    
    def __init__(self, wiki_path: str = None):
        self.wiki_path = Path(wiki_path) if wiki_path else config.OBSIDIAN_PATH / "wiki"
        self.graph_store_path = config.OBSIDIAN_PATH / "graph_store"
        self.graph_store_path.mkdir(parents=True, exist_ok=True)
        
        self.notes: List[Dict] = []
        self.embeddings: Dict[str, Any] = {}
        self.comunidades: Dict[str, int] = {}
        self.hubs: List[Tuple[str, float]] = []
        
        self._scan()
    
    def _scan(self) -> None:
        """Escanea las notas."""
        if not self.wiki_path.exists():
            return
        
        import yaml
        for file_path in self.wiki_path.rglob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            fm = yaml.safe_load(parts[1]) or {}
                        except Exception:
                            fm = {}
                        body = parts[2]
                    else:
                        fm = {}
                        body = content
                else:
                    fm = {}
                    body = content
                
                wikilinks = re.findall(r"\[\[([^\]]+)\]\]", body)
                
                self.notes.append({
                    "id": file_path.stem,
                    "tipo": fm.get("tipo", "unknown"),
                    "titulo": fm.get("titulo", file_path.stem),
                    "tags": fm.get("tags", []),
                    "content": body[:2000],
                    "wikilinks": wikilinks,
                    "word_count": len(body.split()),
                })
            except Exception:
                continue
        
        logger.info(f"📄 Wiki escaneado: {len(self.notes)} notas")
    
    def generar_embeddings(self) -> None:
        """Genera embeddings (si sentence-transformers disponible)."""
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            model = SentenceTransformer("all-MiniLM-L6-v2")
            
            texts = [f"{n['titulo']}. {' '.join(n['tags'])}. {n['content'][:500]}" for n in self.notes]
            
            if texts:
                embeddings = model.encode(texts, show_progress_bar=False)
                self.embeddings = {self.notes[i]["id"]: embeddings[i] for i in range(len(self.notes))}
                logger.info(f"🧠 Embeddings: {len(self.embeddings)}")
        except ImportError:
            logger.warning("sentence-transformers no disponible")
        except Exception as e:
            logger.warning(f"Error embeddings: {e}")
    
    def construir_grafo(self) -> Any:
        """Construye grafo de conocimiento."""
        try:
            import networkx as nx
            
            G = nx.DiGraph()
            
            for note in self.notes:
                G.add_node(note["id"], 
                          tipo=note["tipo"],
                          titulo=note["titulo"],
                          tags=note["tags"])
            
            for note in self.notes:
                for link in note["wikilinks"]:
                    target = link.split("|")[0].strip().replace(" ", "_").lower()
                    if target and target != note["id"]:
                        G.add_edge(note["id"], target, tipo="wikilink")
            
            logger.info(f"🕸️ Grafo: {len(G.nodes())} nodos, {len(G.edges())} aristas")
            return G
        except ImportError:
            logger.warning("networkx no disponible")
            return None
    
    def detectar_comunidades(self) -> dict[str, int]:
        """Detecta comunidades (Louvain)."""
        try:
            import networkx as nx
            from collections import Counter
            
            G = self.construir_grafo()
            if not G:
                return {}
            
            G_undirected = G.to_undirected()
            communities = nx.community.louvain_communities(G_undirected, seed=42)
            
            comunidad_map = {}
            for comm_id, comm_nodes in enumerate(communities):
                for node in comm_nodes:
                    comunidad_map[node] = comm_id
            
            self.comunidades = comunidad_map
            logger.info(f"📊 Comunidades: {len(communities)}")
            return comunidad_map
        except Exception as e:
            logger.warning(f"Error comunidades: {e}")
            return {}
    
    def identificar_hubs(self) -> list[tuple[str, float]]:
        """Identifica hubs por betweenness centrality."""
        try:
            import networkx as nx
            
            G = self.construir_grafo()
            if not G:
                return []
            
            betweenness = nx.betweenness_centrality(G.to_undirected())
            degree_cent = nx.degree_centrality(G.to_undirected())
            
            hub_score = {}
            for node in G.nodes():
                b = betweenness.get(node, 0)
                d = degree_cent.get(node, 0)
                hub_score[node] = (b * 0.6) + (d * 0.4)
            
            self.hubs = sorted(hub_score.items(), key=lambda x: x[1], reverse=True)[:10]
            logger.info(f"🏛️ Hubs: {len(self.hubs)}")
            return self.hubs
        except Exception as e:
            logger.warning(f"Error hubs: {e}")
            return []
    
    def full_index(self) -> dict[str, int]:
        """Pipeline completo de indexación."""
        self.generar_embeddings()
        self.detectar_comunidades()
        self.identificar_hubs()
        return {
            "notas": len(self.notes),
            "embeddings": len(self.embeddings),
            "comunidades": len(set(self.comunidades.values())),
            "hubs": len(self.hubs),
        }