from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import render
from .models import Treinamentos, DataTreinamento
from .utils import gerar_documentos
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from django.conf import settings
from langchain_community.vectorstores import FAISS
import os
from django_q.tasks import async_task
from django_q.models import Task
from pathlib import Path

@receiver(post_save, sender=Treinamentos)
def signals_treinamento_ia(sender, instance, created, **kwargs):
    if created:
        async_task(task_treinar_ia, instance.id)
    
    
def task_treinar_ia(instance_id):
    instance = Treinamentos.objects.get(id=instance_id)
    documentos = gerar_documentos(instance)

    if not documentos:
        return
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(documentos)
    embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
    
    db_path = Path(settings.BASE_DIR) / "banco_faiss"
        
    if db_path.exists():
            vectordb = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
            vectordb.add_documents(chunks)
    else:
        vectordb = FAISS.from_documents(chunks, embeddings)
    
    vectordb.save_local(str(db_path))
        
