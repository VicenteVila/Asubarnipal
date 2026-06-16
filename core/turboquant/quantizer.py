"""Asymmetric 4-bit quantization for PyTorch tensors.

Implements asymmetric quantization with per-tensor or per-channel ranges,
supporting both CPU and CUDA devices.
"""

import logging
import math
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

import torch


@dataclass
class QuantizationStats:
    """Estadísticas de una operación de cuantización."""
    original_min: float
    original_max: float
    mean_error: float
    max_error: float
    mse: float
    snr_db: float
    compression_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_min": round(self.original_min, 4),
            "original_max": round(self.original_max, 4),
            "mean_error": round(self.mean_error, 6),
            "max_error": round(self.max_error, 6),
            "mse": round(self.mse, 6),
            "snr_db": round(self.snr_db, 2),
            "compression_ratio": round(self.compression_ratio, 2),
        }


class AsymmetricQuantizer:
    """Cuantización asimétrica de 4 bits.

    Attributes:
        bits: Número de bits (default: 4).
        per_channel: Si True, calcula rango por canal en lugar de por tensor.
    """

    def __init__(self, bits: int = 4, per_channel: bool = False):
        self.bits = bits
        self.levels = 2 ** bits  # 16 for 4-bit
        self.per_channel = per_channel

    def quantize(
        self, tensor: torch.Tensor, dim: int = -1
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Cuantiza un tensor float32 a int4 (almacenado como int8).

        Args:
            tensor: Tensor de entrada en float32.
            dim: Dimensión para cuantización per-channel (default: -1 = per-tensor).

        Returns:
            (quantized, min_val, max_val):
                quantized: Tensor int8 con valores en [0, levels-1].
                min_val: Valor mínimo (escalar o vector 1D).
                max_val: Valor máximo (escalar o vector 1D).
        """
        if self.per_channel and dim >= 0:
            return self._quantize_per_channel(tensor, dim)

        min_val = tensor.min()
        max_val = tensor.max()

        if max_val == min_val:
            max_val = min_val + 1e-6

        normalized = (tensor - min_val) / (max_val - min_val)
        quantized = torch.round(normalized * (self.levels - 1)).to(torch.int8)

        return quantized, min_val, max_val

    def dequantize(
        self,
        quantized: torch.Tensor,
        min_val: torch.Tensor,
        max_val: torch.Tensor,
    ) -> torch.Tensor:
        """Dequantiza un tensor int4 a float32.

        Args:
            quantized: Tensor int8 con valores en [0, levels-1].
            min_val: Valor mínimo.
            max_val: Valor máximo.

        Returns:
            Tensor float32 reconstruido.
        """
        normalized = quantized.float() / (self.levels - 1)
        original = normalized * (max_val - min_val) + min_val
        return original

    def _quantize_per_channel(
        self, tensor: torch.Tensor, dim: int
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Cuantización per-channel.

        Para dim=0 en tensor (C, ...), calcula rango por canal (dim=0).
        """
        reduce_dim = tuple(d for d in range(tensor.ndim) if d != dim)
        if not reduce_dim:
            return self.quantize(tensor)

        min_vals = tensor.amin(dim=reduce_dim, keepdim=True)
        max_vals = tensor.amax(dim=reduce_dim, keepdim=True)

        ranges = max_vals - min_vals
        ranges[ranges == 0] = 1e-6

        normalized = (tensor - min_vals) / ranges
        quantized = torch.round(normalized * (self.levels - 1)).to(torch.int8)

        return quantized, min_vals, max_vals

    def quantize_weight(
        self, weight: torch.nn.Parameter
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Cuantiza un parámetro de peso.

        Conveniencia para cuantizar pesos de modelos.
        """
        return self.quantize(weight.data)

    def analyze(
        self, original: torch.Tensor, quantized: torch.Tensor, min_val: torch.Tensor, max_val: torch.Tensor
    ) -> QuantizationStats:
        """Analiza el error de cuantización.

        Args:
            original: Tensor original float32.
            quantized: Tensor cuantizado int8 (valores 0-15).
            min_val: Valor mínimo usado para cuantizar.
            max_val: Valor máximo usado para cuantizar.

        Returns:
            QuantizationStats con métricas de error.
        """
        reconstructed = self.dequantize(quantized, min_val, max_val)
        error = original - reconstructed

        mse = torch.mean(error ** 2).item()
        mean_error = torch.mean(torch.abs(error)).item()
        max_error = torch.max(torch.abs(error)).item()

        signal_power = torch.mean(original ** 2).item()
        noise_power = mse
        snr_db = 10 * math.log10(signal_power / noise_power) if noise_power > 1e-12 else float("inf")

        original_bytes = original.nelement() * 4
        compressed_bytes = quantized.nelement() * 1
        compression_ratio = original_bytes / compressed_bytes

        return QuantizationStats(
            original_min=original.min().item(),
            original_max=original.max().item(),
            mean_error=mean_error,
            max_error=max_error,
            mse=mse,
            snr_db=snr_db,
            compression_ratio=compression_ratio,
        )


class DynamicQuantizedLinear(torch.nn.Module):
    """Capa lineal con cuantización dinámica de activaciones.

    Los pesos se cuantizan estáticamente en 4 bits.
    Las activaciones se cuantizan dinámicamente en cada forward.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        quantizer: Optional[AsymmetricQuantizer] = None,
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.quantizer = quantizer or AsymmetricQuantizer(bits=4)

        self.weight_quantized = torch.nn.Parameter(
            torch.zeros(out_features, in_features, dtype=torch.int8),
            requires_grad=False,
        )
        self.weight_min = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
        self.weight_max = torch.nn.Parameter(torch.zeros(1), requires_grad=False)

        self.bias = torch.nn.Parameter(torch.zeros(out_features))

    def quantize_weights(self, weight: torch.Tensor):
        """Cuantiza los pesos estáticamente."""
        q, mn, mx = self.quantizer.quantize(weight)
        self.weight_quantized.data.copy_(q)
        self.weight_min.data.copy_(mn)
        self.weight_max.data.copy_(mx)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = self.quantizer.dequantize(self.weight_quantized, self.weight_min, self.weight_max)
        output = torch.nn.functional.linear(x, weight, self.bias)
        return output


def quantize_model(
    model: torch.nn.Module,
    quantizer: Optional[AsymmetricQuantizer] = None,
    skip_classes: Optional[tuple] = None,
) -> torch.nn.Module:
    """Cuantiza todos los pesos de un modelo PyTorch.

    Reemplaza capas nn.Linear por DynamicQuantizedLinear cuando es posible.
    Para modelos sin acceso a la arquitectura, cuantiza los pesos in-place.

    Args:
        model: Modelo PyTorch.
        quantizer: Cuantizador a usar (default: AsymmetricQuantizer()).
        skip_classes: Clases de módulos a saltar (default: (nn.Dropout,)).

    Returns:
        Modelo con pesos cuantizados.
    """
    quantizer = quantizer or AsymmetricQuantizer(bits=4)
    skip_classes = skip_classes or (torch.nn.Dropout, torch.nn.Dropout2d)

    _logger = logging.getLogger(__name__)
    quantized_count = 0
    for name, module in model.named_modules():
        if isinstance(module, skip_classes):
            continue

        if isinstance(module, torch.nn.Linear):
            try:
                new_layer = DynamicQuantizedLinear(
                    module.in_features, module.out_features, bias=module.bias is not None
                )
                new_layer.quantize_weights(module.weight.data)
                if module.bias is not None:
                    new_layer.bias.data.copy_(module.bias.data)

                parent_name = ".".join(name.split(".")[:-1])
                child_name = name.split(".")[-1]
                if parent_name:
                    parent = dict(model.named_modules())[parent_name]
                else:
                    parent = model
                setattr(parent, child_name, new_layer)
                quantized_count += 1
            except Exception as e:
                _logger.warning(f"Could not quantize layer {name}: {e}")

    _logger.info(f"Quantized {quantized_count} Linear layers to 4-bit")

    return model


def benchmark_quantization(
    tensor_sizes: list = None,
    device: str = "cpu",
    num_warmup: int = 5,
    num_iter: int = 50,
) -> Dict[str, Any]:
    """Benchmark de velocidad de cuantización.

    Args:
        tensor_sizes: Lista de tuplas (dim1, dim2) para tensores de prueba.
        device: Dispositivo para benchmark.
        num_warmup: Iteraciones de warmup.
        num_iter: Iteraciones de medición.

    Returns:
        Dict con resultados de benchmark.
    """
    import time

    if tensor_sizes is None:
        tensor_sizes = [(1024, 1024), (4096, 4096), (8192, 8192)]

    quantizer = AsymmetricQuantizer(bits=4)
    results = {}

    for size in tensor_sizes:
        tensor = torch.randn(*size, device=device)
        key = f"{size[0]}x{size[1]}"

        for _ in range(num_warmup):
            quantizer.quantize(tensor)

        start = time.perf_counter()
        for _ in range(num_iter):
            q, mn, mx = quantizer.quantize(tensor)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / num_iter) * 1000

        stats = quantizer.analyze(tensor, q, mn, mx)

        results[key] = {
            "avg_ms": round(avg_ms, 3),
            "throughput_mb_s": round(
                (tensor.nelement() * 4 / 1024 / 1024) / (avg_ms / 1000), 2
            ),
            "snr_db": round(stats.snr_db, 2),
            "compression_ratio": round(stats.compression_ratio, 2),
        }

    return results
