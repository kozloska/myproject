import spacy

from audio.models import Project, Question  # Импорт из текущего приложения


class TranscriptionService:
    @staticmethod
    def extract_questions(text):
        nlp = spacy.load("ru_core_news_sm")
        doc = nlp(text)
        return [sent.text for sent in doc.sents if sent.text.endswith('?')]

    @staticmethod
    def save_questions(questions, project_id):
        project = Project.objects.get(ID=project_id)
        for question in questions:
            Question.objects.create(Text=question, ID_Project=project)
        project.Status = True
        project.save()