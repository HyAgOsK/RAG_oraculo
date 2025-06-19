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
    
    total_length = sum(len(doc.page_content) for doc in documentos)
    if total_length < 1000:
        chunk_size = 300
        chunk_overlap = 50
    elif total_length < 5000:
        chunk_size = 500
        chunk_overlap = 100
    else:
        chunk_size = 1000
        chunk_overlap = 500
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        length_function=len)
    
    
    chunks = splitter.split_documents(documentos)
    print(f"Split {len(documentos)} documents into {len(chunks)} chunks.")
    
    embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
    
    db_path = Path(settings.BASE_DIR) / "banco_faiss"
        
    if db_path.exists():
            vectordb = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
            vectordb.add_documents(chunks)
    else:
        vectordb = FAISS.from_documents(chunks, embeddings)
    
    vectordb.save_local(str(db_path))
        
