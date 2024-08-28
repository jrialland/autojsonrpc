import pytest
from autojsonrpc import jsonrpc_service
from autojsonrpc.flask import jsonrpc_blueprint

@jsonrpc_service()
class SayHelloService:
    def say_hello(self, name: str) -> str:
        return f"Hello, {name}!"


@pytest.fixture()
def app():
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(jsonrpc_blueprint())
    return app

@pytest.fixture()
def client(app):
    return app.test_client()

def test_flask_call_params_list(client):
    response = client.post("/jsonrpc", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sayHelloService.say_hello",
        "params": ["World"]
    })
    assert response.status_code == 200
    assert response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": "Hello, World!"
    }

def test_flask_call_params_dict(client):
    response = client.post("/jsonrpc", json={
        "jsonrpc": "2.0",
        "id": 54141,
        "method": "sayHelloService.say_hello",
        "params": {"name": "World"}
    })
    assert response.status_code == 200
    assert response.json == {
        "jsonrpc": "2.0",
        "id": 54141,
        "result": "Hello, World!"
    }