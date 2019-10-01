#!/usr/bin/env python

from MyCypher import MyCypher

encstr = bytes('drEN/LqPBu1wJYHpN5eCjZXqVgvDEP3rZnXJt85Ma0k=', 'utf-8')

cypher = MyCypher(iv = str('asdf'))
print(cypher.decrypt(encstr))

