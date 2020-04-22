# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import re

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging
import base64

_logger = logging.getLogger(__name__)


class PaymentAcquirerCmi(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('cmi', 'CMI')])
    cmi_merchant_id = fields.Char(string='Merchant Id', required_if_provider='cmi', groups='base.group_user')
    cmi_merchant_key = fields.Char(string='Merchant Store Key', required_if_provider='cmi', groups='base.group_user')
    cmi_url_gateway = fields.Char("Gateway url", required_if_provider='cmi', default='')
    cmi_tx_confirmation = fields.Boolean(string='Automatic confirmation mode', default=True,
                                         help="Check this box to confirm CMI transactions automatically.")

    def _get_cmi_urls(self, environment):
        """ CMI URLs"""
        if environment == 'prod':
            return {'cmi_form_url': self.cmi_url_gateway}
        else:
            return {'cmi_form_url': self.cmi_url_gateway}

    def _cmi_generate_sign(self, inout, values):
        # def _cmi_generate_sign(self, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param self: the self browse record. It should have a shakey in shakey out
        :param string inout: 'in' (odoo contacting cmi) or 'out' (cmi
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        if inout not in ('in', 'out'):
            raise Exception("Type must be 'in' or 'out'")
        if inout == 'in':
            keys = "amount|BillToCity|BillToCompany|BillToCountry|BillToName|BillToPostalCode|BillToStateProv|BillToStreet1|callbackUrl|clientid|currency|email|failUrl|hashAlgorithm|lang|oid|okUrl|refreshtime|rnd|shopurl|storetype|tel|TranType".split(
                '|')
            sign = ''.join('%s|' % (str(values.get(k)).replace("|", "\\|").replace("\\", "\\\\")) for k in keys)
            sign += self.cmi_merchant_key.replace("|", "\\|").replace("\\", "\\\\") or ''
            shasign = base64.b64encode(hashlib.sha512(sign.encode('utf-8')).digest())
        else:
            keys = sorted(values, key=str.casefold)
            keys = [e for e in keys if e not in ('encoding', 'HASH')]
            sign = ''.join('%s|' % (str(values.get(k)).replace("|", "\\|").replace("\\", "\\\\")) for k in keys)
            sign += self.cmi_merchant_key.replace("|", "\\|").replace("\\", "\\\\") or ''
            shasign = base64.b64encode(hashlib.sha512(sign.encode('utf-8')).digest())

        return shasign

    def cmi_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        lang = values.get('partner_lang').strip().lower()
        arLang = "ar"
        enLang = "en"
        frLang = "fr"
        if frLang in lang:
            lang = frLang
        elif arLang in lang:
            lang = arLang
        else:
            lang = enLang
        # cmi_tx_confirmation=PaymentTransactionCmi._get_cmi_tx_confirmation(self)
        # _logger.info('CMI: cmi_tx_confirmation 2 %s', cmi_tx_confirmation)
        _logger.info('CMI payment post values: %s', values)
        billing_state = values['billing_partner_state'].name if values.get('billing_partner_state') else ''
        if values.get('billing_partner_country') and values.get('billing_partner_country') == self.env.ref('base.us',
                                                                                                           False):
            billing_state = values['billing_partner_state'].code if values.get('billing_partner_state') else ''
        cmi_values = dict(values,
                          clientid=self.cmi_merchant_id,
                          oid=values['reference'],
                          amount=values['amount'],
                          currency='504',
                          TranType='PreAuth',
                          storetype='3D_PAY_HOSTING',
                          hashAlgorithm='ver3',
                          rnd='197328465',
                          lang=lang,
                          refreshtime='5',
                          encoding='UTF-8',
                          BillToName=re.sub(r'[^a-zA-Z0-9 ]+', '', values.get('billing_partner_name')).strip(),
                          email=values.get('billing_partner_email').strip(),
                          tel=re.sub(r'[^0-9 -]+', ' ', values.get('billing_partner_phone')).strip(),
                          BillToStreet1=re.sub(r'[^a-zA-Z0-9 ]+', ' ', values.get('billing_partner_address')).strip(),
                          BillToCity=re.sub(r'[^a-zA-Z0-9 ]+', '', values.get('billing_partner_city')).strip(),
                          BillToPostalCode=re.sub(r'[^a-zA-Z0-9 ]+', '', values.get('billing_partner_zip')).strip(),
                          BillToCompany=re.sub(r'[^a-zA-Z0-9 ]+', '',
                                               values.get('billing_partner_commercial_company_name')).strip(),
                          BillToCountry=re.sub(r'[^a-zA-Z0-9 ]+', '',
                                               values.get('billing_partner_country').name).strip(),
                          BillToStateProv=re.sub(r'[^a-zA-Z0-9 ]+', '', billing_state).strip(),
                          shopurl=base_url,
                          failUrl=urls.url_join(base_url, '/payment/cmi/error').strip(),
                          okUrl=urls.url_join(base_url, '/payment/cmi/return').strip(),
                          callbackUrl=urls.url_join(base_url, '/payment/cmi/callback').strip()
                          )

        cmi_values['hash'] = self._cmi_generate_sign('in', cmi_values)
        return cmi_values

    def cmi_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_cmi_urls(environment)['cmi_form_url']


class PaymentTransactionCmi(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _cmi_form_get_tx_from_data(self, data):
        """ Given a data dict coming from cmi, verify it and find the related
        transaction record. """
        reference = data.get('oid')
        # pay_id = data.get('mihpayid')
        shasign = data.get('HASH')
        if not reference or not shasign:
            raise ValidationError(
                _('CMI: received data with missing reference (%s) or hash (%s)') % (reference, shasign))

        transaction = self.search([('reference', '=', reference)])

        if not transaction:
            error_msg = (_('CMI: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('CMI: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = transaction.acquirer_id._cmi_generate_sign('out', data).decode("utf-8")
        if shasign_check.upper() != shasign.upper():
            raise ValidationError(
                _('CMI: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data))
        return transaction

    def _cmi_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('oid') != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('oid'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('amount'), '%.2f' % self.amount))

        return invalid_parameters

    def _get_cmi_tx_confirmation(self, data):
        reference = data.get('oid')
        transaction = self.search([('reference', '=', reference)])
        return transaction.acquirer_id.cmi_tx_confirmation

    def _cmi_form_validate(self, data):
        status = data.get('ProcReturnCode')
        result = self.write({
            'acquirer_reference': data.get('oid'),
            'date': fields.Datetime.now(),
        })
        if status == '00':
            self._set_transaction_done()
        elif status != '00':
            self._set_transaction_cancel()
        else:
            self._set_transac
