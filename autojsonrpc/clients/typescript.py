from dataclasses import is_dataclass
from .javascript import js_block_comment
from .. import ServiceDefinition
from ..types import get_ts_type

def js_block_comment(text: str, start="/**", end="*/", indent: int = 0) -> str:
    """Convert a multiline string to a javascript block comment."""
    code = " " * indent + start + "\n"
    for line in text.strip().split("\n"):
        code += " " * indent + " * " + line + "\n"
    code += " " * indent + " " + end
    return code


def get_ts_interface_definition(python_type: type) -> str:
    """Generate a typescript interface from a dataclass."""
    assert is_dataclass(python_type), "Type must be a dataclass"
    fields = python_type.__dataclass_fields__
    code = "export interface " + python_type.__name__ + " {\n"
    for field_name, field_type in fields.items():
        code += f"    {field_name}: {get_ts_type(field_type.type, True)};\n"
    code += "}\n"
    return code

"""Typescript code for a JSON-RPC client."""
JSONRPC_TS = """
class JsonRpcClient {
    private _id: number=1;
    constructor(public jsonrpc_url: string = '@jsonrpc_url@') {}
    protected _call(method: string, params: any[]): Promise<any> {
        return fetch(`${this.jsonrpc_url}?method=${method}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                jsonrpc: '2.0',
                id: this._id++,
                method: method,
                params: params,
            })
        }).then(response => response.json())
        .then(payload => {
            if('error' in payload) {
                throw new Error(payload.error.message);
            }
            return payload.result;
        });
    }
}
"""

def generate_ts_interfaces(services: dict[str, ServiceDefinition]) -> str:
        dataclasses = set()
        for service in services.values():
            for method in service.methods.values():
                dataclasses.update(
                    [
                        param.annotation
                        for param in method.signature.parameters.values()
                        if is_dataclass(param.annotation)
                    ]
                )
                if is_dataclass(method.return_type):
                    dataclasses.add(method.return_type)
        return "\n".join(
            [get_ts_interface_definition(dataclass) for dataclass in dataclasses]
        )

def generate_ts(services: dict[str, ServiceDefinition], jsonrpc_url: str = "/jsonrpc") -> str:
        code = generate_ts_interfaces(services)
        code += JSONRPC_TS.replace("@jsonrpc_url@", jsonrpc_url)
        variable_decls = []
        for servicename, service in services.items():
            code += "\n"
            class_name = servicename[0].upper() + servicename[1:]
            if service.docstring:
                code += js_block_comment(service.docstring) + "\n"
            code += f"export class {class_name} extends JsonRpcClient {{\n"
            for methodname, method in service.methods.items():
                code += "\n"
                params = []
                args = []
                for param in method.signature.parameters.values():
                    params.append(f"{param.name}: {get_ts_type(param.annotation, False)}")
                    args.append(param.name)
                ts_return_type = get_ts_type(method.return_type, True)
                if method.docstring:
                    code += js_block_comment(method.docstring, indent=4) + "\n"
                code += f"    public {methodname}({','.join(params)}): Promise<{ts_return_type}> {{ return this._call('{servicename}.{methodname}', [{', '.join(args)}]) as Promise<{ts_return_type}>; }}\n"
            code += "}\n"
            variable_decls.append(f"export const {servicename} = new {class_name}();")
        code += "\n" + "\n".join(variable_decls)
        return code
