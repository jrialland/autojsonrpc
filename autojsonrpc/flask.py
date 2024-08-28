import flask
from . import registry


def jsonrpc_blueprint() -> flask.Blueprint:
    """Create a Flask blueprint for handling JSON-RPC requests. The blueprint has the following routes:

        - /jsonrpc: handles JSON-RPC requests
        - /jsonrpc/client.js: serves the javascript client code
        - /jsonrpc/client.min.js: serves the minified javascript client code
        - /jsonrpc/client.ts: serves the typescript client code

        The blueprint is registered with the Flask app as follows:
        `app.register_blueprint(jsonrpc_blueprint())`

    Returns:
        flask.Blueprint: Flask blueprint for handling JSON-RPC requests
    """
    bp = flask.Blueprint("jsonrpc", __name__)

    @bp.route("/jsonrpc", methods=["POST"])
    def handle_request():
        """Handle JSON-RPC requests."""
        iterable, status = registry.handle_request(
            flask.request.stream, flask.request.mimetype
        )
        return flask.Response(
            response=iterable,
            status=status,
            mimetype="application/json",
            direct_passthrough=True,
        )

    @bp.route("/jsonrpc/<path:filename>", methods=["GET"])
    def client_code(filename):
        """Serve the client code."""
        generated = registry.generate_client(filename)
        if generated:
            code, content_type = generated
            return flask.Response(response=code, mimetype=content_type)
        else:
            flask.abort(404)
    return bp

__all__ = ["jsonrpc_blueprint"]
