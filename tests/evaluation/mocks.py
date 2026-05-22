"""Extended mocks for evaluation testing."""

import asyncio
from unittest.mock import Mock, AsyncMock


class MockMessage:
    """Mock Telegram Message that captures responses."""

    def __init__(self):
        self.text = "test"
        self._reply = None
        self._reply_markup = None
        self.document = None
        self.photo = None
        self.voice = None
        self.audio = None

    async def reply_text(self, text, parse_mode=None, reply_markup=None, **kwargs):
        self._reply = text
        self._reply_markup = reply_markup
        return Mock()


class MockUpdate:
    """Mock Telegram Update with flexible configuration."""

    def __init__(self, user_id=12345, first_name="EvalUser", args=None):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.first_name = first_name
        self.message = MockMessage()
        self.effective_message = self.message
        self.callback_query = Mock()
        self.callback_query.data = None
        self.callback_query.answer = AsyncMock()
        self.callback_query.edit_message_text = AsyncMock()
        self._args = args or []


class MockContext:
    """Mock Telegram CallbackContext."""

    def __init__(self, args=None):
        self.args = args or []
        self.user_data = {}
        self.bot = Mock()
        self.bot.get_file = AsyncMock()


def run_async(coro):
    """Run async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_handler_test(handler_fn, args=None, user_id=12345):
    """Create a test harness for a command handler.

    Returns (update, context, response_text, reply_markup).
    """
    update = MockUpdate(user_id=user_id, args=args)
    context = MockContext(args=args)
    run_async(handler_fn(update, context))
    return update, context, update.message._reply, update.message._reply_markup


def create_callback_test(handler_fn, callback_data, user_id=12345):
    """Create a test harness for a callback handler.

    Returns (update, context, edited_text).
    """
    update = MockUpdate(user_id=user_id)
    update.callback_query.data = callback_data
    context = MockContext()
    run_async(handler_fn(update, context))
    call_args = update.callback_query.edit_message_text.call_args
    edited_text = call_args[0][0] if call_args else ""
    return update, context, edited_text


class MockLLMResponse:
    """Mock LLM response generator."""

    RESPONSES = {
        "attention": "El mecanismo de attention permite al modelo pesar diferentes partes de la entrada de forma dinamica. Los pesos de attention se calculan mediante productos escalares entre queries y keys.",
        "transformer": "Un transformer consiste en encoder y decoder. El encoder procesa la entrada completa con self-attention, mientras el decoder genera la salida autoregresivamente.",
        "rag": "RAG (Retrieval-Augmented Generation) combina retrieval de documentos con generacion de texto. Primero busca documentos relevantes, luego genera una respuesta usando ese contexto.",
        "fine_tuning": "Fine-tuning es el proceso de ajustar un modelo pre-entrenado con datos especificos de un dominio. Permite adaptar modelos generales a tareas particulares.",
        "consultor": "FASE 1 - DEFINICION: El problema de optimizar un pipeline RAG implica mejorar la relevancia de retrieval y la calidad de generacion.\n\nFASE 2 - EJECUCION: Propongo implementar hybrid search con BM25 + embeddings.\n\nFASE 3 - EVALUACION: Medir precision con metricas de retrieval.",
        "devil": "Riesgos identificados:\n1. Responsabilidad legal: un diagnostico erroneo puede causar dano al paciente.\n2. Alucinaciones: los LLMs inventan informacion medica.\n3. Sesgo: los datos de entrenamiento pueden no representar la diversidad de pacientes.\n4. Limitacion tecnica: no tienen conocimiento clinico real.",
        "libre": "Las tendencias mas relevantes incluyen agentes autonomos, modelos multimodales, y sistemas RAG avanzados. La IA generativa esta transformando industrias.",
        "socratico": "Que entiendes por consciencia? Como definirias la diferencia entre procesar informacion y ser consciente de ella?",
        "lateral": "Desde la perspectiva de un ninja: la arquitectura de software es como un dojo - cada componente tiene su lugar, la eficiencia es clave, y la simplicidad vence a la complejidad.",
        "default": "Esta es una respuesta generada para evaluacion del sistema.",
    }

    @classmethod
    def get(cls, query: str) -> str:
        query_lower = query.lower()
        for key, response in cls.RESPONSES.items():
            if key in query_lower:
                return response
        return cls.RESPONSES["default"]


class MockBraveResponse:
    """Mock Brave Search response."""

    RESULTS = {
        "default": [
            {
                "title": "Understanding Neural Networks",
                "url": "https://example.com/neural-networks",
                "snippet": "Neural networks are computing systems inspired by biological neural networks.",
            },
            {
                "title": "Deep Learning Fundamentals",
                "url": "https://example.com/deep-learning",
                "snippet": "Deep learning is a subset of machine learning using neural networks.",
            },
            {
                "title": "AI Research Papers 2024",
                "url": "https://example.com/ai-papers",
                "snippet": "Latest research papers on artificial intelligence and machine learning.",
            },
        ],
        "attention": [
            {
                "title": "Attention Is All You Need",
                "url": "https://arxiv.org/abs/1706.03762",
                "snippet": "The Transformer model based solely on attention mechanisms.",
            },
            {
                "title": "Self-Attention Mechanism Explained",
                "url": "https://example.com/self-attention",
                "snippet": "How self-attention works in transformer architectures.",
            },
        ],
    }

    @classmethod
    def get(cls, query: str) -> list[dict]:
        query_lower = query.lower()
        for key, results in cls.RESULTS.items():
            if key in query_lower:
                return results
        return cls.RESULTS["default"]
