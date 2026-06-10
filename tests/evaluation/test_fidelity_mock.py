"""
Test rápido del FidelityChecker con respuestas mock.

Este script prueba el FidelityChecker sin necesidad de Ollama,
usando respuestas predefinidas para verificar la lógica de scoring.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from tests.evaluation.fidelity_checker import FidelityChecker, load_paper_from_wiki


# Respuestas mock para testing
MOCK_RESPONSES = {
    "q1_bleu_score": {
        "question": "¿Cuál es el BLEU score del Transformer big en WMT 2014 English-to-German?",
        "good_response": """
        The Transformer big achieved 28.4 BLEU on the WMT 2014 English-to-German translation task.
        This was a significant improvement over previous models.
        """,
        "bad_response": """
        The Transformer big achieved 35.7 BLEU on the WMT 2014 English-to-German translation task.
        It uses LSTM layers in the encoder.
        """,
    },
    "q2_parameters": {
        "question": "¿Cuántos parámetros tiene el Transformer big comparado con el base?",
        "good_response": """
        The Transformer big has 213 million parameters, while the base model has 65 million parameters.
        The big model is approximately 3.3x larger.
        """,
        "bad_response": """
        The Transformer big has 65 million parameters, while the base model has 213 million parameters.
        """,
    },
    "q3_architecture": {
        "question": "¿El Transformer usa LSTM, GRU o algún tipo de RNN?",
        "good_response": """
        No, the Transformer does not use LSTM, GRU, or any other type of RNN.
        It is based entirely on attention mechanisms, dispensing with recurrence and convolutions.
        """,
        "bad_response": """
        Yes, the Transformer uses LSTM layers in the encoder and GRU in the decoder.
        """,
    },
}


def test_fidelity_checker():
    """Prueba el FidelityChecker con respuestas mock."""
    print("="*80)
    print("FIDELITY CHECKER - Mock Response Test")
    print("="*80)
    
    # 1. Cargar paper
    print("\n[1/3] Loading paper from wiki...")
    try:
        paper_content = load_paper_from_wiki()
        print(f"✓ Loaded {len(paper_content)} chars")
    except Exception as e:
        print(f"✗ Error loading paper: {e}")
        return
    
    # 2. Inicializar checker
    print("\n[2/3] Initializing FidelityChecker...")
    checker = FidelityChecker(paper_content)
    print(f"✓ Extracted {len(checker.ground_truth_claims)} claims")
    
    # 3. Probar respuestas
    print("\n[3/3] Testing mock responses...")
    
    for query_id, test_data in MOCK_RESPONSES.items():
        print(f"\n{'='*80}")
        print(f"Query: {query_id}")
        print(f"{'='*80}")
        print(f"Question: {test_data['question']}")
        
        # Test buena respuesta
        print(f"\n--- Good Response ---")
        good_report = checker.check_response(
            test_data['question'],
            test_data['good_response']
        )
        print(good_report.summary())
        
        # Test mala respuesta
        print(f"\n--- Bad Response ---")
        bad_report = checker.check_response(
            test_data['question'],
            test_data['bad_response']
        )
        print(bad_report.summary())
        
        # Verificar que buena > mala
        if good_report.score > bad_report.score:
            print(f"\n✓ Good response scored higher ({good_report.score:.1f} vs {bad_report.score:.1f})")
        else:
            print(f"\n✗ WARNING: Bad response scored higher or equal!")


if __name__ == "__main__":
    test_fidelity_checker()
