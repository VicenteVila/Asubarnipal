# Fase 2: Aceleración de TurboQuant

**Prioridad**: 🟡 MEDIA  
**Estado**: Pendiente  
**Estimación**: 3-4 semanas  
**Dependencias**: PyTorch 2.0+, CUDA (opcional)

## Objetivo

Integrar PyTorch para cuantización de modelos y optimización con kernels CUDA, acelerando la inferencia en 2-4x y reduciendo el uso de RAM en 30%.

## Contexto

Actualmente Asubarnipal usa modelos GGUF con llama.cpp, que ya tiene cuantización de 4 bits. Sin embargo, PyTorch ofrece:
- Kernels CUDA optimizados para GPUs NVIDIA
- Cuantización dinámica con rangos asimétricos
- Mejor integración con el ecosistema ML
- Soporte para técnicas avanzadas (GPTQ, AWQ)

## Fundamentos Matemáticos

### Cuantización de 4 Bits con Rangos Asimétricos

**Fórmula:**
```
v_q = round((v - min) / (max - min) * 15)
```

**Donde:**
- `v`: valor original (float32)
- `min`, `max`: rango del tensor
- `v_q`: valor cuantizado (int4, 0-15)

**Ventajas sobre cuantización simétrica:**
- Mejor preservación de precisión en distribuciones asimétricas
- Reduce error de cuantización en 15-25%
- Compatible con activaciones ReLU (siempre positivas)

**Desquantización:**
```
v = v_q * (max - min) / 15 + min
```

## Especificación Técnica

### 1. Integración de PyTorch

#### 1.1 Instalación y Configuración

**Requisitos:**
```bash
# PyTorch con soporte CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Librerías de cuantización
pip install bitsandbytes accelerate transformers
```

**Verificación:**
```python
import torch

# Verificar CUDA
if torch.cuda.is_available():
    print(f"CUDA disponible: {torch.cuda.get_device_name(0)}")
    print(f"Memoria GPU: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("CUDA no disponible, usando CPU")
```

#### 1.2 Adaptador para Modelos GGUF

**Problema:** Los modelos GGUF no son directamente compatibles con PyTorch.

**Solución:** Crear un adaptador que:
1. Cargue el modelo GGUF con llama.cpp
2. Extraiga los pesos
3. Convierta a formato PyTorch
4. Aplique cuantización adicional si es necesario

**Implementación:**
```python
class PyTorchModelAdapter:
    """
    Adaptador para convertir modelos GGUF a PyTorch.
    """
    
    def __init__(self, gguf_path: str, device: str = 'cuda'):
        self.gguf_path = gguf_path
        self.device = device
        self.model = None
        self.tokenizer = None
    
    def load(self):
        """Carga y convierte el modelo."""
        # 1. Cargar con llama.cpp
        from llama_cpp import Llama
        llm = Llama(model_path=self.gguf_path)
        
        # 2. Extraer pesos (implementación específica del modelo)
        weights = self._extract_weights(llm)
        
        # 3. Crear modelo PyTorch
        self.model = self._create_pytorch_model(weights)
        
        # 4. Mover a GPU si está disponible
        if self.device == 'cuda' and torch.cuda.is_available():
            self.model = self.model.to('cuda')
        
        return self
    
    def _extract_weights(self, llm) -> dict:
        """Extrae pesos del modelo GGUF."""
        # Implementación específica para cada arquitectura
        pass
    
    def _create_pytorch_model(self, weights: dict):
        """Crea modelo PyTorch desde pesos."""
        # Implementación específica para cada arquitectura
        pass
```

### 2. Cuantización de 4 Bits

#### 2.1 Cuantización Estática

**Proceso:**
1. Calcular rango (min, max) de cada tensor
2. Aplicar fórmula de cuantización
3. Almacenar pesos cuantizados y parámetros de dequantización

**Implementación:**
```python
class AsymmetricQuantizer:
    """
    Cuantización asimétrica de 4 bits.
    """
    
    @staticmethod
    def quantize(tensor: torch.Tensor) -> tuple[torch.Tensor, float, float]:
        """
        Cuantiza tensor a 4 bits.
        
        Returns:
            - tensor_cuantizado: torch.Tensor (int8, 0-15)
            - min_val: float
            - max_val: float
        """
        min_val = tensor.min().item()
        max_val = tensor.max().item()
        
        # Evitar división por cero
        if max_val == min_val:
            max_val = min_val + 1e-6
        
        # Normalizar a [0, 15]
        normalized = (tensor - min_val) / (max_val - min_val)
        quantized = torch.round(normalized * 15).to(torch.int8)
        
        return quantized, min_val, max_val
    
    @staticmethod
    def dequantize(quantized: torch.Tensor, min_val: float, max_val: float) -> torch.Tensor:
        """
        Dequantiza tensor de 4 bits.
        
        Returns:
            - tensor_original: torch.Tensor (float32)
        """
        normalized = quantized.float() / 15.0
        original = normalized * (max_val - min_val) + min_val
        
        return original
```

