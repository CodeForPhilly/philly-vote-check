# Notes on using python requests to post .NET forms:
# http://stackoverflow.com/questions/24975955/sending-an-asp-net-post-with-pythons-requests

from dateutil.parser import parse
import BeautifulSoup
import json
import re
import requests


DATE_FORMAT = '%m/%d/%Y'
DEFAULT_COUNTY = 'PHILADELPHIA'
NOT_FOUND_MESSAGE = 'No Voter Registration information could be found for the data provided.'
URL = 'https://www.pavoterservices.state.pa.us/Pages/voterregistrationstatus.aspx'
STATUS_REGEX = re.compile(r'^(.+?)\(Date of Birth: (\d+/\d+/\d+)\) is registered to vote in.+?Status :(.+?)Party  :(.+?)If you wish')
WARD_REGEX = re.compile(r'^Polling Place Address for (.+?) WD (\d+) DIV (\d+)$')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2342.2 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8'
}

def pa_voter_lambda_handler(event, context):
    county = event.get('county', DEFAULT_COUNTY)
    middle_name = event.get('middleName', None)
    if middle_name and len(middle_name.strip() < 1):
        middle_name = None
    first_name = event.get('firstName')
    last_name = event.get('lastName')
    dob = event.get('dob')
    # convert date to mm/dd/yyyy format
    dob_date = parse(dob)
    dob = dob_date.strftime(DATE_FORMAT)

    registration = get_registration(county, first_name, middle_name, last_name, dob)
    return json.dumps({'registration': registration})


def get_registration(county, first_name, middle_name, last_name, dob):
    session = requests.Session()
    frm_response = session.get(URL, headers=HEADERS)
    soup = BeautifulSoup.BeautifulSoup(frm_response.content)

    # magic .NET hidden fields
    viewstate = soup.findAll(attrs={'name':'__VIEWSTATE'})
    valid = soup.findAll(attrs={'name':'__EVENTVALIDATION'})
    gen = soup.findAll(attrs={'name':'__VIEWSTATEGENERATOR'})

    # drop-down with counties
    county_dropdown = soup.find(id='ctl00_ContentPlaceHolder1_CountyCombo')
    opts = county_dropdown.findAll('option')

    # first option is not a county; loop through the rest and map county name to dropdown val
    # (going to submit dropdown val with form)
    opts_rng = range(1, len(opts))
    counties = {opts[i].text: int(opts[i]['value']) for i in opts_rng}
    county_val = counties.get(county.upper())

    # actual form data to submit
    frm = {'ctl00$ContentPlaceHolder1$CountyCombo': county_val,
        'ctl00$ContentPlaceHolder1$SuffixCombo': None,
        'ctl00$ContentPlaceHolder1$btnContinue': 'Continue',
        'ctl00$ContentPlaceHolder1$txtVRSOpt2Item2': first_name,
        'ctl00$ContentPlaceHolder1$txtVRSOpt2Item3': last_name,
        'ctl00$ContentPlaceHolder1$txtVRSOpt2Item4': dob,
        'ctl00$ContentPlaceHolder1$txtVRSOpt2Item5': middle_name,
        '__EVENTTARGET': None,
        '__EVENTARGUMENT': None,
        '__VIEWSTATE': viewstate[0]['value'],
        '__EVENTVALIDATION': valid[0]['value'],
        '__VIEWSTATEGENERATOR': gen[0]['value']
    }
     
    reg_response = session.post(url=URL, data=frm, headers={'Referer': frm_response.url})
    reg = BeautifulSoup.BeautifulSoup(reg_response.content)

    # span with name, dob, party, and registration status
    status_span = reg.find(id='ctl00_ContentPlaceHolder1_regstatus')

    if not status_span:
        # check for span saying no info found
        not_found_span = reg.find(id='ctl00_ContentPlaceHolder1_lblNotFound')
        if not_found_span:
            return {'notFound': NOT_FOUND_MESSAGE}
        else:
            return {}

    status = STATUS_REGEX.search(status_span.text)
    found_name, found_dob, found_status, found_party = status.groups()

    # section with county name, ward, and division ID
    ward_section = reg.find(id='ctl00_ContentPlaceHolder1_PollingPlaceAddressLabel')
    ward_match = WARD_REGEX.match(ward_section.text)
    county_abbr, ward, div = ward_match.groups()

    # polling place info
    place_name_section = reg.find(id='ctl00_ContentPlaceHolder1_DescriptionRowCell')
    polling_place_name = place_name_section.text
    polling_addr_section = reg.find(id='ctl00_ContentPlaceHolder1_addRow1Cell1')
    polling_place_addr = polling_addr_section.text
    polling_city_section = reg.find(id='ctl00_ContentPlaceHolder1_PollingPlaceCityLabel')
    polling_place_city = polling_city_section.text
    polling_state_section = reg.find(id='ctl00_ContentPlaceHolder1_PollingPlaceStateLabel')
    polling_place_state = polling_state_section.text
    
    # accessibility (get alt text from image)
    acc = reg.find(id='ctl00_ContentPlaceHolder1_AccessibilityImage')
    access_text = acc.attrMap['alt']

    # object to return with the scraped data on it
    response = {
        'name': found_name,
        'dob': found_dob,
        'status': found_status,
        'party': found_party,
        'county': county_abbr,
        'ward': ward,
        'division': div,
        'polling_place': {
            'name': polling_place_name,
            'address': {
                'street': polling_place_addr,
                'city': polling_place_city,
                'state': polling_place_state
            },
            'accessibility': access_text
        }
    }

    return response
