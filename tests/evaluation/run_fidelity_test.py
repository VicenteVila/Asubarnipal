"""
Script de evaluación de fidelidad factual.

Ejecuta las 5 queries de evaluación contra el agente y verifica
si las respuestas mantienen fidelidad al paper original.

Uso:
    python tests/evaluation/run_fidelity_test.py
"""

import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import time
from datetime import datetime
from typing import Dict, List

from tests.evaluation.fidelity_checker import FidelityChecker, load_paper_from_wiki


def load_evaluation_queries() -> List[Dict]:
    """Carga las queries de evaluación desde JSON."""
    queries_path = Path(__file__).parent / "ground_truth" / "evaluation_queries.json"
    
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_path}")
    
    with open(queries_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_fidelity_evaluation(use_harness: bool = False) -> Dict:
    """
    Ejecuta evaluación de fidelidad completa.
    
    Args:
        use_harness: Si True, activa LIFE-HARNESS en el agente
    
    Returns:
        Diccionario con resultados de la evaluación
    """
    print("="*80)
    print("FIDELITY EVALUATION - Attention Is All You Need")
    print("="*80)
    
    # 1. Cargar ground truth
    print("\n[1/5] Loading paper from wiki...")
    try:
        paper_content = load_paper_from_wiki()
        print(f"✓ Loaded {len(paper_content)} chars")
    except Exception as e:
        print(f"✗ Error loading paper: {e}")
        return {"error": str(e)}
    
    # 2. Inicializar FidelityChecker
    print("\n[2/5] Initializing FidelityChecker...")
    checker = FidelityChecker(paper_content)
    print(f"✓ Extracted {len(checker.ground_truth_claims)} claims from ground truth")
    
    # 3. Cargar queries
    print("\n[3/5] Loading evaluation queries...")
    queries = load_evaluation_queries()
    print(f"✓ Loaded {len(queries)} queries")
    
    # 4. Inicializar servicio
    print("\n[4/5] Initializing agent service...")
    try:
        from app.service import AsubarnipalService
        service = AsubarnipalService(use_harness=use_harness)
        harness_status = "ENABLED" if use_harness else "DISABLED"
        print(f"✓ Service initialized (LIFE-HARNESS: {harness_status})")
    except Exception as e:
        print(f"✗ Error initializing service: {e}")
        return {"error": str(e)}
    
    # 5. Ejecutar queries
    print("\n[5/5] Running evaluation queries...")
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}/{len(queries)}: {query['id']}")
        print(f"{'='*80}")
        print(f"Question: {query['question']}")
        print(f"Difficulty: {query['difficulty']}")
        print(f"Expected claims: {query['expected_claims']}")
        
        # Ejecutar query
        start = time.time()
        try:
            response_dict = service.agent_chat(query['question'])
            duration = time.time() - start
            
            # Extraer string de respuesta del diccionario
            if isinstance(response_dict, dict):
                response = response_dict.get('response', '')
            else:
                response = str(response_dict)
            
            print(f"\nResponse ({len(response)} chars, {duration:.2f}s):")
            print(response[:500] + "..." if len(response) > 500 else response)
        except Exception as e:
            print(f"✗ Error executing query: {e}")
            results.append({
                "query_id": query['id'],
                "question": query['question'],
                "error": str(e),
                "score": 0.0,
            })
            continue
        
        # Verificar fidelidad
        print(f"\nVerifying fidelity...")
        report = checker.check_response(query['question'], response)
        
        # Verificar expected_claims manualmente
        response_lower = response.lower()
        missing_claims = []
        for claim in query['expected_claims']:
            if claim.lower() not in response_lower:
                missing_claims.append(claim)
        
        # Guardar resultado
        result = {
            "query_id": query['id'],
            "question": query['question'],
            "difficulty": query['difficulty'],
            "response": response,
            "score": report.score,
            "claims_detected": report.claims_detected,
            "claims_verified": report.claims_verified,
            "hallucinations": report.hallucinations,
            "omissions": report.omissions,
            "false_citations": report.false_citations,
            "missing_expected_claims": missing_claims,
            "duration_seconds": duration,
        }
        results.append(result)
        
        # Imprimir resultado
        print(f"\n{report.summary()}")
        if missing_claims:
            print(f"⚠️  Missing expected claims: {missing_claims}")
    
    # 6. Generar reporte
    report_data = generate_report(results, use_harness)
    
    # 7. Resumen
    print(f"\n{'='*80}")
    print("FIDELITY EVALUATION COMPLETE")
    print(f"{'='*80}")
    print(f"Average Score: {report_data['average_score']:.1f}/100")
    print(f"Total Queries: {len(results)}")
    print(f"Passed (≥70): {report_data['passed']}")
    print(f"Failed (<70): {report_data['failed']}")
    print(f"Total Hallucinations: {report_data['total_hallucinations']}")
    print(f"Total Omissions: {report_data['total_omissions']}")
    print(f"\nReport saved to: {report_data['report_path']}")
    
    return report_data