#### 2.2 Cuantización Dinámica

**Problema:** Los rangos de activación varían durante la inferencia.

**Solución:** Cuantizar dinámicamente las activaciones en cada forward pass.

**Implementación:**
```python
class DynamicQuantizedLinear(torch.nn.Module):
    """
    Capa lineal con cuantización dinámica de activaciones.
    """
    
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        
        # Pesos cuantizados estáticamente
        self.weight_quantized = None
        self.weight_min = None
        self.weight_max = None
        
        # Bias en float32
        self.bias = torch.nn.Parameter(torch.zeros(out_features))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 1. Cuantizar activaciones dinámicamente
        x_quantized, x_min, x_max = AsymmetricQuantizer.quantize(x)
        
        # 2. Dequantizar pesos
        weight = AsymmetricQuantizer.dequantize(
            self.weight_quantized,
            self.weight_min,
            self.weight_max
        )
        
        # 3. Dequantizar activaciones
        x_dequant = AsymmetricQuantizer.dequantize(x_quantized, x_min, x_max)
        
        # 4. Calcular salida
        output = torch.nn.functional.linear(x_dequant, weight, self.bias)
        
        return output
```

### 3. Kernels CUDA Optimizados

#### 3.1 Kernel de Cuantización

**Objetivo:** Acelerar cuantización en GPU.

**Implementación CUDA:**
```cuda
__global__ void quantize_4bit_kernel(
    const float* input,
    int8_t* output,
    float* min_vals,
    float* max_vals,
    int size
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (idx < size) {
        // Calcular min/max (simplificado, en producción usar reducción paralela)
        float min_val = min_vals[blockIdx.x];
        float max_val = max_vals[blockIdx.x];
        
        // Normalizar y cuantizar
        float normalized = (input[idx] - min_val) / (max_val - min_val);
        output[idx] = (int8_t)roundf(normalized * 15.0f);
    }
}
```

**Wrapper PyTorch:**
```python
from torch.utils.cpp_extension import load

# Cargar kernel CUDA
quantize_cuda = load(
    name='quantize_cuda',
    sources=['quantize.cu', 'quantize_wrapper.cpp'],
    extra_cuda_cflags=['-O3'],
    verbose=True
)

def quantize_4bit_cuda(tensor: torch.Tensor) -> tuple[torch.Tensor, float, float]:
    """Versión CUDA de cuantización."""
    if not tensor.is_cuda:
        tensor = tensor.cuda()
    
    min_val = tensor.min().item()
    max_val = tensor.max().item()
    
    output = torch.empty_like(tensor, dtype=torch.int8)
    quantize_cuda.quantize(tensor, output, min_val, max_val)
    
    return output, min_val, max_val
```

#### 3.2 Kernel de MatMul Cuantizado

**Objetivo:** Acelerar multiplicación de matrices con pesos cuantizados.

**Estrategia:**
1. Dequantizar pesos en registros de GPU
2. Realizar MatMul en float32
3. Optimizar acceso a memoria

**Implementación:**
```python
class QuantizedMatMul(torch.autograd.Function):
    """MatMul optimizado para pesos cuantizados."""
    
    @staticmethod
    def forward(ctx, x, w_quantized, w_min, w_max, bias):
        # Dequantizar pesos
        w = AsymmetricQuantizer.dequantize(w_quantized, w_min, w_max)
        
        # MatMul estándar
        output = torch.matmul(x, w.t())
        
        if bias is not None:
            output += bias
        
        return output
    
    @staticmethod
    def backward(ctx, grad_output):
        # Implementar backward si es necesario para fine-tuning
        pass
```

### 4. Retención de Histórico en Memoria

#### 4.1 Caché de KV (Key-Value)

**Problema:** En modelos transformer, el caché de KV crece linealmente con la longitud de la secuencia.

**Solución:** Implementar políticas de eviction para limitar el uso de memoria.

