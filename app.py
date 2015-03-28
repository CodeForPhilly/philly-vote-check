#!env/bin/python
from flask import abort, Flask, jsonify, request

app = Flask(__name__)

@app.route('/pavoter', methods=['POST'])
def get_stuff():
    if not request.json or not 'name' in request.json:
        abort(400)
    stuff = {'foo': 'some bar', 'baz': ['one','two','three'], 'name': request.json.get('name', '')}
    return jsonify({'stuff': stuff})

@app.route('/')
def index():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(debug=True)