# -*- coding: utf-8 -*-
import logging
import pprint
import json

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

from .. vendor.MontonioFinancingSDK import MontonioFinancingSDK

class MontonioFinancingAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('montonio_financing', 'Montonio Financing')])
    montonio_access_key = fields.Char(string='Access Key')
    montonio_secret_key = fields.Char(string='Secret Key')

    def montonio_financing_form_generate_values(self, values):
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
        })
        _logger.info(pprint.pformat(montonio_tx_values))
        
        return montonio_tx_values
    
    def montonio_financing_get_form_action_url(self):
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')  + '/payment/montonio_financing/redirect'

class PaymentTransactionMontonioFinancing(models.Model):
    _inherit = 'payment.transaction'

    MONTONIO_APPLICATION_URL = 'https://application.montonio.com'
    MONTONIO_SANDBOX_APPLICATION_URL = 'https://sandbox-application.montonio.com'

    def compose_montonio_financing_callback_url(self, reference, is_notification):
        return '{}/payment/montonio_financing/callback?merchant_reference={}{}'.format(
            self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            reference,
            '&is_notification=1' if is_notification else ''
        )

    def redirect_to_montonio_financing(self, values):
        ''' Creates application in Montonio API. '''

        _logger.info('[Montonio Financing]: Create application for order:{}'.format(
            values.get('invoice_num')
        ))
        
        order_lines = []
        for line in self.sale_order_ids.order_line:
            order_lines.append({
                "product_name": line.name,
                "product_price": line.price_reduce_taxinc,
                "quantity": line.product_uom_qty,
            })

        # Create draft data for Montonio 
        payload = {
            "origin"				: "online",
            "merchant_reference"	: self.reference,
            "customer_first_name" 	: values.get('customer_first_name'), 
            "customer_last_name"  	: values.get('customer_last_name'), 
            "customer_email"  		: values.get('customer_email'), 
            "customer_phone" 		: values.get('customer_phone'),
            "customer_city"         : values.get('customer_city'),
            "customer_address"      : values.get('customer_address'),
            "customer_postal_code"  : values.get('customer_postal_code'),
            "products"				: order_lines,
            "callback_url"          : self.compose_montonio_financing_callback_url(self.reference, False),
            "notification_url"      : self.compose_montonio_financing_callback_url(self.reference, True)
        }

        sdk = MontonioFinancingSDK(
            public_key=self.acquirer_id.montonio_access_key,
            secret_key=self.acquirer_id.montonio_secret_key,
            environment= 'sandbox' if self.acquirer_id.environment == 'test' else 'production'
        )

        # post application to Montonio
        res = sdk.post_montonio_application_draft(payload)

        if res['status'] != 'SUCCESS':
            return '/shop/payment/'

        return '{}?access_token={}'.format(
            self.MONTONIO_SANDBOX_APPLICATION_URL if self.acquirer_id.environment == 'test' else self.MONTONIO_APPLICATION_URL,
            res['data']['access_token']
        )
    
    def montonio_financing_callback(self, values):
        ''' Validate Montonio Financing status. '''

        former_tx_state = self.state
        
        redirect_url = '/shop/payment'

        sdk = MontonioFinancingSDK(
            public_key=self.acquirer_id.montonio_access_key,
            secret_key=self.acquirer_id.montonio_secret_key,
            environment= 'sandbox' if self.acquirer_id.environment == 'test' else 'production'
        )
        
        res = sdk.get_montonio_application(self.reference)

        if res['status'] == 'SUCCESS' and res['data']['status'] == 'signed':
            redirect_url = '/payment/process/' 

            # mark a new state for the transaction
            self._set_transaction_done()
            if self.state == 'done' and self.state != former_tx_state:
                _logger.info('Validated Montonio Financing for tx %s: set as done' % (self.reference))

                # actually write to DB that transaction is done (webhook) 
                self._post_process_after_done()
        else:
            self._set_transaction_error(json.dumps(res))

        return redirect_url
