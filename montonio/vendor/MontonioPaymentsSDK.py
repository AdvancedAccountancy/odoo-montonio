import jwt
import base64

class MontonioPaymentsSDK:

    MONTONIO_PAYMENTS_SANDBOX_APPLICATION_URL = 'https://sandbox-payments.montonio.com'
    MONTONIO_PAYMENTS_APPLICATION_URL = 'https://payments.montonio.com'

    def __init__(self, access_key, secret_key, environment):
        self.access_key = access_key
        self.secret_key = secret_key
        self.environment = environment

    def get_payment_url(self):
        base = self.MONTONIO_PAYMENTS_APPLICATION_URL if self.environment == 'production' else self.MONTONIO_PAYMENTS_SANDBOX_APPLICATION_URL 
        return "{}?payment_token={}".format(base, self.generate_payment_token())
    
    
    def generate_payment_token(self):
        ''' Parse Payment Data to correct data types and add additional data '''
        payment_data = {
            'amount' : float(self.payment_data['amount']),
            'currency' : str(self.payment_data['currency']),
            'access_key' : str(self.access_key),
            'merchant_reference': str(self.payment_data['merchant_reference']),
            'merchant_return_url' : str(self.payment_data['merchant_return_url']),
        }

        if 'merchant_notification_url' in self.payment_data:
            payment_data['merchant_notification_url'] = str(self.payment_data['merchant_notification_url'])

        if 'preselected_aspsp' in self.payment_data:
            payment_data['preselected_aspsp'] = str(self.payment_data['preselected_aspsp'])
        
        if 'preselected_locale' in self.payment_data:
            payment_data['preselected_locale'] = str(self.payment_data['preselected_locale'])

        return jwt.encode(payment_data, self.secret_key, algorithm='HS256').decode('utf-8')

    @staticmethod
    def decode_payment_token(token, secret_key):
        try:
            return jwt.decode(token, secret_key, algorithms=['HS256'])
        except jwt.exceptions.InvalidSignatureError as identifier:
            return False
    
    ''' MARK: Property accessors '''
    @property
    def payment_data(self):
        return self.__payment_data
    
    @payment_data.setter
    def payment_data(self, value):
        self.__payment_data = value

    @property
    def access_key(self):
        return self.__access_key
    
    @access_key.setter
    def access_key(self, value):
        self.__access_key = value

    @property
    def secret_key(self):
        return self.__secret_key

    @secret_key.setter
    def secret_key(self, value):
        self.__secret_key = value
    
    @property
    def environment(self):
        return self.__environment

    @environment.setter
    def environment(self, value):
        self.__environment = value


        

    
