# services/llm_processor.py
import os
from llama_cpp import Llama


class LLMProcessor:
    _instance = None

    def __init__(self):
        self.model = None
        self.load_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self):
        model_path = r"C:\Models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=6,
            n_batch=128,
            n_gpu_layers=20,
            verbose=False
        )

    def generate_questions(self, text):
        prompt = f"""Проанализируй текст и выдели основные смысловые вопросы. Требования:
1. Нумерованный список
2. Сохрани технические термины
3. Объедини повторяющиеся вопросы
4. Только вопросы

Текст: {text[:3000]}"""  # Обрезка текста до 3000 символов

        try:
            response = self.model(
                prompt,
                max_tokens=500,
                temperature=0.6,
                top_p=0.95,
                top_k=40,
                stop=["\n"]
            )
            return self.clean_output(response['choices'][0]['text'])
        except Exception as e:
            # Логирование ошибки и возврат пустого списка
            return []

    @staticmethod
    def clean_output(text):
        return [q.split('. ', 1)[-1] for q in text.split('\n') if q.strip()]