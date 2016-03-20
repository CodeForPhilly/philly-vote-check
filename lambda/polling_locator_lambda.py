#!/usr/bin/env python

import json
import requests

GEOCODE_URL = 'http://gis.phila.gov/arcgis/rest/services/ElectionGeocoder/GeocodeServer/findAddressCandidates'
POLLING_URL = 'http://api.phila.gov/polling-places/v1'

ACCESSIBILITY_CODES = {
    'F': 'Building Fully Accessible',
    'B': 'Building Substantially Accessible',
    'M': 'Building Accessibilty Modified',
    'A': 'Alternate Entrance',
    'R': 'Building Accessible With Ramp',
    'N': 'Building Not Accessible'
}

PARKING_CODES = {
    'N': 'No Parking',
    'G': 'General Parking',
    'L': 'Loading Zone',
    'H': 'Handicap Parking'
}


def polling_location_lambda_handler(event, context):
    address = event.get('address')
    return polling_location_by_address(address)


def polling_location_by_address(address):
    addresses = election_geocode(address)
    if not addresses:
        return json.dumps({'error': 'Address not found.'})
    for addr in addresses:
        ward = addr.get('ward')
        division = addr.get('division')
        if not ward or not division:
            continue
        addr['polling_locations'] = polling_lookup(ward, division)
    return json.dumps(addresses)


def election_geocode(address):
    geocode_params = {
        'outFields': 'division',
        'f': 'pjson',
        'Street': address
    }

    r = requests.get(GEOCODE_URL, headers={'Accept': 'application/json'}, params=geocode_params)

    if not r.ok:
        return []

    response = r.json()
    candidates = response.get('candidates')
    if not candidates or len(candidates) == 0:
        return []
    
    # split ward and division
    for addr in candidates:
        addr_attr = addr.get('attributes')
        if not addr_attr:
            continue
        warddiv = addr_attr.get('division')
        if not warddiv:
            continue
        addr['ward'] = warddiv[:2]
        addr['division'] = warddiv[2:]
        del addr['attributes']
        
    # sort descending by score
    candidates.sort(cmp=lambda x,y: cmp(y['score'], x['score']))
    return candidates


def polling_lookup(ward, division):
    polling_params = {
        'ward': ward,
        'division': division
    }

    # docs for endpoint at: http://phlapi.com/pollingplaces/
    r = requests.get(POLLING_URL, headers={'Accept': 'application/json'}, params=polling_params)

    if not r.ok:
        return []

    response = r.json()
    # add friendly code descriptions
    if not response or not response['features'] or len(response['features']) == 0:
        return []

    info = []
    for feature in response['features']:
        if not feature['attributes']:
            continue

        location = feature['attributes']
        location['building_description'] = ACCESSIBILITY_CODES.get(location.get('building'))
        location['parking_description'] = PARKING_CODES.get(location.get('parking'))
        info.append(location)

    return info
    