# -*- coding: utf-8 -*-
import logging
import pprint
import json

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

from .. vendor.MontonioPaymentsSDK import MontonioPaymentsSDK

class MontonioPaymentsAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('montonio_payments', 'Montonio Payments')])
    montonio_access_key = fields.Char(string='Access Key')
    montonio_secret_key = fields.Char(string='Secret Key')

    @api.model
    def _create_missing_journal_for_acquirers(self, company=None):
        # By default, the wire transfer method uses the default Bank journal.
        company = company or self.env.user.company_id
        acquirers = self.env['payment.acquirer'].search(
            [('provider', '=', 'transfer'), ('journal_id', '=', False), ('company_id', '=', company.id)])

        bank_journal = self.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1)
        if bank_journal:
            acquirers.write({'journal_id': bank_journal.id})
        return super(MontonioPaymentsAcquirer, self)._create_missing_journal_for_acquirers(company=company)

    def montonio_payments_form_generate_values(self, values):
        self.ensure_one()

        montonio_tx_values = dict(values)
        montonio_tx_values.update({
            "environment" 	        : self.environment,
            "customer_first_name" 	: values.get('partner_first_name'),
            "customer_last_name"  	: values.get('partner_last_name'),
            "customer_email"  		: values.get('partner_email'),
            "customer_phone" 		: values.get('partner_phone'),
            "customer_city"         : values.get('partner_city') or '',
            "customer_address"      : values.get('partner_address') or '',
            "customer_postal_code"  : values.get('partner_zip') or '',
            'amount'                : values.get('amount') or '',
            'currency'              : 'EUR',
        })
        
        return montonio_tx_values

    def montonio_payments_get_form_action_url(self):
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')  + '/payment/montonio_payments/redirect'
    

class PaymentTransactionMontonioPayments(models.Model):
    _inherit = 'payment.transaction'
    
    def compose_callback_url(self, reference, is_notification):
        return '{}/payment/montonio_payments/callback?merchant_reference={}{}'.format(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            reference,
            '&is_notification=1' if is_notification else ''
        )

    def get_redirect_url(self, values):

        ''' 
        Use payment data from transaction to create redirect url 
        with Montonio Payments SDK 
        '''
        payment_data = {
            'amount':                values.get('amount'),
            "merchant_reference"   : self.reference,
            "customer_first_name"  : values.get('customer_first_name'), 
            "customer_last_name"   : values.get('customer_last_name'), 
            "customer_email"       : values.get('customer_email'), 
            "customer_phone"       : values.get('customer_phone'),
            "customer_city"        : values.get('customer_city'),
            "customer_address"     : values.get('customer_address'),
            "customer_postal_code" : values.get('customer_postal_code'),
            'amount'               : values.get('amount'),
            'currency'             : values.get('currency'),
            'merchant_return_url'  : self.compose_callback_url(self.reference, False),
            'merchant_notification_url'  : self.compose_callback_url(self.reference, True),
        }

        sdk = MontonioPaymentsSDK(
            self.acquirer_id.montonio_access_key,
            self.acquirer_id.montonio_secret_key,
            'sandbox' if self.acquirer_id.environment == 'test' else 'production'
        )

        sdk.payment_data = payment_data
        _logger.info(self.acquirer_id.montonio_secret_key)

        return sdk.get_payment_url()
    
    def montonio_payments_callback(self, values):
        ''' Validate Montonio Payments status. '''
        _logger.info('\nValidating Montonio Payments - Order:{}'.format(values.get('reference')))
        
        former_tx_state = self.state

        redirect_url = '/shop/payment'

        if not values.get('payment_token'):
            return redirect_url
        
        payment_info = MontonioPaymentsSDK.decode_payment_token(
            values.get('payment_token'), 
            self.acquirer_id.montonio_secret_key
        )

        if not payment_info:
            return redirect_url

        if payment_info['status'] == 'finalized':
            redirect_url = '/payment/process/'

            # mark a new state for the transaction
            self._set_transaction_done()
            if self.state == 'done' and self.state != former_tx_state:
                _logger.info('Validated Montonio Payments for tx %s: set as done' % (self.reference))

                # actually write to DB that transaction is done (webhook) 
                self._post_process_after_done()
        else:
            self._set_transaction_error(json.dumps(payment_info))
        
        return redirect_url

