from .. import ServiceDefinition
from ..types import get_python_name

PYTHON_CLIENT_TEMPLATE = """
import json
import requests
from typing import Any
# ------------------------------------------------------------------------------
class RpcClient:
    def __init__(self, url):
        self._id = 1
        self.url = url

    def call(self, service_name, method_name, **kwargs):
        request_payload = {
            'jsonrpc': '2.0',
            'id': self._id,
            'method': f'{service_name}.{method_name}',
            'params': kwargs,
        }
        self._id += 1
        response = requests.post(self.url, json=request_payload)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            raise ValueError(result['error'])
        if 'result' in result:
            return result['result']
        return None
"""

# ------------------------------------------------------------------------------
def generate_python(services: dict[str, ServiceDefinition]):

    def generate_method_args(methoddef):
        return ', '.join([f'{argname}: {get_python_name(argtype, False)}' for argname, argtype in methoddef.args])

    code = PYTHON_CLIENT_TEMPLATE
    for servicename, servicedef in services.items():
        class_name = servicename.capitalize() + 'Client'
        code += '\n# '+'-'*78
        code += f"\nclass {class_name}:\n\n"
        code += f"    def __init__(self, rpc_client):\n"
        code += f"        self.rpc_client = rpc_client\n"
        for methodname, methoddef in servicedef.methods.items():
            return_type = get_python_name(methoddef.return_type, True)
            code += '\n'
            code += f"    def {methodname}(self{', ' if methoddef.arg_names else ''}{generate_method_args(methoddef)}) -> {return_type}:\n"
            call_args = ', '.join([a+'='+a for a in methoddef.arg_names])
            code += f"        return self.rpc_client.call('{servicename}', '{methodname}'{', ' if call_args else ''}{call_args}) #type:ignore\n"
    return code
