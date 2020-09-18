# -*- coding: utf-8 -*-
# Copyright (c) Montonio Finance OÜ
# License LGPL-3 (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': "Montonio Payment Acquirer",
    'category': 'eCommerce',
    'license': 'LGPL-3',
    'summary': 'Accept payments through Montonio',
    'author': "Montonio Finance",
    'website': "https://www.montonio.com",
    'version': '0.0.1',
    'description': '''
Montonio is a financing solution which lets your customer fill in a single application and retrieves credit offers from multiple lenders in real time, increasing the chances that they’ll find a suitable offer.
Visit www.montonio.com for more details.
    ''',
    'depends': [
        'payment'
    ],
    'data': [
        'views/payment_views.xml',
        'views/payment_montonio_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'demo': [
        'demo.xml'
    ],
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
        'static/images/banner.png',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
