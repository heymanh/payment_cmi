# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class CmiController(http.Controller):
    @http.route(['/payment/cmi/return', '/payment/cmi/cancel', '/payment/cmi/error'], type='http', auth='public', csrf=False)
    def cmi_return(self, **post):
        """ CMI."""
        _logger.info(
            'CMI: entering cmi_return with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'cmi')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/payment/cmi/callback'], auth='public', csrf=False)
    def feedback(self, **post):
        cmi_tx_confirmation = request.env['payment.transaction'].sudo()._get_cmi_tx_confirmation(post)
        _logger.info(
            'CMI: entering feedback with post data %s', pprint.pformat(post))
        try:
            request.env['payment.transaction'].sudo().form_feedback(post, 'cmi')
        except Exception:
            _logger.exception('Error on /payment/cmi/callback')
            return 'FAILURE'
            # return 'APPROVED'
        if cmi_tx_confirmation == True:
            return 'ACTION=POSTAUTH'
        else:
            return 'APPROVED'
