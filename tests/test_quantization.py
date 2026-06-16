"""Tests for TurboQuant quantization modules."""

import torch
import pytest

from core.turboquant.quantizer import (
    AsymmetricQuantizer,
    DynamicQuantizedLinear,
    QuantizationStats,
    quantize_model,
    benchmark_quantization,
)
from core.turboquant.pytorch_adapter import PyTorchModelAdapter, _MockLlama
from core.turboquant.verify_deps import check_deps, print_status


class TestCheckDeps:
    def test_check_deps_returns_dict(self):
        results = check_deps()
        assert isinstance(results, dict)
        assert "torch" in results
        assert "transformers" in results
        assert "accelerate" in results

    def test_torch_is_installed(self):
        results = check_deps()
        ok, detail = results["torch"]
        assert ok
        assert "cpu" in detail or "cu" in detail


class TestAsymmetricQuantizer:
    def test_quantize_dequantize_identity(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.tensor([0.0, 0.5, 1.0])
        q_t, mn, mx = q.quantize(t)
        d = q.dequantize(q_t, mn, mx)
        assert torch.allclose(t, d, atol=0.1)

    def test_quantize_uniform_range(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.linspace(0, 1, 100)
        q_t, mn, mx = q.quantize(t)
        assert mn == 0.0
        assert mx == 1.0
        assert q_t.min() == 0
        assert q_t.max() == 15

    def test_quantize_negative_values(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.tensor([-1.0, -0.5, 0.0, 0.5, 1.0])
        q_t, mn, mx = q.quantize(t)
        d = q.dequantize(q_t, mn, mx)
        assert torch.allclose(t, d, atol=0.1)

    def test_quantize_single_value(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.ones(10)
        q_t, mn, mx = q.quantize(t)
        assert mx.item() > mn.item()
        assert q_t.unique().numel() <= 2

    def test_quantize_2d_tensor(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.randn(32, 64)
        q_t, mn, mx = q.quantize(t)
        assert q_t.shape == t.shape
        assert q_t.dtype == torch.int8

    def test_quantize_per_channel(self):
        q = AsymmetricQuantizer(bits=4, per_channel=True)
        t = torch.randn(8, 64)
        q_t, mn, mx = q.quantize(t, dim=0)
        assert q_t.shape == t.shape
        assert len(mn.shape) == 2
        assert mn.shape[-1] == 1
        assert mn.shape[0] == 8

    def test_quantize_per_channel_dim1(self):
        q = AsymmetricQuantizer(bits=4, per_channel=True)
        t = torch.randn(8, 64)
        q_t, mn, mx = q.quantize(t, dim=1)
        assert q_t.shape == t.shape
        assert mn.shape[-1] == 64
        assert mn.shape[0] == 1

    def test_dequantize_preserves_shape(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.randn(16, 16)
        q_t, mn, mx = q.quantize(t)
        d = q.dequantize(q_t, mn, mx)
        assert d.shape == t.shape
        assert d.dtype == torch.float32

    def test_quantize_weight_convenience(self):
        q = AsymmetricQuantizer(bits=4)
        w = torch.nn.Parameter(torch.randn(128, 256))
        q_t, mn, mx = q.quantize_weight(w)
        assert q_t.shape == (128, 256)


class TestQuantizationStats:
    def test_analyze_returns_stats(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.randn(100)
        q_t, mn, mx = q.quantize(t)
        stats = q.analyze(t, q_t, mn, mx)
        assert isinstance(stats, QuantizationStats)
        assert stats.mean_error >= 0
        assert stats.mse >= 0
        assert stats.snr_db > 0
        assert stats.compression_ratio == 4.0

    def test_analyze_perfect_reconstruction(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.tensor([0.0, 0.25, 0.5, 0.75, 1.0])
        q_t, mn, mx = q.quantize(t)
        stats = q.analyze(t, q_t, mn, mx)
        assert stats.mean_error < 0.05
        assert stats.mse < 0.01

    def test_stats_to_dict_keys(self):
        q = AsymmetricQuantizer(bits=4)
        t = torch.randn(50)
        q_t, mn, mx = q.quantize(t)
        stats = q.analyze(t, q_t, mn, mx)
        d = stats.to_dict()
        expected_keys = {"original_min", "original_max", "mean_error", "max_error", "mse", "snr_db", "compression_ratio"}
        assert expected_keys.issubset(d.keys())


class TestDynamicQuantizedLinear:
    def test_forward_shape(self):
        dql = DynamicQuantizedLinear(64, 128)
        dql.quantize_weights(torch.randn(128, 64))
        x = torch.randn(4, 64)
        out = dql(x)
        assert out.shape == (4, 128)

    def test_quantize_weights_updates_params(self):
        dql = DynamicQuantizedLinear(32, 16)
        w = torch.randn(16, 32)
        dql.quantize_weights(w)
        assert dql.weight_quantized.shape == (16, 32)
        assert dql.weight_quantized.dtype == torch.int8

    def test_forward_batch(self):
        dql = DynamicQuantizedLinear(10, 5)
        dql.quantize_weights(torch.randn(5, 10))
        x = torch.randn(2, 10)
        out = dql(x)
        assert out.shape == (2, 5)

    def test_bias_is_learnable(self):
        dql = DynamicQuantizedLinear(8, 4, bias=True)
        assert dql.bias.requires_grad is True


class TestQuantizeModel:
    def test_quantize_simple_model(self):
        model = torch.nn.Sequential(
            torch.nn.Linear(64, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, 10),
        )
        q_model = quantize_model(model)
        x = torch.randn(4, 64)
        out = q_model(x)
        assert out.shape == (4, 10)

    def test_quantize_model_with_dropout(self):
        model = torch.nn.Sequential(
            torch.nn.Linear(64, 128),
            torch.nn.Dropout(0.5),
            torch.nn.Linear(128, 10),
        )
        q_model = quantize_model(model)
        x = torch.randn(4, 64)
        out = q_model(x)
        assert out.shape == (4, 10)

    def test_quantize_empty_model(self):
        model = torch.nn.Sequential()
        q_model = quantize_model(model)
        assert q_model is not None

    def test_quantize_preserves_structure(self):
        model = torch.nn.Sequential(
            torch.nn.Linear(10, 20),
            torch.nn.Linear(20, 5),
        )
        q_model = quantize_model(model)
        assert len(q_model) == 2


class TestBenchmarkQuantization:
    def test_benchmark_returns_dict(self):
        results = benchmark_quantization(
            tensor_sizes=[(64, 64)],
            device="cpu",
            num_warmup=2,
            num_iter=5,
        )
        assert "64x64" in results
        assert "avg_ms" in results["64x64"]
        assert results["64x64"]["compression_ratio"] == 4.0

    def test_benchmark_multiple_sizes(self):
        results = benchmark_quantization(
            tensor_sizes=[(32, 32), (64, 64)],
            device="cpu",
            num_warmup=1,
            num_iter=3,
        )
        assert len(results) == 2


class TestPytorchAdapter:
    def test_adapter_creation(self):
        adapter = PyTorchModelAdapter("/fake/model.gguf")
        assert adapter.device == "cpu"
        assert adapter.model is None

    def test_adapter_with_cuda_fallback(self):
        adapter = PyTorchModelAdapter("/fake/model.gguf", device="cuda")
        assert adapter.device == "cpu"

    def test_mock_llama(self):
        mock = _MockLlama("/fake/model.gguf")
        weights = mock.get_mock_weights()
        assert len(weights) > 0
        assert "output.weight" in weights

    def test_mock_llama_tensor_shapes(self):
        mock = _MockLlama("/fake/model.gguf")
        weights = mock.get_mock_weights()
        for name, tensor in weights.items():
            assert isinstance(tensor, torch.Tensor)

    def test_adapter_get_num_params_no_model(self):
        adapter = PyTorchModelAdapter("/fake/model.gguf")
        assert adapter.get_num_parameters() == 0

    def test_verify_deps_runs(self):
        results = check_deps()
        assert isinstance(results, dict)
