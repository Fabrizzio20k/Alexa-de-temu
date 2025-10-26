from llama_cpp import Llama
import json
from pathlib import Path
from datetime import datetime
import pytz


class LLMService:
    def __init__(self):
        model_path = Path("models/llama-3.2-3b-instruct.gguf")
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=8,
            n_gpu_layers=0,
            verbose=False
        )

    def generate_smart_home_response(self, context: dict) -> dict:
        peru_tz = pytz.timezone('America/Lima')
        now = datetime.now(peru_tz)
        current_time = now.strftime("%I:%M %p")
        current_date = now.strftime("%A, %d de %B del %Y")

        system_prompt = "Eres un asistente de hogar inteligente en español, similar a Alexa.\n\nREGLA CRÍTICA: SOLO cambia el estado de un dispositivo si el usuario EXPLÍCITAMENTE lo pide con palabras como: enciende, apaga, abre, cierra, prende, etc.\n\nSi el usuario hace una PREGUNTA (hora, fecha, temperatura, clima), debes mantener TODOS los estados EXACTAMENTE como están actualmente.\n\nResponde SOLO con un objeto JSON válido:\n{\n  \"answer\": \"Tu respuesta\",\n  \"ventilador\": true o false,\n  \"persianas\": true o false,\n  \"bulbs\": true o false\n}\n\nEJEMPLOS CORRECTOS:\n\nUsuario: ¿Qué hora es?\nEstados actuales: ventilador=true, persianas=true, bulbs=true\nRespuesta: {\"answer\": \"Son las 3:30 PM\", \"ventilador\": true, \"persianas\": true, \"bulbs\": true}\n\nUsuario: Enciende el ventilador\nEstados actuales: ventilador=false, persianas=true, bulbs=true\nRespuesta: {\"answer\": \"Encendiendo el ventilador\", \"ventilador\": true, \"persianas\": true, \"bulbs\": true}\n\nUsuario: Apaga las luces\nEstados actuales: ventilador=true, persianas=true, bulbs=true\nRespuesta: {\"answer\": \"Apagando las luces\", \"ventilador\": true, \"persianas\": true, \"bulbs\": false}\n\nUsuario: ¿Cuál es la temperatura?\nEstados actuales: ventilador=false, persianas=false, bulbs=true\nRespuesta: {\"answer\": \"La temperatura es de 25 grados\", \"ventilador\": false, \"persianas\": false, \"bulbs\": true}\n\nRespuestas cortas y naturales como Alexa."

        ventilador_str = "encendido" if context['ventilador'] else "apagado"
        persianas_str = "abiertas" if context['persianas'] else "cerradas"
        bulbs_str = "encendidos" if context['bulbs'] else "apagados"

        user_message = f"INFORMACIÓN ACTUAL:\nHora: {current_time}\nFecha: {current_date}\nTemperatura: {context['temperature']}°C\nHumedad: {context['humidity']}%\nLuz ambiente: {context['light_quantity']}%\n\nESTADOS ACTUALES DE DISPOSITIVOS:\nVentilador: {ventilador_str} (actualmente: {context['ventilador']})\nPersianas: {persianas_str} (actualmente: {context['persianas']})\nFocos: {bulbs_str} (actualmente: {context['bulbs']})\n\nSOLICITUD DEL USUARIO: {context['request']}\n\nIMPORTANTE: Si el usuario solo pregunta algo, mantén los estados en: ventilador={context['ventilador']}, persianas={context['persianas']}, bulbs={context['bulbs']}\n\nRespuesta JSON:"

        prompt = f"{system_prompt}\n\n{user_message}"

        output = self.llm(
            prompt,
            max_tokens=150,
            temperature=0.2,
            top_p=0.9,
            stop=["\n\n", "Usuario:", "SOLICITUD"],
            echo=False
        )

        response_text = output['choices'][0]['text'].strip()

        if response_text.startswith("```"):
            response_text = response_text.replace(
                "```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(response_text)

            ventilador = parsed.get("ventilador")
            persianas = parsed.get("persianas")
            bulbs = parsed.get("bulbs")

            if not isinstance(ventilador, bool):
                ventilador = context['ventilador']
            if not isinstance(persianas, bool):
                persianas = context['persianas']
            if not isinstance(bulbs, bool):
                bulbs = context['bulbs']

            return {
                "answer": parsed.get("answer", "Lo siento, no entendí"),
                "ventilador": ventilador,
                "persianas": persianas,
                "bulbs": bulbs
            }
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {response_text}")
            return {
                "answer": "Lo siento, no pude procesar tu solicitud",
                "ventilador": context['ventilador'],
                "persianas": context['persianas'],
                "bulbs": context['bulbs']
            }
