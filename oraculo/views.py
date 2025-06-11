from django.shortcuts import render, redirect
from rolepermissions.checkers import has_permission
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from .models import DataTreinamento, Pergunta, Treinamentos
from django.http import HttpResponse
from django.http import JsonResponse
from django_q.models import Task
import os 
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from django.conf import settings
from django.http import StreamingHttpResponse
from pathlib import Path
import json
from django.core.cache import cache
from .utils import sched_message_response

def treinar_ia(request):
    #if not has_permission(request.user, 'treinar_ia'):
    #    raise Http404()
    if request.method == 'GET':
        tasks = Task.objects.all()
        return render(request, 'treinar_ia.html', {'tasks': tasks})    
    elif request.method == 'POST':
        site = request.POST.get('site')
        conteudo = request.POST.get('conteudo')
        arquivo = request.FILES.get('arquivo')
        
        treinamento = Treinamentos(
                site=site,
                conteudo=conteudo,
                arquivo=arquivo
        )
        treinamento.save()
                
    return redirect('treinar_ia')

@csrf_exempt
def chat(request):
    if request.method == 'GET':
        return render(request, 'chat.html')
    elif request.method == 'POST':
        pergunta_user = request.POST.get('pergunta')
        
        pergunta = Pergunta(
            pergunta=pergunta_user
        )
        pergunta.save()
        
        return JsonResponse({'id': pergunta.id})
        

@csrf_exempt
def stream_response(request):
    id_pergunta = request.POST.get('id_pergunta')
    pergunta = Pergunta.objects.get(id=id_pergunta)
    
    def stream_generator():
        embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        db_path = Path(settings.BASE_DIR) / "banco_faiss"
        vectordb = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
        docs = vectordb.similarity_search(pergunta.pergunta, k=5)
        for doc in docs:
            dt = DataTreinamento.objects.create(
                metadata=doc.metadata,
                texto=doc.page_content
            )
            pergunta.data_treinamento.add(dt)

        contexto = "\n\n".join([
            f"Material: {doc.page_content}"
            for doc in docs
        ])

        messages = [
            {'role': 'system', 'content': f'Você é um assistente virtual e deve responder com precisão as perguntas sobre uma empresa.\n\n{contexto}'},
            {'role': 'user', 'content': f'{pergunta.pergunta}'}
        ]

        llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            streaming=True,
            openai_api_key=settings.OPENAI_API_KEY
        )

        for chunk in llm.stream(messages):
            token = chunk.content
            if token:
                yield token

    return StreamingHttpResponse(stream_generator(), content_type='text/plain; charset=utf-8')
    
    
    
def ver_fontes(request, id):
    pergunta = Pergunta.objects.get(id=id)
    for i in pergunta.data_treinamento.all():
        print(i.metadata)
        print(i.texto)
        print('-----')
    print(pergunta.pergunta)
    return render(request, 'ver_fontes.html', {'pergunta': pergunta})



@csrf_exempt
def webhook_whatsapp(request):
    
    data = json.loads(request.body)
    phone = data.get('data').get('key').get('remoteJid').split('@')[0]
    message = data.get('data').get('message').get('extendedTextMessage').get('text')
    
    buffer = cache.get(f'wa_buffer_{phone}', [])
    buffer.append(message)
    # tempo para a pessoa para responder,
    # seja o que for é preciso ver o cache e memória da pessoa
    # para saber, depende do público
    cache.set(f'wa_buffer_{phone}', buffer, timeout=60)
    
    # agora vai agendar a mensagem de resposta sem ser na hora
    sched_message_response(phone)
    
    print(buffer)
    
    return HttpResponse('test')
