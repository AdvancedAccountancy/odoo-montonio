# -*- coding: utf-8 -*-

import json
import logging

import pprint
import werkzeug
from werkzeug import urls

from odoo import http

_logger = logging.getLogger(__name__)

class MontonioPaymentsControllers(http.Controller):

    @http.route(['/payment/montonio_payments/redirect'], auth='public', csrf=False)
    def redirect_to_montonio(self, **post):
        ''' Redirect to Montonio Payments '''

        cr, context, env = http.request.cr, http.request.context, http.request.env

        tx = None
        if post.get('invoice_num'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['invoice_num'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        response = tx.get_redirect_url(post)

        return werkzeug.utils.redirect(response)

    def montonio_payments_callback(self, post):
        ''' Validate Montonio application status '''
        
        cr, context, env = http.request.cr, http.request.context, http.request.env

        tx = None
        if post.get('merchant_reference'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['merchant_reference'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        redirect_url = tx.montonio_payments_callback(post)

        return werkzeug.utils.redirect(redirect_url)

    @http.route(['/payment/montonio_payments/callback'], type='http', auth='public', csrf=False)
    def handle_montonio_payments_callback_http(self, **post):
        return self.montonio_payments_callback(post)
    