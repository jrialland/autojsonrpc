from autojsonrpc import jsonrpc_service
from autojsonrpc.wsgi import wsgi_func
from io import BytesIO
import json

@jsonrpc_service()
class ExampleService:
    def add(self, a:int, b:int) -> int:
        return a+b
    
def run_wsgi(payload):
    environ = {
        'REQUEST_METHOD': 'POST',
        'PATH_INFO': '/jsonrpc',
        'CONTENT_TYPE': 'application/json',
        'wsgi.input': BytesIO(json.dumps(payload).encode())
    }

    class StartResponse:
        def __init__(self):
            self.response_headers = []
            self.response_status = None
        def __call__(self, status, headers):
            self.response_status = status
            self.response_headers = headers
    start_response = StartResponse()
    response_body = b''.join(wsgi_func(environ, start_response))
    return start_response.response_status, {k:v for k,v in start_response.response_headers}, response_body.decode()

def test_wsgi():

    response_status, response_headers, response_body = run_wsgi({
        'jsonrpc':'2.0',
        'id':252,
        'method':'exampleService.add',
        'params': [17, 3]
    })
    assert int(response_status.split()[0]) == 200
    assert response_headers['Content-Type'] == 'application/json'
    response_json = json.loads(response_body)
    assert response_json['jsonrpc'] == '2.0'
    assert response_json['id'] == 252
    assert response_json['result'] == 20