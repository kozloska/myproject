

import spacy
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer

from audio.models import Project, Question  # Импорт из текущего приложения


import spacy
from audio.models import Project, Question  # Импорт из текущего приложения

class TranscriptionService:
    @staticmethod
    def extract_questions(text):
        nlp = spacy.load("ru_core_news_sm")
        doc = nlp(text)
        return [sent.text for sent in doc.sents if sent.text.endswith('?')]

    @staticmethod
    def process_question(question):
        # Используем spaCy для обработки вопроса
        nlp = spacy.load("ru_core_news_sm")
        doc = nlp(question)
        summary = " ".join([sent.text for sent in doc.sents])  # Здесь можно применить свою логику
        return summary

    @staticmethod
    def save_questions(questions, project_id):
        project = Project.objects.get(ID=project_id)
        for question in questions:
            processed_question = TranscriptionService.process_question(question)
            Question.objects.create(Text=processed_question, ID_Project=project)
        project.Status = True
        project.save()