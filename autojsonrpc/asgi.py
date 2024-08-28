"""
ASGI config for autojsonrpc project.
"""

from . import registry
import io

async def read_body(receive):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return io.BytesIO(body)

async def application(scope, receive, send):
    """
        ASGI application for handling JSON-RPC requests. The application has the following routes:
            - /jsonrpc: (POST) handles JSON-RPC requests
            - /* (GET): serves client code (javascript, typescript, etc.)

        The application is registered with the ASGI server as follows
         * (example using starlette):
        ```
        from starlette.applications import Starlette
        from starlette.routing import Route
        from autojsonrpc.asgi import application

        app = Starlette(routes=[Route("/", application)])
        ```

    """
    method = scope["method"]
    path = scope["path"]
    mimetype = next(
        (v for k, v in scope["headers"] if k == b"content-type"), b""
    ).decode()

    request_body = await read_body(receive)
    if method == "POST" and path == "/jsonrpc":
        iterable, status = registry.handle_request(request_body, mimetype)
        await send(
            {
                "type": "http.response.start",
                "status": int(status.split()[0]),
                "headers": [(b"content-type", mimetype.encode())],
            }
        )
        await send({"type": "http.response.body", "body": b"".join(iterable)})

    elif method == 'GET':
        try:
            client, content_type  = registry.generate_client(path)
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [(b'content-type', content_type.encode())]
            })
            await send({
                'type': 'http.response.body',
                'body': client.encode()
            })
        except Exception as e:
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [(b'content-type', b'text/plain')]
            })
            await send({
                'type': 'http.response.body',
                'body': str(e).encode()
            })
