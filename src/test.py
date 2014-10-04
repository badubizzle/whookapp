import random
from elasticsearch import Elasticsearch
from WhookApp.WhookApp import *
__author__ = '@badu_bizzle'

WhookApp.ES_INDEX_NAME = "whookapptest"

es = Elasticsearch([{u'host': u'127.0.0.1', u'port': b'9200'}])
result = es.search(index=WhookApp.ES_INDEX_NAME,doc_type="user")
users = result['hits']['hits']

def parse_raw(string, sender=None):
    print "parsing: %s" % string
    data=dict()
    data['id']=1
    data['content']=string
    if sender is not None:
        data['sender']="%s@test" % sender
    else:
        data['sender']="%s@test" % random.choice(users)['_id']

    data['ts']=0
    return data

def process(json_object):

    whookapp = WhookApp(json_object)
    whookapp.process()
    return json_object, whookapp.success, whookapp.reply

import sys
q,success,response=None,None,None
if len(sys.argv)<2:
    print "Usage: python test.py [sender] command"
    print "sender - number of sender"
    print "command - command to execute"
    print "help get help info"

if sys.argv[1].strip()=="help":
    print WhookAppResponse.HELP_DOC
else:
    if len(sys.argv)==2:
        q, success, response = process(parse_raw(sys.argv[1]))
    elif len(sys.argv)==3:
        sender = sys.argv[1]
        q, success, response = process(parse_raw(sys.argv[2], sender=sender))

    print "Query: %s" % q
    print "Response: %s" % response