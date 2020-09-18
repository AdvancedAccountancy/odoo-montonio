# creating signatures
import hmac
import hashlib

# http deps
import json
import urllib.request
from urllib.error import URLError, HTTPError

MONTONIO_API_URL = 'https://api.montonio.com'

MONTONIO_SANDBOX_API_URL = 'https://sandbox-api.montonio.com'

class MontonioFinancingSDK:
    ''' Montonio Financing SDK for Python 3. '''

    def __init__(self, public_key, secret_key, environment='sandbox'):
        self._public_key = public_key
        self._secret_key = secret_key
        self.api_url = MONTONIO_SANDBOX_API_URL if environment == 'sandbox' else MONTONIO_API_URL

    def _generate_signature(self, data):
        ''' Method for generating SHA256 signatures for requests. '''
        sha_signature = \
            hmac.new(str.encode(self._secret_key), str.encode(
                data), hashlib.sha256).hexdigest()
        return sha_signature

    def _api_request(self, route, data=None, headers=None):
        ''' Method for making requests to Montonio API. '''

        default_headers = {'content-type': 'application/json'}

        # prepare request
        req = urllib.request.Request(
            "".join([self.api_url, route]),
            headers={**default_headers, **headers},
            data=json.dumps(data).encode('utf8') if data else None
        )

        # make request & handle response
        try:
            response = urllib.request.urlopen(req)
            return {
                'status': 'SUCCESS',
                'data': json.loads(response.read().decode('utf8'))
            }
        except HTTPError as e:
            return {'status': 'HTTPError', 'data': e.code}
        except URLError as e:
            return {'status': 'URLError', 'data': e.reason}

    def post_montonio_application_draft(self, draft_data):
        ''' Method for posting application draft to Montonio. '''

        route = '/application_drafts'
        headers = {
            'x-access-key': self._public_key,
            'x-signature': self._generate_signature(json.dumps(draft_data))
        }
        return self._api_request(route, draft_data, headers)

    def get_montonio_application(self, order_id):
        ''' Method for fetching application status from Montonio. '''

        route = "".join(['/applications?merchant_reference=', order_id])
        headers = {
            'x-access-key': self._public_key,
            'x-signature': self._generate_signature(route)
        }
        return self._api_request(route, None, headers)
