"""autojsonrpc: JSON-RPC server and client generator for Python and JavaScript/TypeScript.
    This module provides a decorator for registering a class as a JSON-RPC service, and a Flask blueprint for handling JSON-RPC requests.
    The module also generates JavaScript and TypeScript code for calling JSON-RPC methods.
    The JSON-RPC server uses the JSON-RPC 2.0 protocol.
    The JSON-RPC client code is generated as a class with methods for calling the JSON-RPC methods.
    The JSON-RPC client code is generated in JavaScript and TypeScript.
    The JSON-RPC server and client code is generated based on the type hints of the methods and dataclasses used in the service.
    The JSON-RPC server and client code is generated dynamically at runtime.

    Example usage:

    ```python

    @dataclass
    class UserData:
        username: str
        lastlogin: datetime.datetime

    @jsonrpc_service('sampleService')
    class SampleService:

        def get_user(self, username: str) -> UserData:
            return UserData(username, datetime.datetime.now())

        def say_hello(self, data:UserData) -> str:
            return f"Hello {data.username}!"

    app = Flask(__name__)
    app.register_blueprint(jsonrpc_blueprint())
    ```

    The following javascript code can be used to call the JSON-RPC methods:

        ```javascript
        (async function call_jsonrpc() {
            const user = await sampleService.get_user('Alice');
            console.log(user);
            const message = await sampleService.say_hello(user);
            console.log(message);
        })();
        ```
"""

from os.path import basename
import inspect
import logging
import io
from .types import convert_arg, to_dict, to_json
from typing import Any, Callable, IO, Iterable, Tuple, Dict
import json


class MethodDefinition:

    def __init__(self, name: str, func: Callable, servicedef: "ServiceDefinition"):
        """Create a method definition from a method
        Args:
            name (str): method name
            func (Callable): method function
            service (ServiceDefinition): definition of the service that the method belongs to
        """
        self.name = name
        self.func = func
        self.servicedef = servicedef
        # get the function signature by reading type hints, if available
        self.signature = inspect.signature(func)

    @property
    def docstring(self) -> str | None:
        """Return the docstring of the method."""
        return self.func.__doc__

    @property
    def return_type(self) -> type:
        """Return the return type of the method."""
        ann = self.signature.return_annotation
        return ann if ann != inspect.Signature.empty else type(None)

    @property
    def arg_types(self) -> list:
        """Return the types of the arguments of the method, in the order in which they are defined in the method signature."""
        arg_types = []
        for param in self.signature.parameters.values():
            if param.annotation == inspect.Signature.empty:
                arg_types.append(Any)
            else:
                arg_types.append(param.annotation)
        return arg_types

    @property
    def arg_names(self) -> list:
        """Return the names of the arguments of the method, in the order in which they are defined in the method signature."""
        return list(self.signature.parameters.keys())

    @property
    def args(self) -> list[tuple[str, type]]:
        """Return a list of tuples containing the names and types of the arguments of the method."""
        return zip(self.arg_names, self.arg_types)

    def parse_args_dict(self, args: dict) -> dict:
        """convert an untyped dictionary of arguments from JSON-RPC into a typed dictionary, so that the function can be called with the correct types."""
        typed_args = {}
        for name, value in args.items():
            param_type = self.signature.parameters[name].annotation
            typed_args[name] = convert_arg(value, param_type)
        return typed_args

    def parse_args_list(self, args: list) -> list:
        """convert an untyped list of arguments from JSON-RPC into a typed list, so that the function can be called with the correct types."""
        if len(args) != len(self.arg_types):  # ignoring the self argument
            raise ValueError(
                f"Error parsing arguments for method {self.name} : expected {len(self.arg_types)} arguments, got {len(args)}"
            )
        return [convert_arg(value, t) for value, t in zip(args, self.arg_types)]

    def get_invoker(self) -> Callable:
        def invoker(*args, **kwargs):
            return self.func(*list(args), **kwargs)

        return invoker


class ServiceDefinition:

    def __init__(self, name: str, service_instancier: Callable[[], object]):
        """Create a service definition from a service object
        Args:
            name (str): service name
            service (object): service object
        """
        self.name = name
        self.service_instance = service_instancier()
        self.methods:dict[str, MethodDefinition] = {}

        self.docstring = self.service_instance.__doc__
        for method_name in dir(self.service_instance):
            if not method_name.startswith("_"):
                method = getattr(self.service_instance, method_name)
                if callable(method):
                    self.methods[method_name] = MethodDefinition(
                        method_name, method, self
                    )

    @property
    def service(self) -> object:
        return self.service_instance


