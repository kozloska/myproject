import spacy
from audio.models import Project, Question  # Импорт из текущего приложения

class TranscriptionService:
    nlp = spacy.load("ru_core_news_sm")

    @classmethod
    def extract_questions(cls, text):
        doc = cls.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip().endswith('?')]

    @classmethod
    def process_question(cls, question):
        doc = cls.nlp(question)
        return " ".join([token.lemma_ for token in doc if not token.is_stop])

    @classmethod
    def save_questions(cls, questions, project_id):
        project = Project.objects.get(ID=project_id)
        for question in questions:
            processed = cls.process_question(question)
            Question.objects.create(Text=processed, ID_Project=project)
        project.Status = "Готов"
        project.save()