**Implementación:**
```python
class KVEvictionPolicy:
    """Política de eviction para caché de KV."""
    
    def __init__(self, max_memory_gb: float = 4.0):
        self.max_memory_bytes = int(max_memory_gb * 1024**3)
        self.cache = {}
        self.access_times = {}
    
    def get(self, key: str) -> torch.Tensor:
        """Obtener valor del caché."""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def put(self, key: str, value: torch.Tensor):
        """Almacenar valor en caché."""
        # Verificar límite de memoria
        current_memory = self._get_memory_usage()
        value_size = value.element_size() * value.nelement()
        
        # Eviction si es necesario
        while current_memory + value_size > self.max_memory_bytes:
            self._evict_least_recent()
            current_memory = self._get_memory_usage()
        
        # Almacenar
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def _evict_least_recent(self):
        """Eliminar entrada menos recientemente usada."""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times, key=self.access_times.get)
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def _get_memory_usage(self) -> int:
        """Calcular uso de memoria actual."""
        total = 0
        for tensor in self.cache.values():
            total += tensor.element_size() * tensor.nelement()
        return total
```

#### 4.2 Compresión de Historial Conversacional

**Problema:** El historial de conversación crece indefinidamente.

**Solución:** Comprimir mensajes antiguos manteniendo solo resúmenes.

**Implementación:**
```python
class ConversationCompressor:
    """Compresor de historial conversacional."""
    
    def __init__(self, max_messages: int = 50, summary_threshold: int = 20):
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold
    
    def compress(self, messages: list[dict]) -> list[dict]:
        """
        Comprime historial de conversación.
        
        Estrategia:
        1. Mantener últimos N mensajes completos
        2. Resumir mensajes antiguos
        3. Preservar mensajes críticos (con herramientas, decisiones)
        """
        if len(messages) <= self.max_messages:
            return messages
        
        # Separar mensajes recientes y antiguos
        recent = messages[-self.max_messages:]
        old = messages[:-self.max_messages]
        
        # Filtrar mensajes críticos
        critical = [m for m in old if self._is_critical(m)]
        
        # Resumir mensajes no críticos
        non_critical = [m for m in old if not self._is_critical(m)]
        summary = self._summarize(non_critical)
        
        # Combinar
        compressed = []
        if summary:
            compressed.append({
                'role': 'system',
                'content': f"[Resumen de conversación anterior: {summary}]"
            })
        
        compressed.extend(critical)
        compressed.extend(recent)
        
        return compressed
    
    def _is_critical(self, message: dict) -> bool:
        """Determina si un mensaje es crítico."""
        content = message.get('content', '')
        
        # Mensajes con herramientas son críticos
        if 'tool_calls' in message or 'function_call' in message:
            return True
        
        # Mensajes con decisiones son críticos
        decision_keywords = ['decidí', 'decisión', 'conclusión', 'resultado']
        if any(kw in content.lower() for kw in decision_keywords):
            return True
        
        return False
    
    def _summarize(self, messages: list[dict]) -> str:
        """Resume mensajes no críticos."""
        if not messages:
            return ""
        
        # Concatenar contenido
        text = "\n".join([m.get('content', '') for m in messages])
        
        # Generar resumen (usar LLM o método extractivo)
        # Por simplicidad, usar resumen extractivo
        summary = self._extractive_summary(text, max_sentences=3)
        
        return summary
    
    def _extractive_summary(self, text: str, max_sentences: int = 3) -> str:
        """Genera resumen extractivo simple."""
        import re
        
        # Dividir en oraciones
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if len(sentences) <= max_sentences:
            return ". ".join(sentences)
        
        # Seleccionar primeras y últimas oraciones
        selected = sentences[:max_sentences//2] + sentences[-(max_sentences//2):]
        
        return ". ".join(selected)
```

## Tareas de Implementación

### Semana 1: Integración de PyTorch

- [ ] **Tarea 1.1**: Instalar PyTorch y dependencias
  - Archivo: `requirements.txt`
  - Añadir: torch, torchvision, torchaudio, bitsandbytes, accelerate
  - Estimación: 2 horas

- [ ] **Tarea 1.2**: Crear adaptador GGUF → PyTorch
  - Archivo: `core/turboquant/pytorch_adapter.py`
  - Clase: `PyTorchModelAdapter`
  - Estimación: 12 horas

- [ ] **Tarea 1.3**: Implementar cuantización asimétrica
  - Archivo: `core/turboquant/quantizer.py`
  - Clase: `AsymmetricQuantizer`
  - Estimación: 8 horas

### Semana 2: Kernels CUDA

- [ ] **Tarea 2.1**: Implementar kernel de cuantización CUDA
  - Archivo: `core/turboquant/cuda/quantize.cu`
  - Wrapper: `core/turboquant/cuda/quantize_wrapper.cpp`
  - Estimación: 10 horas

