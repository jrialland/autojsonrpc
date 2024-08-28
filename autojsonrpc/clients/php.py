from .. import ServiceDefinition
from ..types import get_php_name
PHP_CLIENT_HEAD = """
<?php
    class JsonRpcClient {

        private $jsonrpc_url;

        private $_id = 1;

        public function __construct($url = "@jsonrpc_url@") {
            $this->jsonrpc_url = $url;
        }

        public function __call($method, $params) {
            $request = array(
                'jsonrpc' => '2.0',
                'method' => $method,
                'params' => $params,
                'id' => $this->_id++,
            );
            $curl = curl_init($this->jsonrpc_url);
            curl_setopt($curl, CURLOPT_POST, 1);
            curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($request));
            $response = curl_exec($curl);
            curl_close($curl);
            $json_response = json_decode($response, true);
            if (isset($json_response['error'])) {
                throw new Exception($json_response['error']['message']);
            }
            return $json_response['result'];
        }
    };

"""

def generate_php(
    services: dict[str, ServiceDefinition],
    jsonrpc_url: str = "/jsonrpc",):
    code = PHP_CLIENT_HEAD.replace("@jsonrpc_url@", jsonrpc_url)
    for servicename, definition in services.items():

        code += f"\n    class {servicename[0].upper() + servicename[1:]}Client extends JsonRpcClient {{\n\n"


        code += "    private static $instance;\n\n"
        code += "    private function __construct($url = '@jsonrpc_url@') {\n"
        code += "        super($url);\n"
        code += "        self::instance = this;\n"
        code += "    }\n"

        for methodname, methoddef in definition.methods.items():
            return_type = get_php_name(methoddef.return_type, True)
            code += "\n"
            if methoddef.docstring:
                code += f"\n    // {methoddef.docstring}\n"
            code += f"        public function {methodname}("

            params = []
            args = []
            for argname, argtype in methoddef.args:
                params.append(f"{argname}: {get_php_name(argtype, False)}")
                args.append(argname)

            code += ", ".join(params)
            code += ") {\n"
            code += f"            return $this->__call('{servicename}.{methodname}', array("
            code += ", ".join(args)
            code += f")) as {return_type};\n"
            code += "        }\n"

        code += "    };\n"

    return code
