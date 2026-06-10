"""
FidelityChecker: Verifica fidelidad factual de respuestas del agente contra ground truth.

Métricas:
1. Accuracy factual: % de claims numéricos/técnicos correctos
2. Alucinaciones: claims inventados no presentes en fuente
3. Omisiones críticas: info clave de fuente no mencionada
4. Citas falsas: citas textuales inventadas
5. Drift semántico: paráfrasis que cambian significado
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class Claim:
    """Un claim verificable extraído del texto."""
    text: str
    claim_type: str  # "numeric", "factual", "quote", "methodology", "negative_usage", "positive_usage", "architecture"
    source_section: str = ""
    verified: bool = False
    match_details: Optional[str] = None
    context: str = ""  # Contexto alrededor del claim (para verificación)


@dataclass
class FidelityReport:
    """Reporte de fidelidad para una respuesta."""
    question: str
    response: str
    
    # Métricas
    claims_detected: int = 0
    claims_verified: int = 0
    hallucinations: List[str] = field(default_factory=list)
    omissions: List[str] = field(default_factory=list)
    false_citations: List[str] = field(default_factory=list)
    
    # Score
    score: float = 0.0  # 0-100
    
    # Detalles
    verified_claims: List[Dict] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convierte el reporte a diccionario para serialización."""
        return {
            "question": self.question,
            "response": self.response[:500],  # Truncar para JSON
            "score": self.score,
            "claims_detected": self.claims_detected,
            "claims_verified": self.claims_verified,
            "hallucinations": self.hallucinations,
            "omissions": self.omissions,
            "false_citations": self.false_citations,
            "verified_claims": self.verified_claims,
            "unverified_claims": self.unverified_claims,
        }
    
    def summary(self) -> str:
        """Genera resumen legible del reporte."""
        lines = [
            f"Score: {self.score:.1f}/100",
            f"Claims: {self.claims_verified}/{self.claims_detected} verified",
        ]
        if self.hallucinations:
            lines.append(f"⚠️  Hallucinations: {len(self.hallucinations)}")
            for h in self.hallucinations[:3]:
                lines.append(f"   - {h[:100]}")
        if self.omissions:
            lines.append(f"⚠️  Omissions: {len(self.omissions)}")
            for o in self.omissions[:3]:
                lines.append(f"   - {o[:100]}")
        if self.false_citations:
            lines.append(f"⚠️  False citations: {len(self.false_citations)}")
        return "\n".join(lines)


