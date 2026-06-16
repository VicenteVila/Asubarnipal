"""GGUF → PyTorch model adapter.

Loads GGUF models via llama.cpp and provides a PyTorch-compatible interface.
Falls back to a mock/placeholder if llama_cpp is not installed.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

import torch

logger = logging.getLogger(__name__)


class PyTorchModelAdapter:
    """Adaptador para convertir modelos GGUF a PyTorch.

    Args:
        gguf_path: Ruta al archivo GGUF del modelo.
        device: Dispositivo destino ('cpu' o 'cuda').
    """

    def __init__(self, gguf_path: str, device: str = "cpu"):
        self.gguf_path = gguf_path
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self._llama = None

    def load(self) -> "PyTorchModelAdapter":
        """Carga y convierte el modelo GGUF a PyTorch.

        Returns:
            self para encadenamiento.
        """
        if not Path(self.gguf_path).exists():
            raise FileNotFoundError(f"GGUF model not found: {self.gguf_path}")

        # 1. Cargar con llama.cpp
        llm = self._load_llama()

        # 2. Extraer pesos
        weights = self._extract_weights(llm)

        # 3. Crear modelo PyTorch
        self.model = self._create_pytorch_model(weights)

        # 4. Mover a dispositivo
        self.model = self.model.to(self.device)
        self.model.eval()

        logger.info(f"Model loaded: {Path(self.gguf_path).name} on {self.device}")
        return self

    def _load_llama(self):
        """Carga modelo con llama.cpp."""
        try:
            from llama_cpp import Llama
            self._llama = Llama(model_path=self.gguf_path, n_ctx=2048, verbose=False)
            return self._llama
        except ImportError:
            logger.warning("llama_cpp not installed. Using mock model.")
            return _MockLlama(self.gguf_path)

    def _extract_weights(self, llm) -> Dict[str, torch.Tensor]:
        """Extrae pesos del modelo GGUF.

        Returns:
            Dict con nombre del tensor → torch.Tensor.
        """
        if isinstance(llm, _MockLlama):
            return llm.get_mock_weights()

        weights = {}
        try:
            if hasattr(llm, "model") and hasattr(llm.model, "tensors"):
                for name, tensor in llm.model.tensors.items():
                    weights[name] = torch.from_numpy(tensor)
            elif hasattr(llm, "get_tensor"):
                for name in llm.get_tensor_names():
                    weights[name] = torch.from_numpy(llm.get_tensor(name))
        except Exception as e:
            logger.error(f"Failed to extract weights: {e}")
            raise

        return weights

    def _create_pytorch_model(self, weights: Dict[str, torch.Tensor]) -> torch.nn.Module:
        """Crea un modelo PyTorch simple desde los pesos extraídos.

        Para modelos reales, esto debería construir la arquitectura específica
        (LlamaForCausalLM, etc.). Aquí creamos un contenedor genérico.
        """
        model = _GenericWrapper(weights)
        return model

    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 128,
        temperature: float = 0.7,
    ) -> torch.Tensor:
        """Genera texto usando el modelo.

        Args:
            input_ids: Tensor de tokens de entrada [1, seq_len].
            max_new_tokens: Máximo de tokens a generar.
            temperature: Temperatura para sampling.

        Returns:
            Tensor con los tokens generados.
        """
        if self._llama is not None and not isinstance(self._llama, _MockLlama):
            import numpy as np
            text = self._llama.create_completion(
                prompt=self._llama.tokenizer.decode(input_ids[0].tolist()),
                max_tokens=max_new_tokens,
                temperature=temperature,
            )["choices"][0]["text"]
            return torch.tensor([self._llama.tokenizer.encode(text)])
        else:
            logger.warning("Mock model: returning random tokens")
            return torch.randint(0, 1000, (1, max_new_tokens))

    def get_device(self) -> str:
        return self.device

    def get_num_parameters(self) -> int:
        if self.model is None:
            return 0
        return sum(p.numel() for p in self.model.parameters())


class _MockLlama:
    """Mock de llama.cpp para cuando no está instalado."""

    def __init__(self, model_path: str):
        self.model_path = model_path

    def get_mock_weights(self) -> Dict[str, torch.Tensor]:
        return {
            "token_embd.weight": torch.randn(32000, 2048),
            "blk.0.attn_q.weight": torch.randn(2048, 2048),
            "blk.0.attn_k.weight": torch.randn(2048, 2048),
            "blk.0.attn_v.weight": torch.randn(2048, 2048),
            "blk.0.attn_output.weight": torch.randn(2048, 2048),
            "blk.0.ffn_gate.weight": torch.randn(2048, 8192),
            "blk.0.ffn_down.weight": torch.randn(8192, 2048),
            "blk.0.ffn_up.weight": torch.randn(2048, 8192),
            "output.weight": torch.randn(32000, 2048),
        }

    def get_tensor_names(self) -> list:
        return list(self.get_mock_weights().keys())

    def create_completion(self, **kwargs) -> dict:
        return {"choices": [{"text": "Mock response"}]}


class _GenericWrapper(torch.nn.Module):
    """Wrapper genérico que almacena pesos como parámetros."""

    def __init__(self, weights: Dict[str, torch.Tensor]):
        super().__init__()
        for name, tensor in weights.items():
            safe_name = name.replace(".", "_").replace("/", "_")
            self.register_parameter(safe_name, torch.nn.Parameter(tensor, requires_grad=False))

        self._weights = weights
        self.output_layer = torch.nn.Linear(2048, 32000, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.output_layer(x)

    def get_weights(self) -> Dict[str, torch.Tensor]:
        return self._weights
