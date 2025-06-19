from langchain.docstore.document import Document
from typing import List
import requests
from langchain_community.document_loaders import PyMuPDFLoader, ImageCaptionLoader
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.cache import cache 
from datetime import datetime, timedelta
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from .wrapper_evolutionapi import SendMessage
from django.conf import settings

scheduler = BackgroundScheduler()
scheduler.start()

def formatar_texto_pdf(texto: str) -> str:
    linhas = texto.splitlines()
    resultado = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if linha.isupper() and len(linha) < 60:
            resultado.append(f"\n\n### {linha}")
        elif linha.endswith(":"):
            resultado.append(f"\n\n## {linha}")
        else:
            resultado.append(linha)
    return "\n".join(resultado).strip()


def html_para_texto_rag(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    texto_final = []
    
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        texto = tag.get_text(strip=True)
        
        if not texto:
            continue
        if tag.name in ["h1","h2","h3"]:
            texto_formatado = f"\n\n### {texto.upper()}"
        elif tag.name == "li":
            texto_formatado = f" - {texto}"
        else:
            texto_formatado = texto
        
        texto_final.append(texto_formatado)
    
    return "\n".join(texto_final).strip()


def gerar_documentos(instance) -> List[Document]:
    documentos = []
    if instance.arquivo:
        extensao = instance.arquivo.name.split('.')[-1].lower()
        if extensao == 'pdf':
            loader = PyMuPDFLoader(instance.arquivo.path)
            pdf_doc = loader.load()
            for doc in pdf_doc:
                doc.page_content = formatar_texto_pdf(doc.page_content)
                doc.metadata['url'] = [instance.arquivo.url]
            documentos += pdf_doc
        elif extensao in ['txt', 'md']:
            with open(instance.arquivo.path, 'r', encoding='utf-8') as file:
                content = file.read()
                documentos.append(Document(page_content=content, metadata={'url': [instance.arquivo.url]}))
        elif extensao in ['png', 'jpg', 'jpeg']:
            loader = ImageCaptionLoader(instance.arquivo.path)
            image_doc = loader.load()
            for doc in image_doc:
                doc.metadata['url'] = [instance.arquivo.url]
            documentos += image_doc
                
    if instance.conteudo:
        documentos.append(Document(page_content=instance.conteudo))
    
    if instance.site:
        site_url = instance.site if instance.site.startswith('https://') else f'https://{instance.site}'
        content = requests.get(site_url, timeout=10).text
        content = html_para_texto_rag(content)
        documentos.append(Document(page_content=content))
    else:
        return
    
    return documentos

def send_message_response(phone):
    messages = cache.get(f"wa_buffer_{phone}", [])
    if messages:
        question = "\n".join(messages)
        embeddings = OpenAIEmbeddings()
        vectordb = FAISS.load_local("banco_faiss", embeddings, allow_dangerous_deserialization=True)
        docs = vectordb.similarity_search(question, k=5)
        context = "\n\n".join([doc.page_content for doc in docs ])

        messages = [
            {"role": "system", "content": f"Recupere e integre referências técnicas de ML, Visão Computacional e EdgeML, datascience para gerar respostas claras, práticas e otimizadas para execução em núvem e em borda na borda.\n\n{context}"},
            {"role": "user", "content": question}
        ]
        
        llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
        )

        response = llm.invoke(messages).content
        print(response)
        SendMessage().send_message('arcane', {
            "number": phone,
            "textMessage": {"text": response}
        })

    cache.delete(f"wa_buffer_{phone}")
    cache.delete(f"wa_timer_{phone}")

    

def sched_message_response(phone):
    if not cache.get(f'wa_timer_{phone}'):
        scheduler.add_job(
            send_message_response,
            'date',
            run_date=datetime.now() + timedelta(seconds=15),
            kwargs={'phone': phone},
            misfire_grace_time=60
        )
        cache.set(f'wa_timer_{phone}', True, timeout=60)
    