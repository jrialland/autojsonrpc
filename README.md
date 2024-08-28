# autojsonrpc

A Python library that helps me to provide json-rpc in flask and fastapi projects.

## Usage

```python
from autojsonrpc import jsonrpc_service
from autojsonrpc.flask import jsonrpc_blueprint
from flask import Flask

@jsonrpc_service()
class SayHelloService:
    def say_hello(self, name: str) -> str:
        return f"Hello, {name}!"


app = Flask(__name__)
app.register_blueprint(jsonrpc_blueprint())
app.run()

# and browse http://localhost:5000/jsonrpc/client.js
```

2. See other examples in ./tests
