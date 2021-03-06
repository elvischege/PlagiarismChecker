from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt, spacy

# Flask
app = Flask(__name__)
api = Api(app)


# MongoDB
client = MongoClient("mongodb://db:27017")
db = client["PlagiarismDB"]
users = db["Users"]

admins = ["elvis", "peter", "bob", "joe", "john"] # testing purposes

# Functions

def user_exists(username):
    if users.count_documents({"Username": username}) == 0:
        return False
    else:
        return True


def token_balance(username):
    return users.find({"Username": username})[0]["Tokens"]


def verify_password(username, password):
    hashed_pw = users.find({"Username": username})[0]["Password"]

    if bcrypt.checkpw(password.encode("utf-8"), hashed_pw):
        return True
    else:
        return False


# Resources
class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]

        if user_exists(username):
            return jsonify({
                "message": "User already registered"
            })
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


        new_user = {
            "Username": username,
            "Tokens": 8
        }

        users.insert_one({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 8,

        })

        return jsonify(new_user)


class Detect(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        # tokens = posted_data["tokens"]

        # Documents to check against
        doc1 = posted_data["doc1"]
        doc2 = posted_data["doc2"]


        correct_pw = verify_password(username, password)
        tokens = token_balance(username)

        if not user_exists(username):
            return jsonify({"message": "Invalid username!"})

        
        if not correct_pw:
            return jsonify({"message": "Invalid password!"})

        if tokens <= 0:
            return jsonify({"message": "Insufficient tokens to complete the request"})

        # Calculate
        nlp = spacy.load("en_core_web_sm")

        doc1 = nlp(doc1)
        doc2 = nlp(doc2)

        # int (0-1) closer to 1 indicates similarity
        ratio = doc1.similarity(doc2)

        return_json = {"message": "Success", "similarity": ratio}
        current_tokens = token_balance(username)

        users.update_one(
            {"Username": username},
             {"$set":{
                 "Tokens": current_tokens-1
             }})
        return jsonify(return_json)
         

class Refill(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        refill_amount = posted_data["refill_token"]

        if not user_exists(username):
            return jsonify({"message": "Invalid username"})
        
        if username in admins:
            verify_password(password)
            current_tokens = token_balance(username)
            users.update_one({"Username": username}, {"$set": {"Tokens": current_tokens+refill_amount}})
            return jsonify({"message": "Token refilled successfully"})
        else:
            return jsonify({"message": "You do not have permission to refill token"})

# url mapping
api.add_resource(Register, '/register')
api.add_resource(Detect, '/detect')
api.add_resource(Refill, '/refill')


# Run to docker set port
app.run(debug=True, host='0.0.0.0', port="3000")