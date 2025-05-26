import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import pymorphy3
from audio.models import Project, Question
import logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    # Инициализация ресурсов NLTK и pymorphy3
    _stop_words = None
    _morph = None

    @classmethod
    def init_resources(cls):
        if cls._stop_words is None:
            try:
                cls._stop_words = set(stopwords.words('russian'))
            except LookupError:
                nltk.download('stopwords')
                cls._stop_words = set(stopwords.words('russian'))
        if cls._morph is None:
            cls._morph = pymorphy3.MorphAnalyzer()

    @classmethod
    def extract_questions(cls, text):
        cls.init_resources()
        try:
            # Разбиваем текст на предложения
            sentences = sent_tokenize(text, language='russian')
            # Фильтруем предложения, заканчивающиеся на '?'
            return [sent.strip() for sent in sentences if sent.strip().endswith('?')]
        except LookupError:
            nltk.download('punkt')
            sentences = sent_tokenize(text, language='russian')
            return [sent.strip() for sent in sentences if sent.strip().endswith('?')]

    @classmethod
    def process_question(cls, question):
        cls.init_resources()
        # Токенизация слов
        tokens = word_tokenize(question, language='russian')
        # Лемматизация и удаление стоп-слов
        processed = [
            cls._morph.parse(token.lower())[0].normal_form
            for token in tokens
            if token.lower() not in cls._stop_words and token.isalnum()
        ]
        return " ".join(processed)

    @classmethod
    def save_questions(cls, questions, project_id):
        try:
            project = Project.objects.get(id=project_id)
            if not questions:
                project.Status = "Готов (вопросы не найдены)"
                project.save()
                return
            for question in questions:
                processed = cls.process_question(question)
                Question.objects.create(Text=processed, ID_Project=project)
            project.Status = "Готов"
            project.save()
        except Project.DoesNotExist:
            logger.error(f"Project with id {project_id} not found")
            raise