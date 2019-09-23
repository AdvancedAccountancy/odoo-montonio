# -*- coding: utf-8 -*-
import logging
import pprint
import json

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

from .. MontonioAPI import MontonioAPI

class MontonioAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('montonio', 'Montonio')])
    montonio_access_key = fields.Char('Access Key')
    montonio_secret_key = fields.Char('Secret Key')

    @api.multi
    def montonio_form_generate_values(self, values):
        self.ensure_one()

        montonio_tx_values = dict(values)
        montonio_tx_values.update({
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
    

class PaymentTransactionMontonio(models.Model):
    _inherit = 'payment.transaction'

    def _create_montonio_draft(self, values):
        ''' Creates draft in Montonio API. '''

        _logger.info('\nreceived form values')
        _logger.info(values)

        order_lines = []
        _logger.info('\nstart iterating over line ids')
        for line in self.sale_order_ids.order_line:
            order_lines.append({
                "product_name": line.name,
                "product_price": line.price_reduce_taxinc,
                "quantity": line.product_uom_qty,
            })

        _logger.info('access_key')
        _logger.info(self.acquirer_id.montonio_access_key)

        # _logger.info('secret_key')
        # _logger.info(self.acquirer_id.montonio_secret_key)

        # # Create draft data for Montonio 
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
            "products"				: order_lines
        }

        api = MontonioAPI(
            public_key=self.acquirer_id.montonio_access_key,
            secret_key=self.acquirer_id.montonio_secret_key,
            environment= 'sandbox' if self.acquirer_id.environment == 'test' else 'production'
        )
        
        res = api.post_montonio_application_draft(payload)

        _logger.info(json.dumps(res))

        return json.dumps(res)
    
    def _validate_montonio_application(self, values):
        ''' Validate Montonio application status. '''

        _logger.info('\nChecking Montonio application status')
        
        api = MontonioAPI(
            public_key=self.acquirer_id.montonio_access_key,
            secret_key=self.acquirer_id.montonio_secret_key,
            environment= 'sandbox' if self.acquirer_id.environment == 'test' else 'production'
        )
        
        res = api.get_montonio_application(self.reference)

        _logger.info('GOT RESPONSE')
        _logger.info(json.dumps(res))
        _logger.info('TRANSACTION STATUS **********************')
        _logger.info(self.s2s_get_tx_status())

        if res['status'] == 'SUCCESS' and res['data']['status'] == 'signed':
            self._set_transaction_done()
            res['data'] = '/payment/process'
        elif res['status'] == 'SUCCESS' and res['data']['status'] != 'signed':
            res['status'] = 'APPLICATION_ERROR' # no financing / pending
        else:
            self._set_transaction_error(json.dumps(res))

        _logger.info('CHANGED TRANSACTION STATUS')
        _logger.info(json.dumps(res))

        return res
