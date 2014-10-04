'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
from WhookApp import WhookApp

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
import datetime, sys
import redis
import json
if sys.version_info >= (3, 0):
    raw_input = input

from Yowsup.connectionmanager import YowsupConnectionManager

            #join here
class WhatsappListenerClient:

    def __init__(self, keepAlive = False, sendReceipts = False):
        self.sendReceipts = sendReceipts
        self.redis=redis.Redis()

        self.queue_key = 'MESSAGES_LISTS'
        self.MODE_CONNECTED=1
        self.MODE_DISCONNECTED=2
        self.MODE_CONNECTING=3

        connectionManager = YowsupConnectionManager()
        connectionManager.setAutoPong(keepAlive)

        self.signalsInterface = connectionManager.getSignalsInterface()
        self.methodsInterface = connectionManager.getMethodsInterface()

        self.signalsInterface.registerListener("message_received", self.onMessageReceived)
        self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
        self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
        self.signalsInterface.registerListener("disconnected", self.onDisconnected)
        self.signalsInterface.registerListener("receipt_messageSent", self.onMessageSent)
        self.signalsInterface.registerListener("receipt_messageDelivered",self.messageReceived)

        #self.signalsInterface.registerListener("receipt_messageDelivered", lambda jid, messageId: methodsInterface.call("delivered_ack", (jid, messageId)))


        self.cm = connectionManager

    def login(self, username, password):
        self.username = username
        self.connection_mode=self.MODE_CONNECTING
        self.methodsInterface.call("auth_login", (username, password))

        while True:
            if self.connection_mode == self.MODE_CONNECTED:
                next = self.redis.lrange(self.queue_key, 0, 0)
                if next:
                    print ("Processing next in queue : %s " % next)
                    json_object = json.loads(next[0])
                    print ("..........")
                    whookapp = WhookApp(json_object)
                    try:
                        #self.sendTyping(whookapp.sender)
                        whookapp.process()
                        if whookapp.reply is not None:
                            print "Sending reply %s" % whookapp.reply
                            self.sendMessage(whookapp.sender, whookapp.reply)

                        if whookapp.success:
                            print json_object
                            print ("Removing item from queue")
                            n = self.redis.lpop(self.queue_key)
                            print ("Removed item: %s" % n)
                    except Exception as e:
                        pass



                continue
            if self.connection_mode == self.MODE_CONNECTING or self.connection_mode == self.MODE_CONNECTING:
                continue
                #raw_input()
            if self.connection_mode == self.MODE_DISCONNECTED:
                #arg_file = self.file;
                #arg_args = self.sys_argv
                #os.execv(arg_file, arg_args)
                break



    def onAuthSuccess(self, username):
        print("Authed %s" % username)
        self.connection_mode=self.MODE_CONNECTED
        self.methodsInterface.call("ready")
        #self.updateStatus('WhookApp: fun , free and simple way to hook up on WhatsApp. Send HELP to learn more.')
        #self.sendOnline()

    def sendTyping(self, jid):
        self.methodsInterface.call("typing_send", (jid,))
    def updateStatus(self, status):
        self.methodsInterface.call("status_update", (status,))


    def sendOnline(self, name='WhookApp'):
        self.methodsInterface.call("presence_sendAvailableForChat", (name,))


    def sendOffline(self):
        self.methodsInterface.call("presence_sendUnavailable")


    def onAuthFailed(self, username, err):
        print("Auth Failed!")

    def onDisconnected(self, reason):
        print("Disconnected from  %s" %reason)
        self.connection_mode=self.MODE_DISCONNECTED

    def onMessageSent(self, jid, messageId):
        print("Message sent: %s" % messageId)
        self.methodsInterface.call("message_ack", (jid, messageId))

    def sendMessage(self, jid, message):
        self.methodsInterface.call("message_send", (jid, message))

    def sendBroadcast(self, jids, message):
        self.methodsInterface.call("message_broadcast", (jids, message))

    def messageReceived(self, fromAtrribute, msgId):
        self.methodsInterface.call("delivered_ack",(fromAtrribute, msgId))

    def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')

        json_string = json.dumps({WhookApp.MESSAGE_ID_KEY:messageId, WhookApp.SENDER_KEY:jid, WhookApp.CONTENT_KEY:messageContent, WhookApp.TIMESTAMP_KEY:timestamp, WhookApp.SENDER_NAME_KEY:pushName,WhookApp.IS_BROADCAST_KEY:isBroadCast})

        print ("Saving json to redis: %s" %json_string)

        self.redis.rpush(self.queue_key, json_string)

        print("%s [%s]:%s"%(jid, formattedDate, messageContent))

        if wantsReceipt and self.sendReceipts:
            self.methodsInterface.call("message_ack", (jid, messageId))
