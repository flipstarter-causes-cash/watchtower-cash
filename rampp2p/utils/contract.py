from rampp2p.tasks.contract_tasks import execute_subprocess, subprocess_handler

import logging
logger = logging.getLogger(__name__)

def create_contract(**kwargs):
    '''
    Executes a subprocess task to generate the contract address
    '''
    path = './rampp2p/escrow/src/'
    command = 'node {}escrow.js {} {} {} {}'.format(
        path,        
        kwargs.get('arbiter_pubkey'), 
        kwargs.get('buyer_pubkey'), 
        kwargs.get('seller_pubkey'),
        kwargs.get('timestamp'),
    )
    return execute_subprocess.apply_async(
        (command,), 
        link=subprocess_handler.s(
            order_id=kwargs.get('order_id')
        )
    )
