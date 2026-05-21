"""Chat mode handler (/charlar)."""

import random
from telegram import Update
from telegram.ext import CallbackContext

from core.bot_logger import logger
from .validators import validate_topic, validate_query


MODES = {
    "libre": {
        "name": "Charla Libre",
        "emoji": "💬",
        "system": """Eres un compañero de conversación creativo y natural.
Habla como un humano interesante, no como un robot.
- Sé conversacional, cálido, pero inteligente
- Haz preguntas para profundizar
- Comparte perspectivas personales cuando relevante
- No seas excesivamente formal
- Usa ejemplos de la vida real""",
        "welcome": "Iniciando conversación libre sobre"
    },
    "consultor": {
        "name": "Consultor",
        "emoji": "🧠",
        "system": """Eres un consultor senior de estrategia y análisis.
Analiza TODO tema en exactamente estas 3 fases:

1️⃣ *DEFINICIÓN* (¿Qué es?)
- Define el concepto con precisión
- Clarifica el contexto y alcance
- Identifica stakeholders clave

2️⃣ *EJECUCIÓN* (¿Cómo?)
- Propón un plan de acción concreto
- Lista los pasos específicos
- Considera recursos necesarios

3️⃣ *EVALUACIÓN* (¿Qué sigue?)
- Métricas de éxito
- Riesgos potenciales
- Próximos pasos recomendados

Siempre responde en estas 3 fases explícitamente marcadas.""",
        "welcome": "Iniciando análisis de consultor sobre"
    },
    "devil": {
        "name": "Devil's Advocate",
        "emoji": "🔥",
        "system": """Eres el crítico más ruthlessly honesto que existe.
Tu trabajo es encontrar TODOS los problemas, riesgos y fallos.

Para cada afirmación:
1. Encuentra 3 puntos débiles mínimos
2. Cuestiona las assumptions no dichas
3. Muestra casos donde esto ha fallado
4. Advierte sobre consecuencias no deseadas
5. Sugiere versiones mejores

Sé implacable pero constructivo. El objetivo es mejorar.""",
        "welcome": "Iniciando análisis crítico sobre"
    },
    "socratico": {
        "name": "Maestro Socrático",
        "emoji": "❓",
        "system": """Eres Sócrates. No das respuestas - haces preguntas que revelan la verdad.

Reglas de oro:
1. NUNCA des la respuesta directa
2. Cuestiona cada afirmación del usuario
3. Pide ejemplos concretos
4. Cuando el usuario dice "X", pregunta "¿Por qué X y no Y?"
5. Haz preguntas que revelen contradicciones
6. Conduce al usuario a su propia conclusión

Usa frases como:
- "¿Qué quieres decir exactamente con...?"
- "¿Cómo saberíamos si...?"
- "¿Siempre? ¿Hay excepciones?"
- "¿Qué pasaría si...?"?""",
        "welcome": "Iniciando diálogo socrático sobre"
    },
    "lateral": {
        "name": "Pensamiento Lateral",
        "emoji": "🌐",
        "system": """Eres un generador de perspectivas radicalmente diferentes.

Para cada tema, presenta EXACTAMENTE estas 5 visiones:

1️⃣ *Del Chef*: ¿Cómo lo cocinarías? ¿Ingredientes, método, presentación?
2️⃣ *Del Músico*: ¿Qué ritmo, melodía, armonía tiene este concepto?
3️⃣ *De la Tribu*: ¿Cómo lo explicaría un anciano de la aldea?
4️⃣ *Del Algoritmo*: ¿Qué lógica binaria lo define?
5️⃣ *Del Niño de 5 años*: ¿Qué pregunta naïve revelaría?

Sé creativo y sorprendente. No te limites a lo OBVIO.""",
        "welcome": "Explorando perspectivas alternativas sobre"
    }
}


async def charlar_cmd(update: Update, context: CallbackContext) -> None:
    """Chat with 5 specialized modes."""
    args = context.args

    if not args:
        text = """🎭 *Modos de Charla:*

1️⃣ 💬 *Libre* — Conversación natural y creativa
2️⃣ 🧠 *Consultor* — Análisis en 3 fases: Definición → Ejecución → Evaluación
3️⃣ 🔥 *Devil's Advocate* — Crítica implacable, encuentra fallos y riesgos
4️⃣ ❓ *Socrático* — Guía mediante preguntas, no da respuestas directas
5️⃣ 🌐 *Lateral* — Perspectivas alternativas de chef, músico, tribu, algoritmo

*Usa: /charlar <modo> <tema>*

*Ejemplos:*
• `/charlar libre ¿Qué opinas de la IA?`
• `/charlar consultor ¿Cómo mejorar este código?`
• `/charlar devil ¿Es buena idea este producto?`
• `/charlar socrático ¿Qué es la conciencia?`
• `/charlar lateral ¿Cómo percibirá un ninja este problema?`"""
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    mode = args[0].lower()
    topic = " ".join(args[1:])

    if not topic:
        await update.message.reply_text(
            "Usa: /charlar <modo> <tema>\n"
            "Ejemplo: /charlar consultor inteligencia artificial"
        )
        return

    valid, error = validate_topic(topic)
    if not valid:
        logger.warn(f"Charla topic inválido: {error}")
        await update.message.reply_text(f"❌ Tema inválido: {error}")
        return

    topic = topic.strip()
    mode_info = MODES[mode]

    text = f"""🎭 *{mode_info['name']} Activado* {mode_info['emoji']}

{mode_info['welcome']}: *{topic}*

---

{mode_info['system']}

---

Responde ahora según este modo."""
    await update.message.reply_text(text, parse_mode="Markdown")

    from app.service import AgentService
    service = AgentService()

    system_msg = {"role": "system", "content": mode_info["system"]}
    user_msg = {
        "role": "user",
        "content": f"Tema: {topic}\n\nPor favor, analiza este tema según las instrucciones del modo {mode_info['name']}."
    }

    try:
        try:
            from core.turboquant_engine import apply_chat_mode
            from core.turboquant_modes import get_mode_config
            
            mode_cfg = get_mode_config(mode)
            target_model = mode_cfg.model if mode_cfg else None
            
            apply_chat_mode(mode, model=target_model)
            result = service.llm.call_with_turbo([system_msg, user_msg], mode=mode, model=target_model)
            turbo_info = result.get("turbo", {})
            model_name = target_model or service.llm.model
            if turbo_info:
                logger.info(f"TQ mode {mode} applied: model={model_name}, ctx={turbo_info.get('context')}, "
                            f"cache_k={turbo_info.get('cache_k')}")
        except Exception as tq_err:
            logger.warn(f"TQ fallback for mode {mode}: {tq_err}")
            result = service.llm.call_agent([system_msg, user_msg])

        response = result.get("response", "Sin respuesta")[:3500]

        if response:
            tq_note = ""
            if turbo_info:
                tq_note = f"\n\n⚡ *{model_name}* | {turbo_info.get('context', 32)//1024}K ctx | {turbo_info.get('cache_k', '')}"

            await update.message.reply_text(
                f"💬 *Respuesta ({mode_info['name']}):*{tq_note}\n\n{response}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ No hubo respuesta del modelo.")
    except Exception as e:
        logger.error(f"Charla exception", exc=e)
        await update.message.reply_text(f"❌ Error inesperado en modo {mode}")