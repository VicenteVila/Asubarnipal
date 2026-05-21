"""GraphBuilder - Construye el grafo de conocimiento."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Construye y mantiene el grafo de conocimiento."""
    
    def __init__(self, wiki_path: Optional[Path] = None):
        self.wiki_path = wiki_path or config.WIKI_DIR
        self.db_path = config.WIKI_PATH
        self.graph_data = {
            "nodes": [],
            "edges": [],
            "metadata": {}
        }
        self._init_connection()
    
    def _init_connection(self) -> None:
        """Inicializa conexion a la base de datos."""
        if not self.db_path.exists():
            logger.warning(f"Wiki database not found: {self.db_path}")
            self.conn = None
            return
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def build_graph(self) -> Dict:
        """Construye el grafo de conocimiento completo."""
        if self.conn is None:
            return {"nodes": 0, "edges": 0, "hubs": []}
        
        nodes = []
        edges = []
        
        try:
            self.cursor.execute("SELECT id, name, tipo, tags, relacionados FROM entities")
            entities = self.cursor.fetchall()
            
            for entity in entities:
                node = {
                    "id": entity[0],
                    "name": entity[1],
                    "tipo": entity[2] if len(entity) > 2 else "entity",
                }
                
                if len(entity) > 3 and entity[3]:
                    try:
                        tags = json.loads(entity[3])
                        node["tags"] = tags
                    except json.JSONDecodeError:
                        node["tags"] = []
                
                nodes.append(node)
                
                if len(entity) > 4 and entity[4]:
                    try:
                        relacionados = json.loads(entity[4])
                        for related in relacionados:
                            if isinstance(related, dict) and "id" in related:
                                edges.append({
                                    "source": entity[0],
                                    "target": related["id"],
                                    "type": related.get("relation", "related")
                                })
                    except json.JSONDecodeError:
                        pass
            
            self.cursor.execute("""
                SELECT from_entity, to_entity, relation_type 
                FROM relations
            """)
            relations = self.cursor.fetchall()
            
            for rel in relations:
                if rel[0] and rel[1]:
                    edges.append({
                        "source": rel[0],
                        "target": rel[1],
                        "type": rel[2] if rel[2] else "related"
                    })
            
            self.graph_data = {
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "build_time": datetime.now().isoformat()
                }
            }
            
            self._save_graph()
            
            hubs = self._calculate_hubs(nodes, edges)
            
            result = {
                "nodes": len(nodes),
                "edges": len(edges),
                "hubs": hubs[:10]
            }
            
            logger.info(f"Graph built: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error building graph: {e}")
            return {"nodes": 0, "edges": 0, "hubs": [], "error": str(e)}
    
    def _calculate_hubs(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """Calcula nodos hub (mas conectados)."""
        connection_count = {}
        
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if source:
                connection_count[source] = connection_count.get(source, 0) + 1
            if target:
                connection_count[target] = connection_count.get(target, 0) + 1
        
        nodes_with_connections = []
        for node in nodes:
            node_id = node.get("id")
            if node_id in connection_count:
                nodes_with_connections.append({
                    "id": node_id,
                    "name": node.get("name"),
                    "connections": connection_count[node_id]
                })
        
        nodes_with_connections.sort(key=lambda x: x["connections"], reverse=True)
        
        return nodes_with_connections
    
    def _save_graph(self) -> None:
        """Guarda el grafo en archivo."""
        graph_file = config.DATA_DIR / "knowledge_graph.json"
        graph_file.parent.mkdir(exist_ok=True)
        
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(self.graph_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Graph saved to {graph_file}")
    
    def get_neighbors(self, node_id: int, depth: int = 1) -> List[Dict]:
        """Obtiene nodos vecinos."""
        if self.conn is None:
            return []
        
        neighbors = []
        
        try:
            self.cursor.execute("""
                SELECT from_entity, to_entity 
                FROM relations 
                WHERE from_entity = ? OR to_entity = ?
            """, (node_id, node_id))
            
            relations = self.cursor.fetchall()
            neighbor_ids = set()
            
            for rel in relations:
                if rel[0] and rel[0] != node_id:
                    neighbor_ids.add(rel[0])
                if rel[1] and rel[1] != node_id:
                    neighbor_ids.add(rel[1])
            
            if neighbor_ids:
                placeholders = ",".join(["?" for _ in neighbor_ids])
                self.cursor.execute(f"""
                    SELECT id, name, tipo 
                    FROM entities 
                    WHERE id IN ({placeholders})
                """, tuple(neighbor_ids))
                
                neighbors = [
                    {"id": row[0], "name": row[1], "tipo": row[2]}
                    for row in self.cursor.fetchall()
                ]
            
        except Exception as e:
            logger.error(f"Error getting neighbors: {e}")
        
        return neighbors
    
    def close(self) -> None:
        """Cierra la conexion."""
        if self.conn:
            self.conn.close()
