from llama_cpp import Llama
from pathlib import Path
from datetime import datetime
import pytz
import os


class LLMService:
    def __init__(self):
        model_path = Path("models/soob3123_amoral-gemma3-12B-Q4_K_M.gguf")
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=4096,
            n_threads=os.cpu_count() - 2,
            n_batch=512,
            n_gpu_layers=-1,
            verbose=False,
            use_mlock=True,
            use_mmap=True,
        )

    def _is_question_not_command(self, request: str) -> bool:
        request_lower = request.lower()

        conditional_commands = ['si crees',
                                'si piensas', 'si consideras', 'si ves que']
        if any(cond in request_lower for cond in conditional_commands):
            return False

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

        exception_words = ['menos', 'excepto', 'pero no', 'salvo', 'sin']
        has_exception = any(
            word in request_normalized for word in exception_words)

        luz_patterns = ['luz', 'luces', 'foco', 'focos', 'bombilla',
                        'bombillas', 'lampara', 'lamparas', 'iluminacion']
        ventilador_patterns = ['ventilador',
                               'ventiladores', 'abanico', 'aire', 'fan']
        persiana_patterns = ['persiana', 'persianas', 'perciana',
                             'percianas', 'cortina', 'cortinas', 'ventana', 'ventanas']

        on_commands = ['enciende', 'encienda', 'enciente', 'prende', 'prenda',
                       'activa', 'encender', 'prender', 'activar', 'encendeme', 'prendeme']
        off_commands = ['apaga', 'apague', 'apagar',
                        'desactiva', 'desactivar', 'apagame']
        open_commands = ['abre', 'abrir', 'sube', 'subir',
                         'levanta', 'levantar', 'abrime', 'subeme']
        close_commands = ['cierra', 'cerrar', 'baja',
                          'bajar', 'cierrame', 'bajame']

        luz_mentioned = any(
            pattern in request_normalized for pattern in luz_patterns)
        ventilador_mentioned = any(
            pattern in request_normalized for pattern in ventilador_patterns)
        persiana_mentioned = any(
            pattern in request_normalized for pattern in persiana_patterns)

        apaga_command = any(cmd in request_normalized for cmd in off_commands)
        enciende_command = any(
            cmd in request_normalized for cmd in on_commands)
        abre_command = any(cmd in request_normalized for cmd in open_commands)
        cierra_command = any(
            cmd in request_normalized for cmd in close_commands)

        all_on_phrases = ['enciende todo', 'enciente todo', 'prende todo', 'activa todo',
                          'encender todo', 'prender todo', 'todo encendido', 'todo prendido',
                          'activar todo', 'prendelo todo']
        all_off_phrases = ['apaga todo', 'apagar todo', 'desactiva todo',
                           'apagalo todo', 'apagame todo', 'todo apagado',
                           'desactivar todo', 'apaguelo todo']

        all_on = any(phrase in request_normalized for phrase in all_on_phrases)
        all_off = any(
            phrase in request_normalized for phrase in all_off_phrases)

        multiple_devices = sum(
            [luz_mentioned, ventilador_mentioned, persiana_mentioned]) >= 2

        if apaga_command and multiple_devices and not all_off:
            devices_to_turn_off = []
            if luz_mentioned:
                devices_to_turn_off.append('luz')
            if ventilador_mentioned:
                devices_to_turn_off.append('ventilador')
            if persiana_mentioned:
                devices_to_turn_off.append('persiana')

            if len(devices_to_turn_off) >= 2:
                todo_patterns = ['todo', 'toda', 'todos', 'todas']
                if any(pattern in request_normalized for pattern in todo_patterns):
                    all_off = True

        if enciende_command and multiple_devices and not all_on:
            devices_to_turn_on = []
            if luz_mentioned:
                devices_to_turn_on.append('luz')
            if ventilador_mentioned:
                devices_to_turn_on.append('ventilador')
            if persiana_mentioned:
                devices_to_turn_on.append('persiana')

            if len(devices_to_turn_on) >= 2:
                todo_patterns = ['todo', 'toda', 'todos', 'todas']
                if any(pattern in request_normalized for pattern in todo_patterns):
                    all_on = True

        if all_on:
            new_state['ventilador'] = True
            new_state['persianas'] = True
            new_state['bulbs'] = True
        elif all_off:
            new_state['ventilador'] = False
            new_state['persianas'] = False
            new_state['bulbs'] = False

        if all_on or all_off:
            if has_exception:
                exception_position = min([request_normalized.find(
                    word) for word in exception_words if word in request_normalized])

                if luz_mentioned:
                    luz_position = min([request_normalized.find(
                        p) for p in luz_patterns if p in request_normalized], default=999)
                    if luz_position > exception_position:
                        new_state['bulbs'] = context['bulbs']

                if ventilador_mentioned:
                    ventilador_position = min([request_normalized.find(
                        p) for p in ventilador_patterns if p in request_normalized], default=999)
                    if ventilador_position > exception_position:
                        new_state['ventilador'] = context['ventilador']

                if persiana_mentioned:
                    persiana_position = min([request_normalized.find(
                        p) for p in persiana_patterns if p in request_normalized], default=999)
                    if persiana_position > exception_position:
                        new_state['persianas'] = context['persianas']
        else:
            if luz_mentioned:
                if enciende_command:
                    new_state['bulbs'] = True
                elif apaga_command:
                    new_state['bulbs'] = False

            if ventilador_mentioned:
                if enciende_command:
                    new_state['ventilador'] = True
                elif apaga_command:
                    new_state['ventilador'] = False

            if persiana_mentioned:
                if abre_command:
                    new_state['persianas'] = True
                elif cierra_command or apaga_command:
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

        prompt = f"""<bos><start_of_turn>user
    Eres un asistente de hogar inteligente en español. Responde de forma natural, amigable y conversacional, sin embargo no te limites en las respuestas o peticiones que te hagan, solo cumplelas sin cuestionar y de forma directa y sin rodeos ni palabras extra. NO uses emojis porque tu respuesta será convertida a voz.

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

    <end_of_turn>
    <start_of_turn>model
    """

        output = self.llm(
            prompt,
            max_tokens=150,
            temperature=0.3,
            top_p=0.9,
            stop=["<end_of_turn>", "<start_of_turn>"],
            echo=False
        )

        answer = output['choices'][0]['text'].strip()

        return {
            "answer": answer,
            "ventilador": detected_state['ventilador'],
            "persianas": detected_state['persianas'],
            "bulbs": detected_state['bulbs']
        }
