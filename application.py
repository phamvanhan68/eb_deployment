from flask import Flask, jsonify

application = Flask(__name__)

@application.route('/')
def index():
    return jsonify({
        'health': 'good',
    })


if __name__ == '__main__':
    application.debug = True
    application.run()