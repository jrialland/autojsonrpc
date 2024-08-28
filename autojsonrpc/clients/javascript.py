from .. import ServiceDefinition


def js_block_comment(text: str, start="/**", end="*/", indent: int = 0) -> str:
    """Convert a multiline string to a javascript block comment."""
    code = " " * indent + start + "\n"
    for line in text.strip().split("\n"):
        code += " " * indent + " * " + line + "\n"
    code += " " * indent + " " + end
    return code


JSONRPC_CALL_JS = """"use strict";

function _call(jsonrpc_url, id, method, params) {

    return fetch(jsonrpc_url + `?method=${method}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: id,
            method: method,
            params: params,
        })
    })
    .then(response => response.json())
    .then(payload => {
        if('error' in payload) {
            throw new Error(payload.error.message);
        }
        return payload.result;
    });
}
"""


def generate_js(
    services: dict[str, ServiceDefinition],
    jsonrpc_url: str = "/jsonrpc",
    minified: bool = False,
) -> str:
    code = JSONRPC_CALL_JS
    for servicename, service in services.items():
        code += "\nconst " + servicename + " = {\n"
        code += f"\n    jsonrpc_url: '{jsonrpc_url}',\n"
        code += f"\n    _id: 1,\n"
        for methodname, method in service.methods.items():
            code += "\n"
            if method.docstring:
                code += js_block_comment(method.docstring, indent=4) + "\n"
            code += (
                f"    "
                + methodname
                + ": function() { return _call(this.jsonrpc_url, this._id++, '"
                + servicename
                + "."
                + methodname
                + "', Array.from(arguments)); },\n"
            )
        code += "};\n"
    if minified:
        import jsmin  # type: ignore

        code = jsmin.jsmin(code)
    return code
