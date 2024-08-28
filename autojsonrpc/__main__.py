# from . import jsonrpc_service
# from .flask import jsonrpc_blueprint

# from dataclasses import dataclass
# import logging
# from typing import List
# import flask

# logging.basicConfig(level=logging.DEBUG)

# app = flask.Flask(__name__)
# app.register_blueprint(jsonrpc_blueprint())


# @app.route("/")
# def redirect_to_index():
#     return "", 302, {"Location": "/index.html"}


# @app.route("/index.html")
# def index():
#     return """
# <!DOCTYPE html>
# <html>
# <head>
#     <title>JSON-RPC</title>
#     <script src="/jsonrpc/client.js"></script>
# </head>
# <body>
#     <script>
#         async function main() {
#             await userService.createDb();
#             await userService.addOrUpdateUser("David", "david@example.com");
#             for(let user of await userService.getUsers()) {
#                 console.log(user);
#                 await userService.printUser(user);
#             }
#         }
#         main();
#     </script>
# </body>
# </html>
# """
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

# class Base(DeclarativeBase):
#     pass

# db = SQLAlchemy(app, model_class=Base)

# @dataclass
# class User(db.Model):
#     id: Mapped[int] = mapped_column(primary_key=True)
#     username: Mapped[str] = mapped_column(unique=True)
#     email: Mapped[str]

#     def __repr__(self):
#         return  'User' + repr({"id": self.id, "username": self.username, "email": self.email})

# @jsonrpc_service()
# class UserService:

#     def createDb(self) -> None:
#         with app.app_context():
#             db.create_all()
#         for username in ["Alice", "Bob", "Charlie"]:
#             self.addOrUpdateUser(username, f"{username.lower()}@example.com")

#     def addOrUpdateUser(self, username: str, email: str) -> int:
#         user = User.query.filter_by(username=username).first()
#         if user:
#             user.email = email
#             db.session.commit()
#         else:
#             user = User(username=username, email=email)
#             db.session.add(user)
#             db.session.commit()
#         return user.id

#     def getUser(self, id: int) -> User:
#         return User.query.get(id)

#     def getUsers(self) -> List[User]:
#         return User.query.all()

#     def getUserMap(self) -> dict[int, User]:
#         return {user.id: user for user in User.query.all()}

#     def printUser(self, user: User) -> None:
#         print(user)

# @jsonrpc_service()
# class AnotherService:
#     def getNumber(self) -> int:
#         return 42

# app.run(debug=True)
