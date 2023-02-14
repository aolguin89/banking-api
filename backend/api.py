from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api, abort
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from marshmallow import ValidationError

from db_schemas.user_schema import UserSchema
from db_schemas.user_db import UserDb
from db_schemas.account_schema import AccountSchema
from backend.db_schemas.account_db import AccountDb
from utils.loggin_backend import logger_backend
from setup_db import SetupDatabase

app = Flask(__name__)
api = Api(app)
app.config["JWT_SECRET_KEY"] = "prog102"
jwt = JWTManager(app)


class User(Resource):

    def post(self):
        try:
            logger_backend.debug(f"POST '/users' {request.json} ")
            user = UserSchema().load(request.json)
            user_db = UserDb.create(user) 
            ## create account by default
            user_id = UserDb.get_user_by_username(user_db['username'])[0]['id']
            account = AccountDb.create(user_id=user_id)
            logger_backend.debug(f"Create account {account['cbu']}")
            return {
                       "username": user_db['username'],
                       "password": user_db['password'],
                       "code": user_db['code'],
                       "account_cbu": account['cbu']
                   }, 201

        except ValidationError as e:
            logger_backend.debug(f"Validation error:  {e.messages} ")
            abort(405, errors=e.messages)

    def get(self, id=None):
        if id is None:
            return UserDb.get_all()

        user = UserDb.get_user(id)
        if not user:
            abort(404, errors={"errors": {"message": "User with Id {} does not exist".format(id)}})
        return user

    def put(self, id):
        try:
            user = UserSchema().load(request.json)
            if UserDb.update(user, id):
                abort(404, errors={"errors": {"message": "User with Id {} does not exist".format(id)}})
        except ValidationError as e:
            abort(405, errors=e.messages)


api.add_resource(User, "/users", "/user/<int:id>")


class Login(Resource):

    def post(self):
        username = request.json.get("username", None)
        password = request.json.get("password", None)
        code = request.json.get("code", None)
        logger_backend.debug(f"{username} try to login")
        user_db = UserDb.get_user_by_username(username)
        if not user_db:
            return {"msg": "Username doesn't exist"}, 400

        if password != user_db[0]['password'] or code != user_db[0]['code']:
            return {"msg": "Bad password or code"}, 400

        logger_backend.debug(f"{user_db[0]['username']} login token generated ")
        access_token = create_access_token(identity=username)
        return jsonify(access_token=f"Bearer {access_token}")


api.add_resource(Login, "/login")


class Homepage(Resource):
    @jwt_required()
    def get(self):
        username = get_jwt_identity()
        user_db = UserDb.get_user_by_username(username)

        return jsonify(user=user_db)


api.add_resource(Homepage, "/home")


class Account(Resource):
    # create new account

    @jwt_required()
    def post(self):
        username = get_jwt_identity()
        user_id = UserDb.get_user_by_username(username)[0]['id']
        account = AccountDb.create(user_id=user_id)
        logger_backend.debug(f"Create new account by {username}, cbu : {account['cbu']} ")
        return make_response(jsonify(account=account), 201)
    # get all accounts by current user

    @jwt_required()
    def get(self):
        username = get_jwt_identity()
        logger_backend.debug(f"{username} client try to see theirs accounts")
        user_id = UserDb.get_user_by_username(username)[0]['id']
        accounts = AccountDb.get_accounts_by_userid(user_id)
        return jsonify(accounts=accounts)


api.add_resource(Account, "/accounts")


class Account(Resource):
    def get(self,cbu):
        try:
            account = AccountDb.get_account_by_cbu(cbu)[0]
            user = UserDb.get_user(account['user_id'])[0]
            return jsonify(cbu=cbu,
                    username=user['username'],
                    first_name=user['first_name'],
                    last_name=user['last_name'])
        except:
            return make_response(jsonify(msg=f"CBU {cbu} not found"),404)


api.add_resource(Account,"/account/<int:cbu>")


class AddMoney(Resource):
    @jwt_required()
    def post(self):
        cbu = request.json.get("cbu", None)
        amount = request.json.get("amount", None)
        username = get_jwt_identity()
        user_id = UserDb.get_user_by_username(username)[0]['id']
        accounts = AccountDb.get_accounts_by_userid(user_id)
        accounts_cbu = [account['cbu'] for account in accounts]

        if not cbu in accounts_cbu:
            return {"msg": "CBU doesn't belong to current_user"}, 400

        balance_updated = AccountDb.add_money_to_account(cbu=cbu,amount=amount)
        logger_backend.debug(f"{username} added  $ {amount} to cbu : {cbu} ")
        return jsonify(cbu=cbu,
                        balance=balance_updated)


api.add_resource(AddMoney, "/add_money")

class WithdrawMoney(Resource):
    @jwt_required()
    def post(self):
        cbu = request.json.get("cbu", None)
        amount = request.json.get("amount", None)
        username = get_jwt_identity()
        user_id = UserDb.get_user_by_username(username)[0]['id']
        accounts = AccountDb.get_accounts_by_userid(user_id)
        accounts_cbu = [account['cbu'] for account in  accounts]

        if not cbu in accounts_cbu:
            return {"msg": "CBU doesn't belong to current_user"}, 400

        try:
            balance_updated = AccountDb.withdraw_money_from_account(cbu=cbu,amount=amount)
            logger_backend.debug(f"{username} added  $ {amount} to cbu : {cbu} ")
            return jsonify(cbu=cbu, balance=balance_updated)
        except:
            return make_response(jsonify(msg=f"The amount to withdraw is bigger than currente balance"),400)


api.add_resource(WithdrawMoney,"/withdraw_money")


class Transaction(Resource):
    @jwt_required()
    def post(self):
        cbu_origin = request.json.get("cbu_origin", None)
        cbu_destiny = request.json.get("cbu_destiny", None)
        amount = request.json.get("amount", None)
        description = request.json.get("description", None)
        username = get_jwt_identity()
        user_id = UserDb.get_user_by_username(username)[0]['id']
        accounts = AccountDb.get_accounts_by_userid(user_id)
        accounts_cbu = [account['cbu'] for account in  accounts]

        if not cbu_origin in accounts_cbu:
            return {"msg": "CBU doesn't belong to current_user"}, 400

        try :
            (origin,destiny) = AccountDb.transaction(cbu_origin=cbu_origin,cbu_destiny=cbu_destiny,amount=amount)
            return jsonify(cbu_origin=cbu_origin,origin_new_balance=origin,cbu_destiny=cbu_destiny,amount=amount,description=description)
        except:
            return make_response(jsonify(msg="Error with account destiny or ammount"),400)


api.add_resource(Transaction,"/make_transaction")

if __name__ == "__main__":
    SetupDatabase.setup()
    app.run(host="127.0.0.1",port=9000,debug=True)
