# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CMI Payment Acquirer',    'version': '1.0',
    'author': 'Integration-Ecom',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: CMI Implementation',
    'description': """
    CMI Payment Acquirer.

    CMI payment gateway supports MAD as default currency.
    """,
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_cmi_templates.xml',
        'data/payment_icon_data.xml',
        'data/payment_acquirer_data.xml',
    ],
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
