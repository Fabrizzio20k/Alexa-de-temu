from llama_cpp import Llama
from pathlib import Path
from datetime import datetime
import pytz


class LLMService:
    def __init__(self):
        model_path = Path("models/qwen2.5-3b-instruct-q4_k_m.gguf")
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=24,
            n_batch=512,
            n_gpu_layers=0,
            verbose=False
        )

    def _is_question_not_command(self, request: str) -> bool:
        request_lower = request.lower()
        question_indicators = [
            '¿', '?',
            'debería', 'deberia', 'debo', 'puedo', 'podría', 'podria',
            'recomiendas', 'recomendarias', 'recomienda', 'recomendarías',
            'crees que', 'cree que', 'piensas que', 'opinas',
            'qué hago', 'que hago', 'qué haces', 'que haces',
            'conviene', 'mejor', 'peor', 'sugieres', 'aconsejas',
            'es buena idea', 'es mala idea', 'está bien', 'esta bien',
            'como ves', 'qué te parece', 'que te parece',
            'necesito', 'hace falta', 'tendría que', 'tendria que'
        ]
        return any(indicator in request_lower for indicator in question_indicators)

    def _normalize_text(self, text: str) -> str:
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ü': 'u', 'ñ': 'n'
        }
        text_lower = text.lower()
        for old, new in replacements.items():
            text_lower = text_lower.replace(old, new)
        return text_lower

    def _detect_device_commands(self, request: str, context: dict) -> dict:
        request_lower = request.lower()
        request_normalized = self._normalize_text(request)

        if self._is_question_not_command(request):
            return {
                'ventilador': context['ventilador'],
                'persianas': context['persianas'],
                'bulbs': context['bulbs']
            }

        new_state = {
            'ventilador': context['ventilador'],
            'persianas': context['persianas'],
            'bulbs': context['bulbs']
        }

        exception_words = ['menos', 'excepto', 'pero no', 'salvo',
                           'sin', 'menos el', 'menos la', 'menos las', 'menos los']
        has_exception = any(
            word in request_normalized for word in exception_words)

        luz_patterns = ['luz', 'luces', 'foco', 'focos', 'bombilla',
                        'bombillas', 'lampara', 'lamparas', 'iluminacion']
        ventilador_patterns = ['ventilador',
                               'ventiladores', 'abanico', 'aire', 'fan']
        persiana_patterns = ['persiana', 'persianas',
                             'cortina', 'cortinas', 'ventana', 'ventanas']

        on_commands = ['enciende', 'encienda', 'prende', 'prenda', 'activa',
                       'encender', 'prender', 'activar', 'encendeme', 'prendeme']
        off_commands = ['apaga', 'apague', 'apagar',
                        'desactiva', 'desactivar', 'apagame']
        open_commands = ['abre', 'abrir', 'sube', 'subir',
                         'levanta', 'levantar', 'abrime', 'subeme']
        close_commands = ['cierra', 'cerrar',
                          'baja', 'bajar', 'cierrame', 'bajame']

        all_on = any(phrase in request_normalized for phrase in [
                     'enciende todo', 'prende todo', 'activa todo', 'encender todo', 'prender todo', 'todo encendido', 'todo prendido'])
        all_off = any(phrase in request_normalized for phrase in [
                      'apaga todo', 'apagar todo', 'desactiva todo', 'apagalo todo', 'apagame todo', 'todo apagado'])

        if all_off:
            new_state['ventilador'] = False
            new_state['persianas'] = False
            new_state['bulbs'] = False

            if has_exception:
                luz_mentioned = any(
                    pattern in request_normalized for pattern in luz_patterns)
                ventilador_mentioned = any(
                    pattern in request_normalized for pattern in ventilador_patterns)
                persiana_mentioned = any(
                    pattern in request_normalized for pattern in persiana_patterns)

                exception_position = min([request_normalized.find(
                    word) for word in exception_words if word in request_normalized])

                luz_position = min([request_normalized.find(
                    p) for p in luz_patterns if p in request_normalized], default=999)
                ventilador_position = min([request_normalized.find(
                    p) for p in ventilador_patterns if p in request_normalized], default=999)
                persiana_position = min([request_normalized.find(
                    p) for p in persiana_patterns if p in request_normalized], default=999)

                if luz_mentioned and luz_position > exception_position:
                    new_state['bulbs'] = context['bulbs']
                if ventilador_mentioned and ventilador_position > exception_position:
                    new_state['ventilador'] = context['ventilador']
                if persiana_mentioned and persiana_position > exception_position:
                    new_state['persianas'] = context['persianas']

        elif all_on:
            new_state['ventilador'] = True
            new_state['persianas'] = True
            new_state['bulbs'] = True

            if has_exception:
                luz_mentioned = any(
                    pattern in request_normalized for pattern in luz_patterns)
                ventilador_mentioned = any(
                    pattern in request_normalized for pattern in ventilador_patterns)
                persiana_mentioned = any(
                    pattern in request_normalized for pattern in persiana_patterns)

                exception_position = min([request_normalized.find(
                    word) for word in exception_words if word in request_normalized])

                luz_position = min([request_normalized.find(
                    p) for p in luz_patterns if p in request_normalized], default=999)
                ventilador_position = min([request_normalized.find(
                    p) for p in ventilador_patterns if p in request_normalized], default=999)
                persiana_position = min([request_normalized.find(
                    p) for p in persiana_patterns if p in request_normalized], default=999)

                if luz_mentioned and luz_position > exception_position:
                    new_state['bulbs'] = context['bulbs']
                if ventilador_mentioned and ventilador_position > exception_position:
                    new_state['ventilador'] = context['ventilador']
                if persiana_mentioned and persiana_position > exception_position:
                    new_state['persianas'] = context['persianas']
        else:
            luz_mentioned = any(
                pattern in request_normalized for pattern in luz_patterns)
            ventilador_mentioned = any(
                pattern in request_normalized for pattern in ventilador_patterns)
            persiana_mentioned = any(
                pattern in request_normalized for pattern in persiana_patterns)

            if luz_mentioned:
                if any(cmd in request_normalized for cmd in on_commands):
                    new_state['bulbs'] = True
                elif any(cmd in request_normalized for cmd in off_commands):
                    new_state['bulbs'] = False

            if ventilador_mentioned:
                if any(cmd in request_normalized for cmd in on_commands):
                    new_state['ventilador'] = True
                elif any(cmd in request_normalized for cmd in off_commands):
                    new_state['ventilador'] = False

            if persiana_mentioned:
                if any(cmd in request_normalized for cmd in open_commands):
                    new_state['persianas'] = True
                elif any(cmd in request_normalized for cmd in close_commands):
                    new_state['persianas'] = False

        return new_state

    def generate_smart_home_response(self, context: dict) -> dict:
        peru_tz = pytz.timezone('America/Lima')
        now = datetime.now(peru_tz)
        current_time = now.strftime("%I:%M %p")
        current_date = now.strftime("%A, %d de %B del %Y")

        detected_state = self._detect_device_commands(
            context['request'], context)

        ventilador_str = "encendido" if detected_state['ventilador'] else "apagado"
        persianas_str = "abiertas" if detected_state['persianas'] else "cerradas"
        bulbs_str = "encendidas" if detected_state['bulbs'] else "apagadas"

        is_question = self._is_question_not_command(context['request'])

        changed_devices = []
        if detected_state['ventilador'] != context['ventilador']:
            changed_devices.append(
                f"ventilador {'encendido' if detected_state['ventilador'] else 'apagado'}")
        if detected_state['persianas'] != context['persianas']:
            changed_devices.append(
                f"persianas {'abiertas' if detected_state['persianas'] else 'cerradas'}")
        if detected_state['bulbs'] != context['bulbs']:
            changed_devices.append(
                f"luces {'encendidas' if detected_state['bulbs'] else 'apagadas'}")

        if is_question:
            action_context = "El usuario está haciendo una PREGUNTA. Responde con tu recomendación u opinión basada en las condiciones actuales."
        elif changed_devices:
            action_context = f"Se han realizado los siguientes cambios: {', '.join(changed_devices)}. Confirma las acciones de forma natural."
        else:
            action_context = "No se han realizado cambios en los dispositivos. Responde apropiadamente."

        prompt = f"""<|im_start|>system
Eres un asistente de hogar inteligente en español llamado Alexa. Responde de forma natural, amigable y conversacional. NO uses emojis porque tu respuesta será convertida a voz.<|im_end|>
<|im_start|>user
INFORMACIÓN ACTUAL:
Hora: {current_time}
Fecha: {current_date}
Temperatura: {context['temperature']}°C
Humedad: {context['humidity']}%
Luz ambiente: {context['light_quantity']}%

ESTADOS ACTUALES DE DISPOSITIVOS:
Ventilador: {ventilador_str}
Persianas: {persianas_str}
Luces: {bulbs_str}

SOLICITUD DEL USUARIO: {context['request']}

CONTEXTO: {action_context}

Responde de forma natural, breve y amigable.<|im_end|>
<|im_start|>assistant
"""

        output = self.llm(
            prompt,
            max_tokens=150,
            temperature=0.3,
            top_p=0.9,
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False
        )

        answer = output['choices'][0]['text'].strip()

        return {
            "answer": answer,
            "ventilador": detected_state['ventilador'],
            "persianas": detected_state['persianas'],
            "bulbs": detected_state['bulbs']
        }
