# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class CmiController(http.Controller):

    def cmi_validate_data(self, **post):
        cmi = request.env['payment.acquirer'].search([('provider', '=', 'cmi')], limit=1)
        cmi_tx_confirmation = request.env['payment.transaction'].sudo()._get_cmi_tx_confirmation(post)
        security = cmi.sudo()._cmi_generate_sign('out', post).decode("utf-8")
        if security == post['HASH']:
            _logger.info('CMI: validated callback data')
            tx = post.get('oid') and request.env['payment.transaction'].sudo().search([('reference', 'in', [post.get('oid')])], limit=1)
            message = tx.acquirer_id.done_msg
            request.env['payment.transaction'].sudo().form_feedback(post, 'cmi')
            tx.s2s_do_transaction()
            tx._post_process_after_done()
            request.render('payment.confirm', {'tx': tx, 'status': 'success', 'message': message})
            if cmi_tx_confirmation == True:
                return 'ACTION=POSTAUTH'
            else:
                return 'APPROVED'
        else:
            return 'FAILURE'

    # -*- coding: utf-8 -*-
    # Part of Odoo. See LICENSE file for full copyright and licensing details.

    import logging
    import pprint
    import werkzeug
    from odoo import http
    from odoo.http import request

    _logger = logging.getLogger(__name__)

    class CmiController(http.Controller):

        def cmi_validate_data(self, **post):
            cmi = request.env['payment.acquirer'].search([('provider', '=', 'cmi')], limit=1)
            cmi_tx_confirmation = request.env['payment.transaction'].sudo()._get_cmi_tx_confirmation(post)
            security = cmi.sudo()._cmi_generate_sign('out', post).decode("utf-8")
            if security == post['HASH']:
                _logger.info('CMI: validated callback data')
                tx = post.get('oid') and request.env['payment.transaction'].sudo().search(
                    [('reference', 'in', [post.get('oid')])], limit=1)
                message = tx.acquirer_id.done_msg
                request.env['payment.transaction'].sudo().form_feedback(post, 'cmi')
                tx.s2s_do_transaction()
                tx._post_process_after_done()
                request.render('payment.confirm', {'tx': tx, 'status': 'success', 'message': message})
                if cmi_tx_confirmation == True:
                    return 'ACTION=POSTAUTH'
                else:
                    return 'APPROVED'
            else:
                return 'FAILURE'

        @http.route(['/payment/cmi/return', '/payment/cmi/cancel', '/payment/cmi/error'], type='http', auth='public',
                    csrf=False)
        def cmi_return(self, **post):
            """ CMI."""
            cmi = request.env['payment.acquirer'].search([('provider', '=', 'cmi')], limit=1)
            security = cmi.sudo()._cmi_generate_sign('out', post).decode("utf-8")
            if security == post['HASH']:
                request.env['payment.transaction'].sudo().form_feedback(post, 'cmi')
            else:
                _logger.info('Invalid security hash ', )
            return werkzeug.utils.redirect('/payment/process')

        @http.route(['/payment/cmi/callback'], type='http', auth='public', csrf=False)
        def feedback(self, **post):
            if not post:
                _logger.info('CMI: received empty notification; skip.')
            else:
                return self.cmi_validate_data(**post)
