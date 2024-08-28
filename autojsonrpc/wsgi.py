"""
A wsgi function that can be used to serve the JSON-RPC API over HTTP.
"""

from . import registry


def wsgi_func(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ["PATH_INFO"]
    mimetype = environ.get("CONTENT_TYPE", "")

    if path == "/jsonrpc" and method == "POST":
        iterable, status = registry.handle_request(environ["wsgi.input"], mimetype)
        start_response(status, [("Content-Type", mimetype)])
        yield from iterable
        return

    elif method == "GET":
        code, content_type = registry.generate_client(path)
        start_response("200 OK", [("Content-Type", content_type)])
        yield code.encode("utf-8")
        return

    else:
        start_response("404 Not Found", [("Content-Type", "text/plain")])
