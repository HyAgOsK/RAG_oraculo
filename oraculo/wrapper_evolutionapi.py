import requests
from urllib.parse import urlencode, urljoin

class BaseEvolutionAPI:
    
    def __init__(self):
        self._BASE_URL = 'https://evolution-api-production-28e6.up.railway.app/' # url generate domain, dominio ou IP
        self._API_KEY = {
            'arcane': '1dypqrhz7qlb48ofgcx34d'
        }
        
    def _send_request(
        self,
        path,
        method='GET',
        body=None,
        headers={},
        params_url={}
    ):
        method = method.upper()
        
        if headers is None:
            headers = {}
        if params_url is None:
            params_url = {}
            
        url = self._mount_url(path, params_url)
        
        if not isinstance(headers, dict):
            headers = {}
        
        headers.setdefault('Content-Type', 'application/json')
        instance = self._get_instance(path)
        headers['apikey'] = self._API_KEY.get(instance)
        
        print(f"[DEBUG] URL final: {url}")


        request = {
            'GET':requests.get,
            'POST':requests.post,
            'PUT':requests.put,
            'DELETE':requests.delete
        }.get(method)
        
        if not request:
            raise ValueError(f"http error {method} not support")
        
        try:
            response = request(url, headers=headers, json=body)
            return response
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Requisição falhou: {e}")
            return None
            
    def _mount_url(self, path, params_url):
        parameters = urlencode(params_url) if isinstance(params_url, dict) else '' 
        url = urljoin(self._BASE_URL, path)
        
        return f"{url}?{parameters}" if parameters else url

    
    def _get_instance(self, path):
        return path.strip('/').split('/')[-1]
    
    
class SendMessage(BaseEvolutionAPI):
    
    def send_message(self, instance, body):
        path = f'/menssage/sendText/{instance}/'
        return self._send_request(path, method='POST', body=body)
    

# nome da instancia que eu dei quando criou 'arcane'
# escaneando o múmero eu recebo essa mensagem
SendMessage().send_message('arcane', {"number": '5535997253305', "textMessage":{"text":"Olá meu nome é hyago sou consultor de IA"}})

