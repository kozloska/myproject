import os
from llama_cpp import Llama
import re
import logging

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
            
        self.model = Llama(
            model_path=model_path,
            n_ctx=8192,
            n_batch=512,
            n_threads=4,
            n_threads_batch=4,  
            n_gpu_layers=0,      # 0 = CPU. Для GPU поставьте -1 или количество слоёв
            verbose=True,
            mmap=True,
            mlock=True,
            # flash_attn=False,  # Убрано, т.к. у вас CPU (n_gpu_layers=0) 
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
                max_tokens=700,
                temperature=0.4,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stop=["<｜end▁ofsentence｜>"],
            )
            
            # Безопасное извлечение ответа
            if not response.get('choices'):
                return []
                
            raw_text = response['choices'][0]['text'].strip()
            return self._clean_output(raw_text)
            
        except Exception as e:
            logger.error(f"Ошибка LLM: {e}")
            return []

    def _clean_output(self, text: str):
        questions = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit() and '.' in line:
                line = line.split('.', 1)[-1].strip()
            if line.endswith('?'):
                questions.append(line)
        return questions

    def close(self):
        if hasattr(self, 'model'):
            del self.model
