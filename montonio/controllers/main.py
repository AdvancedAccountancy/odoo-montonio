# -*- coding: utf-8 -*-

import json
import logging
import pprint

import requests
import werkzeug
from werkzeug import urls

from odoo import http
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing

from .. import MontonioAPI

_logger = logging.getLogger(__name__)

class MontonioController(http.Controller):

    @http.route(['/payment/montonio/create_draft'], type='json', auth='public', csrf=False)
    def montonio_create_draft(self, **post):
        ''' Creates draft in Montonio API after pressing "Pay Now" button. '''

        cr, context, env = request.cr, request.context, request.env

        tx = None
        if post.get('invoice_num'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['invoice_num'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        response = tx._create_montonio_draft(post)

        return response

    @http.route(['/payment/montonio/validate'], type='json', auth='public', csrf=False)
    def montonio_validate(self, **post):
        ''' Validate Montonio application status '''
        
        cr, context, env = request.cr, request.context, request.env

        tx = None
        if post.get('invoice_num'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['invoice_num'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        res = tx._validate_montonio_application(post)

        # if res['status'] == 'SUCCESS'
        #     PaymentProcessing.add_payment_transaction(tx)

        return json.dumps(res)
