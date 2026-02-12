# audio/services/llm_processor.py
import os
from llama_cpp import Llama

class LLMProcessor:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
        self.model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=6,
            n_batch=128,
            seed=3603909884,    
            n_gpu_layers=20,      # ← если у тебя GPU; иначе 0
            verbose=True          # ← чтобы видеть загрузку
        )

    def generate_questions(self, text: str):
        prompt = (
            "Проанализируй текст защиты проекта и выдели только основные смысловые вопросы, заданные студенту. "
            "Сформулируй вопросы кратко и точно на русском языке. Требования:\n"
            "1. Нумерованный список без дополнительных описаний\n"
            "2. Сохрани технические термины из оригинала\n"
            "3. Объедини повторяющиеся/схожие формулировки в один пункт\n"
            "4. В ответе не используй теги think и прочее\n"
            "5. Исключи мета-комментарии (например, 'Скажите...', 'Еще вопрос')\n"
            f"Текст для анализа: '{text}'"
        )

        try:
            response = self.model(
                prompt,
                max_tokens=500,
                temperature=0.6,
                top_p=0.95,
                top_k=40,
                repeat_penalty=1.0,
                stop=["<｜end▁of▁sentence｜>"],  # ← как в скрипте
            )
            return self._clean_output(response['choices'][0]['text'].strip())
        except Exception as e:
            print(f"Ошибка LLM: {e}")
            return []

    def _clean_output(self, text: str):
        """Очистка: оставляем только строки, заканчивающиеся на '?'"""
        questions = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Убираем нумерацию: "1. Как дела?" → "Как дела?"
            if line[0].isdigit():
                line = line.split('.', 1)[-1].strip()
            if line.endswith('?'):
                questions.append(line)
        return questions

    def close(self):
        """Освобождение ресурсов (опционально)"""
        if hasattr(self, 'model'):
            del self.model