#!env/bin/python
from flask import abort, Flask, jsonify, request

from scrape_voter_registration import get_registration

app = Flask(__name__)

DEFAULT_COUNTY = 'PHILADELPHIA'
DESCRIPTION = {
    'info': 'This endpoint passes along voter registration validation requests to ' +
            'https://www.pavoterservices.state.pa.us, then returns the info found as JSON. ' +
            'Returns empty object if error encountered or registration info not found. ' +
            'To use, POST JSON.',
    'exampleRequest': {
        'firstName':'firstname',
        'middleName': 'veryoptional',
        'lastName':'lastname',
        'dob': 'MM/DD/YYYY',
        'county':'Philadelphia'
    },
    'exampleResponse': {
      'registration': {
        'county': 'PHILA', 
        'division': '00', 
        'dob': 'DD/MM/YYYY', 
        'name': 'FIRST MIDDLE LAST', 
        'party': 'PARTY', 
        'polling_place': {
          'accessibility': 'String describing handicap accessibility', 
          'address': {
            'city': 'PHILADELPHIA', 
            'state': 'PA', 
            'street': '111 SOME ST'
          }, 
          'name': 'POLLING LOCATION NAME'
        }, 
        'status': 'ACTIVE', 
        'ward': '00'
      }
    }
}

@app.route('/pavoter', methods=['POST', 'GET'])
def get_voterinfo():
    if request.method == 'GET':
        return jsonify({'description': DESCRIPTION})
    required_fields = ['firstName', 'lastName', 'dob']
    if not request.json:
        abort(400)
    for fld in required_fields:
        if not fld in request.json:
            abort(400)

    try:
        county = request.json.get('county', DEFAULT_COUNTY)
        middle_name = request.json.get('middleName', None)
        if middle_name and len(middle_name.strip() < 1):
            middle_name = None
        first_name = request.json.get('firstName')
        last_name = request.json.get('lastName')
        dob = request.json.get('dob')
        response = get_registration(county, first_name, middle_name, last_name, dob)
    except:
        response = {}

    return jsonify({'registration': response})

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
