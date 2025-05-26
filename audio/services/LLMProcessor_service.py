# services/llm_processor.py
import os
from llama_cpp import Llama

import os
from llama_cpp import Llama
import logging

logger = logging.getLogger(__name__)
import os
import sys
import psutil
import logging
from llama_cpp import Llama

logger = logging.getLogger(__name__)

# Путь к модели
MODEL_PATH = r"C:\Users\User\PycharmProjects\deep\deepseek-r1-distill-qwen-14b-q4_k_m.gguf"

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
        # Проверка существования файла модели
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model file not found: {MODEL_PATH}")
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

        # Проверка доступной памяти
        available_memory = psutil.virtual_memory().available / (1024 ** 3)
        logger.info(f"Available memory: {available_memory:.2f} GiB")
        if available_memory < 4:  # Минимальный порог памяти (можно настроить)
            logger.warning(f"Low memory available: {available_memory:.2f} GiB")

        # Инициализация модели
        try:
            self.model = Llama(
                model_path=MODEL_PATH,
                n_ctx=4096,
                n_threads=6,
                n_batch=128,
                seed=3603909884,
                n_gpu_layers=20,
                verbose=True,
            )
        except Exception as e:
            logger.error(f"Failed to load LLM model: {str(e)}")
            raise

    def generate_questions(self, text):
        if not text:
            logger.warning("Empty text provided for question generation")
            return []

        prompt = (
            "Проанализируй текст защиты проекта и выдели только основные смысловые вопросы, заданные студенту. "
            "Сформулируй вопросы кратко и точно на русском языке. Требования:\n"
            "1. Нумерованный список без дополнительных описаний\n"
            "2. Сохрани технические термины из оригинала \n"
            "3. Объедини повторяющиеся/схожие формулировки в один пункт\n"
            "4. В ответе не используй теги think и прочее \n"
            "5. Исключи мета-комментарии (например, 'Скажите...', 'Еще вопрос')\n\n"
            f"Текст для анализа: '{text}'"
        )

        return self.generate_response(prompt)

    def generate_response(self, prompt, temperature=0.6, max_tokens=500):
        try:
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                repeat_penalty=1.0,
                stop=["<｜end▁of▁sentence｜>"],
            )
            return self.clean_output(response["choices"][0]["text"].strip())
        except Exception as e:
            logger.error(f"Question generation error: {str(e)}")
            return []

    @staticmethod
    def clean_output(text):
        if '</think>' in text:
            text = text.split('</think>')[-1]
        return [line.split('. ', 1)[-1] if '. ' in line else line
                for line in text.strip().split('\n') if line.strip()]

    def close(self):
        try:
            if self.model:
                self.model.close()
                logger.info("LLM model resources released")
        except Exception as e:
            logger.error(f"Error closing LLM model: {str(e)}")