- [ ] **Tarea 2.2**: Implementar MatMul cuantizado
  - Archivo: `core/turboquant/quantized_ops.py`
  - Clase: `QuantizedMatMul`
  - Estimación: 8 horas

- [ ] **Tarea 2.3**: Benchmark y optimización
  - Archivo: `tests/benchmark_quantization.py`
  - Comparar: CPU vs GPU, float32 vs int4
  - Estimación: 6 horas

### Semana 3: Retención de Histórico

- [ ] **Tarea 3.1**: Implementar caché de KV con eviction
  - Archivo: `core/turboquant/kv_cache.py`
  - Clase: `KVEvictionPolicy`
  - Estimación: 8 horas

- [ ] **Tarea 3.2**: Implementar compresor de conversación
  - Archivo: `core/turboquant/conversation_compressor.py`
  - Clase: `ConversationCompressor`
  - Estimación: 8 horas

- [ ] **Tarea 3.3**: Integrar con `core/turboquant_engine.py`
  - Modificar: `TurboQuantEngine`
  - Añadir: cuantización, caché, compresión
  - Estimación: 6 horas

### Semana 4: Testing y Optimización

- [ ] **Tarea 4.1**: Tests unitarios
  - Archivo: `tests/test_quantization.py`
  - Cobertura: >90%
  - Estimación: 6 horas

- [ ] **Tarea 4.2**: Tests de integración
  - Archivo: `tests/test_turboquant_integration.py`
  - Validar: inferencia completa con cuantización
  - Estimación: 6 horas

- [ ] **Tarea 4.3**: Tests de performance
  - Archivo: `tests/benchmark_inference.py`
  - Medir: latencia, throughput, uso de memoria
  - Estimación: 6 horas

- [ ] **Tarea 4.4**: Optimización final
  - Ajustar: hiperparámetros, políticas de eviction
  - Estimación: 8 horas

## Criterios de Aceptación

### Funcionales

- [ ] Modelos GGUF cargados en PyTorch
- [ ] Cuantización de 4 bits funcional
- [ ] Kernels CUDA operativos (si hay GPU disponible)
- [ ] Caché de KV con eviction funcional
- [ ] Compresión de conversación funcional

### No Funcionales

- [ ] Inferencia 2-4x más rápida que baseline
- [ ] Reducción de 30% en uso de RAM
- [ ] Latencia < 1s para queries típicas
- [ ] Throughput > 10 queries/segundo

### Testing

- [ ] Tests unitarios (cobertura > 90%)
- [ ] Tests de integración (10+ escenarios)
- [ ] Tests de performance (benchmark completo)
- [ ] Validación de calidad (perplexity < 10% de degradación)

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Incompatibilidad GGUF → PyTorch | Alta | Alto | Implementar fallback a llama.cpp |
| Degradación de calidad | Media | Alto | Ajustar rangos de cuantización |
| CUDA no disponible | Media | Medio | Implementar versión CPU optimizada |
| Overhead de cuantización | Baja | Medio | Optimizar kernels y usar caché |

## Dependencias

- **PyTorch 2.0+**: Framework de ML
- **CUDA 11.8+**: Para kernels GPU (opcional)
- **bitsandbytes**: Librería de cuantización
- **accelerate**: Optimización de inferencia
- **transformers**: Modelos y tokenizers

## Recursos Necesarios

- **Desarrollo**: 1 desarrollador ML, 3-4 semanas
- **Testing**: 1 tester, 1 semana
- **Hardware**: GPU NVIDIA con 8GB+ VRAM (recomendado)

## Métricas de Éxito

| Métrica | Actual | Objetivo | Medición |
|---------|--------|----------|----------|
| Latencia de inferencia | ~3s | ~1s | Benchmark |
| Uso de RAM | ~8GB | ~5.6GB | Monitor de sistema |
| Throughput | ~3 q/s | ~10 q/s | Benchmark |
| Perplexity | Baseline | <10% degradación | Evaluación |

## Referencias

- **Análisis completo**: [Arquitectura-comparativa.pdf](./Arquitectura-comparativa.pdf) (páginas 4-5, 8-9)
- **TurboQuant actual**: `core/turboquant_engine.py`
- **PyTorch Quantization**: https://pytorch.org/docs/stable/quantization.html
- **bitsandbytes**: https://github.com/TimDettmers/bitsandbytes

---

**Última actualización**: 2026-06-10  
**Versión**: 1.0  
**Autor**: Análisis arquitectónico comparativo