def generate_report(results: List[Dict], use_harness: bool) -> Dict:
    """Genera reporte JSON y Markdown de los resultados."""
    
    # Calcular métricas
    scores = [r['score'] for r in results if 'score' in r]
    avg_score = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for s in scores if s >= 70)
    failed = len(scores) - passed
    
    total_hallucinations = sum(len(r.get('hallucinations', [])) for r in results)
    total_omissions = sum(len(r.get('omissions', [])) for r in results)
    total_false_citations = sum(len(r.get('false_citations', [])) for r in results)
    
    # Crear reporte
    report = {
        "timestamp": datetime.now().isoformat(),
        "paper": "Attention Is All You Need",
        "harness_enabled": use_harness,
        "summary": {
            "total_queries": len(results),
            "passed": passed,
            "failed": failed,
            "average_score": round(avg_score, 1),
            "total_hallucinations": total_hallucinations,
            "total_omissions": total_omissions,
            "total_false_citations": total_false_citations,
        },
        "results": results,
    }
    
    # Guardar JSON
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    harness_suffix = "_harness" if use_harness else "_baseline"
    json_path = reports_dir / f"fidelity_{timestamp}{harness_suffix}.json"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Generar Markdown
    md_path = reports_dir / f"fidelity_{timestamp}{harness_suffix}.md"
    generate_markdown_report(report, md_path)
    
    report["report_path"] = str(json_path)
    report["markdown_path"] = str(md_path)
    
    return report


def generate_markdown_report(report: Dict, output_path: Path):
    """Genera reporte en formato Markdown."""
    lines = [
        f"# Fidelity Evaluation Report",
        f"",
        f"**Paper:** {report['paper']}",
        f"**Date:** {report['timestamp']}",
        f"**LIFE-HARNESS:** {'Enabled' if report['harness_enabled'] else 'Disabled'}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Queries | {report['summary']['total_queries']} |",
        f"| Passed (≥70) | {report['summary']['passed']} |",
        f"| Failed (<70) | {report['summary']['failed']} |",
        f"| Average Score | {report['summary']['average_score']:.1f}/100 |",
        f"| Total Hallucinations | {report['summary']['total_hallucinations']} |",
        f"| Total Omissions | {report['summary']['total_omissions']} |",
        f"| Total False Citations | {report['summary']['total_false_citations']} |",
        f"",
        f"## Detailed Results",
        f"",
    ]
    
    for result in report['results']:
        lines.extend([
            f"### {result['query_id']}: {result['question']}",
            f"",
            f"**Difficulty:** {result.get('difficulty', 'N/A')}",
            f"",
        ])
        
        if 'error' in result:
            lines.extend([
                f"**Error:** {result['error']}",
                f"",
            ])
            continue
        
        lines.extend([
            f"**Score:** {result['score']:.1f}/100",
            f"",
            f"**Claims:** {result['claims_verified']}/{result['claims_detected']} verified",
            f"",
        ])
        
        if result.get('hallucinations'):
            lines.extend([
                f"**Hallucinations ({len(result['hallucinations'])}):**",
                f"",
            ])
            for h in result['hallucinations']:
                lines.append(f"- {h}")
            lines.append("")
        
        if result.get('omissions'):
            lines.extend([
                f"**Omissions ({len(result['omissions'])}):**",
                f"",
            ])
            for o in result['omissions'][:5]:  # Limitar a 5
                lines.append(f"- {o}")
            lines.append("")
        
        if result.get('missing_expected_claims'):
            lines.extend([
                f"**Missing Expected Claims:**",
                f"",
            ])
            for claim in result['missing_expected_claims']:
                lines.append(f"- `{claim}`")
            lines.append("")
        
        lines.extend([
            f"**Response:**",
            f"",
            f"```",
            result['response'][:1000] + ("..." if len(result['response']) > 1000 else ""),
            f"```",
            f"",
            f"---",
            f"",
        ])
    
    # Guardar
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == "__main__":
    import sys
    
    # Parsear argumentos
    use_harness = "--harness" in sys.argv
    
    # Ejecutar evaluación
    run_fidelity_evaluation(use_harness=use_harness)
