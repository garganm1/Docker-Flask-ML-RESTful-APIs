from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankTransactions
users = db["Users"]

def UserExist(username):
    if users.find({"Username":username}).count() == 0:
        return False
    else:
        return True

def generateReturnDict(status, msg):
    retJson = {
        "status": status,
        "msg": msg
    }
    return retJson

class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if UserExist(username):
            return jsonify( generateReturnDict(301, "Invalid Username") )

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })

        return jsonify( generateReturnDict(200, "Registered successfully") )

def verifyPw(username, password):
    if not UserExist(username):
        return False
    
    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def cashWithUser(username):
    cash = users.find({"Username": username})[0]["Own"]
    return cash

def debtWithUser(username):
    debt = users.find({"Username": username})[0]["Debt"]
    return debt

def verifyCredentials(username, password):
    if not UserExist(username):
        return generateReturnDict(301, "Invalid Username"), True

    correct_pw = verifyPw(username, password)

    if not correct_pw:
        return generateReturnDict(302, "Incorrect Password"), True

    return None, False

def UpdateAccount(username, balance):
    users.update({
        "Username": username
    }, {
        "$set": {
            "Own": balance
        }
    })

def UpdateDebt(username, balance):
    users.update({
        "Username": username
    }, {
        "$set": {
            "Debt": balance
        }
    })


class Add(Resource):
    def post(self):

        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        if amount <= 0:
            return jsonify( generateReturnDict(304, "Amount entered needs to be greater than 0") )

        cash = cashWithUser(username)
        amount-=1 #Transaction Cost
        bank_cash = cashWithUser("BANK")
        UpdateAccount("BANK", bank_cash+1)
        UpdateAccount(username, cash+amount)

        return jsonify( generateReturnDict(200, "Amount added successfully") )


class Transfer(Resource):
    def post(self):

        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        to_user = postedData["to_user"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        if amount <= 0:
            return jsonify( generateReturnDict(304, "Amount entered needs to be greater than 0") )

        if not UserExist(to_user):
            return jsonify( generateReturnDict(301, "To_User is Invalid") )

        cash = cashWithUser(username)

        if cash <= amount:
            return jsonify( generateReturnDict(304, "Not Sufficient Funds") )

        to_user_cash = cashWithUser(to_user)
        bank_cash = cashWithUser("BANK")

        UpdateAccount("BANK", bank_cash+1)
        UpdateAccount(username, cash-amount-1)
        UpdateAccount(to_user, to_user_cash+amount)

        return jsonify( generateReturnDict(200, "Amount Transferred Successfully") )


class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)
        debt = debtWithUser(username)

        retJson = {
            "Own": cash,
            "Debt": debt
        }

        return jsonify(retJson)


class TakeLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)
        debt = debtWithUser(username)

        UpdateAccount(username, cash+amount)
        UpdateDebt(username, debt+amount)

        return jsonify( generateReturnDict(200, "Loan applied to account") )


class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)
        debt = debtWithUser(username)

        if cash < amount:
            return jsonify( generateReturnDict(303, "Not Sufficient Funds") )

        UpdateAccount(username, cash-amount)
        UpdateDebt(username, debt-amount)

        return jsonify( generateReturnDict(200, "Paid Amount towards Loan in the account") )


api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')


if __name__=='__main__':
    app.run(host='0.0.0.0')