# -*- coding: utf-8 -*-

import json
import logging
import pprint

import werkzeug
from werkzeug import urls

from odoo import http

_logger = logging.getLogger(__name__)

class MontonioController(http.Controller):

    @http.route(['/payment/montonio_financing/redirect'], auth='public', csrf=False)
    def redirect_to_montonio_financing(self, **post):
        ''' Creates application in Montonio API after pressing "Pay Now" button. '''
        
        cr, context, env = http.request.cr, http.request.context, http.request.env

        tx = None
        if post.get('invoice_num'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['invoice_num'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        redirect_url = tx.redirect_to_montonio_financing(post)

        return werkzeug.utils.redirect(redirect_url)

    def montonio_financing_callback(self, post):
        ''' Validate Montonio application status '''
        
        cr, context, env = http.request.cr, http.request.context, http.request.env

        tx = None
        if post.get('merchant_reference'):
            tx = env['payment.transaction'].sudo().search([('reference', '=', post['merchant_reference'])])
        if not tx:
            raise werkzeug.exceptions.NotFound()

        redirect_url = tx.montonio_financing_callback(post)

        return werkzeug.utils.redirect(redirect_url)

    @http.route(['/payment/montonio_financing/callback'], methods=['GET'], type='http', auth='public', csrf=False)
    def handle_montonio_financing_callback_http(self, **post):
        return self.montonio_financing_callback(post)

    @http.route(['/payment/montonio_financing/callback'], methods=['POST'], type='json', auth='public', csrf=False)
    def handle_montonio_financing_callback_json(self, **post):
        _logger.info('JOUGEN')
        _logger.info(pprint.pformat(http.request.httprequest.data.decode('utf-8')))
        data = json.loads(http.request.httprequest.data.decode('utf-8'))
        return self.montonio_financing_callback(data)
    

