import json
from bottle import Bottle, response, request

from safewallet import logger, config
from safewallet.services.api_client import ApiClient
from safewallet.services.validator import Validator
from safewallet.models.transaction import Transaction
from safewallet.repository.peers import Peers
from safewallet.repository.mempool import Mempool
from safewallet.repository.blockchain import Blockchain

public_app = Bottle()


@public_app.route('/connect/', method='POST')
def connect():
    peers = Peers()
    if peers.get_peers_count() < peers.MAX_PEERS:
        api_client = ApiClient(peers)
        body = request.json
        host = body['host']
        network = body['network']
        if network == config['network'] and api_client.ping_status(host):
            peers.add_peer(host)
            response.status = 202
            return json.dumps({'success': True})
    response.status = 403
    return json.dumps({'success': False})


@public_app.route('/status/')
def get_status():
    return json.dumps(config['network'])


@public_app.route('/height/')
def get_height():
    blockchain = Blockchain()
    return json.dumps({"height": blockchain.get_height()})


@public_app.route('/nodes/')
def get_nodes():
    peers = Peers()
    nodes = {
        "full_nodes": peers.get_all_peers()
    }
    return json.dumps(nodes)


@public_app.route('/unconfirmed_tx/<tx_hash>')
def get_unconfirmed_tx(tx_hash):
    mempool = Mempool()
    unconfirmed_transaction = mempool.get_unconfirmed_transaction(tx_hash)
    if unconfirmed_transaction:
        return json.dumps(unconfirmed_transaction.to_dict())
    response.status = 404
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@public_app.route('/unconfirmed_tx/count')
def get_unconfirmed_transactions_count():
    mempool = Mempool()
    return json.dumps(mempool.get_unconfirmed_transactions_count())


@public_app.route('/unconfirmed_tx/')
def get_unconfirmed_transactions():
    mempool = Mempool()
    return json.dumps([transaction.to_dict()
                       for transaction in mempool.get_all_unconfirmed_transactions_iter()])


@public_app.route('/address/<address>/balance')
def get_balance(address):
    blockchain = Blockchain()
    return json.dumps(blockchain.get_balance(address))


@public_app.route('/address/<address>/transactions')
def get_transaction_history(address):
    blockchain = Blockchain()
    transaction_history = blockchain.get_transaction_history(address)
    return json.dumps([transaction.to_json() for transaction in transaction_history])


@public_app.route('/transactions/<tx_hash>')
def get_transaction(tx_hash):
    blockchain = Blockchain()
    transaction = blockchain.get_transaction_by_hash(tx_hash)
    if transaction:
        return json.dumps(transaction.to_dict())
    response.status = 404
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@public_app.route('/transactions/', method='POST')
def post_transactions():
    mempool = Mempool()
    validator = Validator()
    body = request.json
    transaction = Transaction.from_dict(body['transaction'])
    if transaction.tx_hash != body['transaction']['tx_hash']:
        logger.info("Invalid transaction hash: {} should be {}".format(body['transaction']['tx_hash'], transaction.tx_hash))
        response.status = 406
        return json.dumps({'message': 'Invalid transaction hash'})
    if mempool.get_unconfirmed_transaction(transaction.tx_hash) is None \
            and validator.validate_transaction(transaction) \
            and mempool.push_unconfirmed_transaction(transaction):
        response.status = 200
        return json.dumps({'success': True, 'tx_hash': transaction.tx_hash})
    response.status = 406
    return json.dumps({'success': False, 'reason': 'Invalid transaction'})