class FidelityChecker:
    """Verifica fidelidad factual de respuestas contra ground truth."""
    
    def __init__(self, ground_truth_text: str):
        """
        Args:
            ground_truth_text: Texto completo del paper/documento fuente
        """
        self.ground_truth = ground_truth_text
        self.ground_truth_lower = ground_truth_text.lower()
        self.ground_truth_claims = self._extract_ground_truth_claims()
    
    def _extract_ground_truth_claims(self) -> List[Claim]:
        """Extrae claims verificables del ground truth."""
        claims = []
        
        # 1. Claims numéricos (BLEU scores, parámetros, dimensiones)
        numeric_patterns = [
            (r'(\d+\.?\d*)\s*BLEU', 'BLEU score'),
            (r'(\d+)\s*million\s*parameters', 'parameters'),
            (r'd_model\s*=\s*(\d+)', 'd_model'),
            (r'(\d+)\s*heads', 'attention heads'),
            (r'(\d+)\s*layers', 'layers'),
            (r'(\d+)\s*hours', 'training time'),
            (r'(\d+)\s*GPUs', 'GPUs'),
        ]
        
        for pattern, claim_type in numeric_patterns:
            matches = re.finditer(pattern, self.ground_truth, re.IGNORECASE)
            for match in matches:
                claims.append(Claim(
                    text=match.group(0),
                    claim_type="numeric",
                    source_section=self._find_section(match.start()),
                ))
        
        # 2. Claims metodológicos (arquitectura, componentes)
        methodology_patterns = [
            r'(self-attention|multi-head attention|scaled dot-product attention)',
            r'(encoder|decoder|feed-forward network)',
            r'(positional encoding|layer normalization)',
            r'(recurrence|convolution)',
        ]
        
        for pattern in methodology_patterns:
            matches = re.finditer(pattern, self.ground_truth, re.IGNORECASE)
            for match in matches:
                claims.append(Claim(
                    text=match.group(0),
                    claim_type="methodology",
                    source_section=self._find_section(match.start()),
                ))
        
        # 3. Citas textuales (entre comillas)
        quote_pattern = r'"([^"]{10,200})"'
        for match in re.finditer(quote_pattern, self.ground_truth):
            claims.append(Claim(
                text=match.group(1),
                claim_type="quote",
                source_section=self._find_section(match.start()),
            ))
        
        return claims
    
    def _find_section(self, char_pos: int) -> str:
        """Encuentra la sección del paper dada una posición de carácter."""
        # Buscar headers de sección (##, ###, o números como "1.", "2.1")
        section_pattern = r'^(#+\s+.+|^\d+\.?\d*\s+[A-Z].+)$'
        lines = self.ground_truth[:char_pos].split('\n')
        
        for line in reversed(lines):
            if re.match(section_pattern, line.strip()):
                return line.strip()[:50]
        
        return "Unknown section"
    
    def check_response(self, question: str, response: str) -> FidelityReport:
        """
        Verifica fidelidad de una respuesta contra ground truth.
        
        Args:
            question: Pregunta original
            response: Respuesta del agente
            
        Returns:
            FidelityReport con métricas detalladas
        """
        report = FidelityReport(question=question, response=response)
        
        # 1. Extraer claims de la respuesta
        response_claims = self._extract_response_claims(response)
        report.claims_detected = len(response_claims)
        
        # 2. Verificar cada claim contra ground truth
        for claim in response_claims:
            verified, match_details = self._verify_claim(claim, response)
            if verified:
                report.claims_verified += 1
                report.verified_claims.append({
                    "claim": claim.text,
                    "match": match_details,
                    "source_section": self._find_source_for_claim(claim),
                })
            else:
                # Posible alucinación
                if claim.claim_type == "numeric":
                    report.hallucinations.append(f"Numeric claim not found: {claim.text}")
                elif claim.claim_type == "quote":
                    report.false_citations.append(claim.text)
                elif claim.claim_type in ["negative_usage", "positive_usage", "architecture"]:
                    report.hallucinations.append(f"Qualitative claim not verified: {claim.text}")
                else:
                    report.unverified_claims.append(claim.text)
        
        # 3. Detectar omisiones críticas
        relevant_gt_claims = self._get_relevant_claims(question)
        for gt_claim in relevant_gt_claims:
            if not self._claim_in_response(gt_claim, response):
                report.omissions.append(f"{gt_claim.claim_type}: {gt_claim.text}")
        
        # 4. Calcular score
        report.score = self._calculate_score(report)
        
        return report
    
    def _extract_response_claims(self, response: str) -> List[Claim]:
        """Extrae claims de la respuesta del agente."""
        claims = []
        
        # Numéricos con contexto
        numeric_pattern = r'\b(\d+\.?\d*)\s*(BLEU|million|parameters|heads|layers|dimensions|hours|GPUs|M|K)\b'
        for match in re.finditer(numeric_pattern, response, re.IGNORECASE):
            # Capturar contexto (50 chars antes y después)
            start = max(0, match.start() - 50)
            end = min(len(response), match.end() + 50)
            context = response[start:end]
            
            # Normalizar unidades (M -> million, K -> thousand)
            number = match.group(1)
            unit = match.group(2).lower()
            
            if unit == 'm':
                unit = 'million'
            elif unit == 'k':
                # Convertir K a número real (ej: 300K -> 300000)
                try:
                    number = str(int(float(number) * 1000))
                    unit = ''
                except:
                    pass
            
            claims.append(Claim(
                text=f"{number} {unit}".strip(),
                claim_type="numeric",
                source_section="",
                context=context
            ))
        
        # Citas
        quote_pattern = r'"([^"]{10,200})"'
        for match in re.finditer(quote_pattern, response):
            claims.append(Claim(text=match.group(1), claim_type="quote", source_section=""))
        
        # Claims cualitativos (afirmaciones sobre arquitectura/método)
        qualitative_patterns = [
            (r'(does not|doesn\'t|no|without|never)\s+use\s+(\w+)', 'negative_usage'),
            (r'uses\s+(\w+)', 'positive_usage'),
            (r'based (?:entirely|solely|only) on\s+([\w\s]+)', 'architecture'),
            (r'dispensing with\s+([\w\s]+)', 'architecture'),
        ]
        
        for pattern, claim_type in qualitative_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                claims.append(Claim(
                    text=match.group(0),
                    claim_type=claim_type,
                    source_section=""
                ))
        
        # Claims factuales (oraciones con verbos clave)
        factual_pattern = r'([^.]*\b(achieved|uses|has|contains|includes|requires)\b[^.]*)'
        for match in re.finditer(factual_pattern, response, re.IGNORECASE):
            text = match.group(1).strip()
            if len(text) > 20:  # Filtrar frases muy cortas
                claims.append(Claim(text=text, claim_type="factual", source_section=""))
        
        return claims
    
    def _verify_claim(self, claim: Claim, response: str = "") -> Tuple[bool, Optional[str]]:
        """Verifica si un claim existe en ground truth."""
        # Normalizar texto para comparación
        normalized_claim = re.sub(r'\s+', ' ', claim.text.lower().strip())
        normalized_gt = re.sub(r'\s+', ' ', self.ground_truth_lower)
        
        # Búsqueda exacta
        if normalized_claim in normalized_gt:
            return True, "exact_match"
        
        # Búsqueda fuzzy (para numéricos con formato diferente)
        if claim.claim_type == "numeric":
            # Extraer número
            numbers = re.findall(r'\d+\.?\d*', claim.text)
            if numbers:
                for num in numbers:
                    if num in normalized_gt:
                        # Verificar contexto si está disponible
                        if claim.context:
                            context_verified = self._verify_numeric_context(
                                num, claim.context, normalized_gt
                            )
                            if context_verified:
                                return True, f"numeric_match:{num}"
                            else:
                                return False, f"numeric_context_mismatch:{num}"
                        return True, f"numeric_match:{num}"
        
        # Verificar claims cualitativos (negaciones, usos, arquitectura)
        if claim.claim_type in ["negative_usage", "positive_usage", "architecture"]:
            return self._verify_qualitative_claim(claim, normalized_gt)
        
        # Búsqueda por palabras clave (para claims factuales)
        if claim.claim_type == "factual":
            keywords = re.findall(r'\b\w{4,}\b', normalized_claim)
            if keywords:
                keyword_matches = sum(1 for kw in keywords if kw in normalized_gt)
                if keyword_matches / len(keywords) > 0.6:  # 60% de keywords presentes
                    return True, "keyword_match"
        
        return False, None
    
    def _verify_numeric_context(self, number: str, context: str, ground_truth: str) -> bool:
        """Verifica que un número aparezca en el contexto correcto."""
        # Extraer entidades del contexto (big, base, encoder, decoder, etc.)
        context_lower = context.lower()
        
        # Patrones de entidades comunes
        entity_patterns = [
            r'\b(big|large)\b',
            r'\b(base|small)\b',
            r'\b(encoder)\b',
            r'\b(decoder)\b',
        ]
        
        entities_in_context = []
        for pattern in entity_patterns:
            if re.search(pattern, context_lower):
                entities_in_context.append(re.search(pattern, context_lower).group(1))
        
        # Si no hay entidades específicas, aceptar el número si está en ground truth
        if not entities_in_context:
            return number in ground_truth
        
        # Buscar el número en ground truth con las mismas entidades
        for entity in entities_in_context:
            # Buscar en un rango más amplio (300 chars) permitiendo cualquier contenido en medio
            pattern1 = rf'{entity}.{{0,300}}\b{number}\b'
            pattern2 = rf'\b{number}\b.{{0,300}}{entity}'
            
            if re.search(pattern1, ground_truth, re.IGNORECASE | re.DOTALL):
                return True
            if re.search(pattern2, ground_truth, re.IGNORECASE | re.DOTALL):
                return True
        
        # Si el número está en ground truth pero no con la entidad, verificar si es el único lugar
        number_positions = [m.start() for m in re.finditer(rf'\b{number}\b', ground_truth)]
        
        if len(number_positions) == 1:
            # Solo hay una ocurrencia, verificar si la entidad está cerca
            pos = number_positions[0]
            nearby_text = ground_truth[max(0, pos-300):pos+300].lower()
            if entity in nearby_text:
                return True
        
        return False
    
    def _verify_qualitative_claim(self, claim: Claim, ground_truth: str) -> Tuple[bool, Optional[str]]:
        """Verifica claims cualitativos (negaciones, usos, arquitectura)."""
        claim_lower = claim.text.lower()
        
        # Detectar negaciones
        is_negative = any(neg in claim_lower for neg in [
            'does not', 'doesn\'t', 'no ', 'without', 'never', 'not use'
        ])
        
        # Extraer tecnología mencionada
        tech_match = re.search(r'use[sd]?\s+(\w+)', claim_lower)
        if not tech_match:
            # Intentar con otros patrones
            tech_match = re.search(r'based.*?on\s+([\w\s]+)', claim_lower)
        
        if not tech_match:
            return False, "no_technology_detected"
        
        technology = tech_match.group(1).strip()
        
        # Mapeo de tecnologías relacionadas
        tech_aliases = {
            'lstm': ['recurrence', 'recurrent', 'rnn'],
            'gru': ['recurrence', 'recurrent', 'rnn'],
            'rnn': ['recurrence', 'recurrent'],
            'convolution': ['convolutions', 'cnn'],
            'cnn': ['convolutions', 'convolution'],
        }
        
        # Verificar en ground truth
        tech_in_gt = technology in ground_truth
        
        # Buscar aliases si la tecnología principal no está
        alias_in_gt = None
        if not tech_in_gt and technology in tech_aliases:
            for alias in tech_aliases[technology]:
                if alias in ground_truth:
                    alias_in_gt = alias
                    break
        
        if is_negative:
            # Si es negación, la tecnología NO debería estar en uso
            # Buscar patrones de negación en ground truth
            search_terms = [technology]
            if alias_in_gt:
                search_terms.append(alias_in_gt)
            
            for term in search_terms:
                negation_patterns = [
                    rf'does not use\s+{term}',
                    rf'without\s+{term}',
                    rf'dispensing with\s+{term}',
                    rf'no\s+{term}',
                    rf'entirely\s+.*?{term}',
                ]
                
                for pattern in negation_patterns:
                    if re.search(pattern, ground_truth, re.IGNORECASE):
                        return True, f"negative_verified:{term}"
            
            # Si la tecnología (o sus aliases) no está en ground truth, la negación es correcta
            if not tech_in_gt and not alias_in_gt:
                return True, f"technology_absent:{technology}"
            
            return False, f"negative_not_verified:{technology}"
        else:
            # Si es afirmación, la tecnología DEBERÍA estar en uso
            if tech_in_gt or alias_in_gt:
                search_term = technology if tech_in_gt else alias_in_gt
                
                # Verificar que no sea solo en referencias bibliográficas
                # Buscar el término fuera de la sección de referencias
                ref_section_match = re.search(r'\bReferences\b', ground_truth, re.IGNORECASE)
                if ref_section_match:
                    main_text = ground_truth[:ref_section_match.start()]
                else:
                    main_text = ground_truth
                
                # Verificar que se use en el texto principal (no solo en referencias)
                if search_term not in main_text.lower():
                    return False, f"technology_only_in_references:{search_term}"
                
                # Verificar que se use (no solo se mencione)
                usage_patterns = [
                    rf'uses?\s+{search_term}',
                    rf'using\s+{search_term}',
                    rf'based on\s+{search_term}',
                ]
                
                for pattern in usage_patterns:
                    if re.search(pattern, main_text, re.IGNORECASE):
                        return True, f"usage_verified:{search_term}"
                
                # Si está presente pero no se verifica uso explícito, aceptar con advertencia
                return True, f"technology_present:{search_term}"
            
            # Si la tecnología NO está en ground truth, la afirmación es falsa
            return False, f"technology_not_in_source:{technology}"
    
    def _find_source_for_claim(self, claim: Claim) -> str:
        """Encuentra la sección del ground truth donde aparece el claim."""
        normalized_claim = re.sub(r'\s+', ' ', claim.text.lower().strip())
        pos = self.ground_truth_lower.find(normalized_claim)
        if pos >= 0:
            return self._find_section(pos)
        return "Not found"
    
    def _get_relevant_claims(self, question: str) -> List[Claim]:
        """Obtiene claims del ground truth relevantes para la pregunta."""
        # Extraer keywords de la pregunta
        keywords = re.findall(r'\b\w{4,}\b', question.lower())
        
        relevant = []
        for claim in self.ground_truth_claims:
            claim_text = claim.text.lower()
            if any(kw in claim_text for kw in keywords):
                relevant.append(claim)
        
        return relevant[:10]  # Top 10 más relevantes
    
    def _claim_in_response(self, claim: Claim, response: str) -> bool:
        """Verifica si un claim del ground truth está en la respuesta."""
        normalized_claim = re.sub(r'\s+', ' ', claim.text.lower().strip())
        normalized_response = re.sub(r'\s+', ' ', response.lower())
        
        # Búsqueda exacta
        if normalized_claim in normalized_response:
            return True
        
        # Búsqueda por keywords
        keywords = re.findall(r'\b\w{4,}\b', normalized_claim)
        if keywords:
            keyword_matches = sum(1 for kw in keywords if kw in normalized_response)
            return keyword_matches / len(keywords) > 0.5
        
        return False
    
    def _calculate_score(self, report: FidelityReport) -> float:
        """Calcula score de fidelidad (0-100)."""
        if report.claims_detected == 0:
            return 0.0
        
        # Componentes del score
        accuracy = (report.claims_verified / report.claims_detected) * 100 if report.claims_detected > 0 else 0
        hallucination_penalty = len(report.hallucinations) * 10
        citation_penalty = len(report.false_citations) * 15
        omission_penalty = len(report.omissions) * 5
        
        score = accuracy - hallucination_penalty - citation_penalty - omission_penalty
        return max(0.0, min(100.0, score))