class JsonRpcRegistry:

    def __init__(self):
        """Create a JSON-RPC registry."""
        self._method_definitions:dict[str, MethodDefinition] = {} # {method_name: method_definition}
        self._service_definitions:dict[str, ServiceDefinition] = {}  # {service_name: service_definition}

    @property
    def service_names(self) -> list[str]:
        """Return the names of the registered services."""
        return list(self._service_definitions.keys())

    @property
    def services(self) -> dict[str, object]:
        """Return the registered services."""
        return self._service_instances.copy()

    def register_service(self, name: str, service_instancier: Callable[[], object]):
        """Register a service object as a JSON-RPC service."""
        definition = self._service_definitions[name] = ServiceDefinition(
            name, service_instancier
        )
        for method_name, method in definition.methods.items():
            self._method_definitions[f"{name}.{method_name}"] = method

    def generate_client(self, filename:str, jsonrpc_url: str = "/jsonrpc") -> tuple[str, str]:
        """Generate javascript code for calling JSON-RPC methods."""
        from .clients.javascript import generate_js
        from .clients.typescript import generate_ts
        from .clients.php import generate_php
        from .clients.python import generate_python
        if filename.endswith(".js"):
            minified = filename.endswith(".min.js")
            return generate_js(self._service_definitions, jsonrpc_url, minified), "application/javascript"
        elif filename.endswith(".ts"):
            return generate_ts(self._service_definitions, jsonrpc_url), "application/javascript"
        elif filename.endswith(".php"):
            return generate_php(self._service_definitions, jsonrpc_url), 'text/plain' #"application/x-httpd-php"
        elif filename.endswith(".py"):
            return generate_python(self._service_definitions), 'text/plain'

    def _make_error(
        self,
        code: int,
        message: str | None = None,
        exception: Exception | None = None,
        id: int | None = None,
    ) -> dict:
        """Generate a JSON-RPC error response."""
        assert message or exception, "Either message or exception must be provided"
        if exception:
            if exception.__traceback__:
                # get the last frame of the exception
                frame_info = inspect.getinnerframes(exception.__traceback__)[-1]
                message = (
                    f"[{basename(frame_info.filename)}:{frame_info.lineno}] {str(exception)}"
                    if frame_info.filename
                    else str(exception)
                )
            else:
                message = str(exception)
        err: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
        }
        if id is not None:
            err["id"] = id
        return err

    def _execute_request(self, payload: dict) -> dict:
        """Execute a JSON-RPC request and generate the json-rpc response."""
        try:
            assert (
                "jsonrpc" in payload and payload["jsonrpc"] == "2.0"
            ), "Invalid JSON-RPC version"
            assert "method" in payload, "Method not specified"
            assert "params" in payload, "Params not specified"
            assert "id" in payload, "ID not specified"
        except AssertionError as e:
            return self._make_error(-32600, str(e))

        method_def: MethodDefinition = self._method_definitions.get(payload["method"])
        if not method_def:
            return self._make_error(-32601, "Method not found", id=payload["id"])

        try:
            if isinstance(payload["params"], dict):
                kwparams = method_def.parse_args_dict(payload["params"])
                result_maker = lambda: method_def.get_invoker()(**kwparams)
            elif isinstance(payload["params"], list):
                params = method_def.parse_args_list(payload["params"])
                result_maker = lambda: method_def.get_invoker()(*params)
            else:
                return self._make_error(-32602, "Invalid params", id=payload["id"])
        except Exception as e:
            logging.exception("Error parsing arguments")
            return self._make_error(-32602, exception=e, id=payload["id"])

        try:
            # execute the method and convert the result to JSON
            result = result_maker()
            return {
                "jsonrpc": "2.0",
                "result": to_dict(result),
                "id": payload["id"],
            }
        except Exception as e:
            logging.exception("Error executing method")
            return self._make_error(-32000, exception=e, id=payload["id"])

    def handle_request(
        self, input_stream: IO, mimetype: str
    ) -> Tuple[Iterable[bytes], str]:

        if mimetype == "application/json":
            response = self._execute_request(json.loads(input_stream.read()))
            status_code = (
                "500 Internal Server Error" if "error" in response else "200 OK"
            )
            return iter([to_json(response).encode()]), status_code

        elif mimetype == "application/x-ndjson":
            reader = io.TextIOWrapper(input_stream, encoding="utf-8")

            def generate_response():
                for line in reader:
                    if not line.strip():
                        continue
                    response = self._execute_request(json.loads(line))
                    yield to_json(response).encode()

            return generate_response(), "200 OK"
        else:
            return io.BytesIO(b""), "415 Unsupported Media Type"



    def get(self, name: str) -> Any:
        """Get a service object by name."""
        definition = self._service_definitions.get(name)
        return definition.service if definition else None

    def set(self, name: str, service: Any):
        """Set a service object by name."""
        definition = self._service_definitions.get(name)
        if definition:
            definition.service_instance = service
        else:
            self.register_service(name, lambda: service)

"""Global JSON-RPC registry."""
registry = JsonRpcRegistry()


class jsonrpc_service:
    """Decorator for registering a class as a JSON-RPC service.
        Example usage:
        ```python
        @jsonrpc_service('sampleService')
        class SampleService:

            def get_user(self, username: str) -> UserData:
                return UserData(username, datetime.datetime.now())

            def say_hello(self, data:UserData) -> str:
                return f"Hello {data.username}!"
        ```
    Args:
        name (str): name of the service

    """

    def __init__(
        self, name: object | str | None = None, instancier: Callable[[], object] | None = None
    ):
        # when the first argument is a class and not a string, it means the decorator was called without parentheses
        # in this we behave as if we were called with default arguments
        if inspect.isclass(name):
            self.name = None
            self.instancier = None
        else:
            self.name = name
            self.instancier = instancier

    def __call__(self, cls: type) -> type:
        name = self.name or cls.__name__[0].lower() + cls.__name__[1:]
        registry.register_service(name, self.instancier or (lambda: cls()))
        return cls


__all__ = ["jsonrpc_service", "registry"]
