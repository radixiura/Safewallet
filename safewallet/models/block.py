import codecs
import hashlib
import json
import time
import pyscrypt

from safewallet.models.transaction import Transaction
from safewallet.models.errors import InvalidTransactions
from safewallet import config

class BlockHeader(object):

  def __init__(self, previous_hash, merkle_root, timestamp=None, nonce=0, version=None):
    self.version = config['network']['version'] if version is None else int(version)
