import json
from flask import Flask, jsonify
import os

application = Flask(__name__)

@application.route('/')
def index():
    file = open('sha.txt', 'r')
    sha_number =  file.read()
    env_variable = os.getenv('REVIEW_BUTTON');
    
    return jsonify({
        'health': 'good',
        'sha_number': sha_number,
        'env_variable': env_variable,
    })


if __name__ == '__main__':
    application.debug = True
    application.run()
    # application.run(host='0.0.0.0', port=8080)