def load_paper_from_wiki(paper_name: str = "Attention Is All You Need") -> str:
    """Carga el contenido de un paper desde la wiki SQLite."""
    import sqlite3
    from pathlib import Path
    
    wiki_db = Path(__file__).parent.parent.parent / "data" / "wiki.db"
    
    if not wiki_db.exists():
        raise FileNotFoundError(f"Wiki database not found: {wiki_db}")
    
    conn = sqlite3.connect(str(wiki_db))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM entities 
        WHERE name = ? AND content IS NOT NULL AND length(content) > 1000
        ORDER BY length(content) DESC
        LIMIT 1
    """, (paper_name,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        raise ValueError(f"Paper '{paper_name}' not found in wiki or has no content")
    
    return row[0]


if __name__ == "__main__":
    # Test rápido
    print("Testing FidelityChecker...")
    
    try:
        paper_content = load_paper_from_wiki()
        checker = FidelityChecker(paper_content)
        
        print(f"✓ Loaded paper: {len(paper_content)} chars")
        print(f"✓ Extracted {len(checker.ground_truth_claims)} claims from ground truth")
        
        # Test con respuesta de ejemplo
        test_response = """
        The Transformer big achieved 28.4 BLEU on WMT 2014 English-to-German.
        It has 213 million parameters and uses multi-head attention.
        """
        
        report = checker.check_response(
            "What is the BLEU score?",
            test_response
        )
        
        print(f"\nTest Report:")
        print(report.summary())
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
