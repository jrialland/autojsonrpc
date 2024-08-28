import pytest
from autojsonrpc import jsonrpc_service
from autojsonrpc.asgi import application
import json


@jsonrpc_service()
class ExampleService:
    def add(self, a: int, b: int) -> int:
        return a + b


class AsgiHarness:

    def __init__(self):
        self.outputs = []

    async def do_post(self, path, headers: dict[str, str], body: bytes, asgi_func):
        scope = {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        }

        async def receive():
            return {
                "type": "http.request",
                "body": body,
            }

        async def send(message):
            self.outputs.append(message)

        await asgi_func(scope, receive, send)


@pytest.mark.asyncio
async def test_asgi():
    request_body = json.dumps(
        {"jsonrpc": "2.0", "id": 252, "method": "exampleService.add", "params": [17, 3]}
    ).encode()
    harness = AsgiHarness()
    await harness.do_post(
        "/jsonrpc", {"Content-Type": "application/json"}, request_body, application
    )
    assert harness.outputs[0]["type"] == "http.response.start"
    assert harness.outputs[0]["status"] == 200
    assert harness.outputs[0]["headers"] == [(b"content-type", b"application/json")]

    assert harness.outputs[1]["type"] == "http.response.body"
    response_body = harness.outputs[1]["body"]
    response_json = json.loads(response_body)
    assert response_json["jsonrpc"] == "2.0"
    assert response_json["id"] == 252
    assert response_json["result"] == 20
