#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2016 Abram Hindle, Randy Wong, Marcin Pietrasik
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        # BUT HOW DO WE GET LISTENERS
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()


    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()


def set_listener( entity, data):
    # how does this black magic even work
    # This is amazing
    ''' do something with the update ! '''
    packet = {}
    packet[entity] = data
    message = json.dumps(packet)
    for thread in threads:
        thread.put(message)


myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    return flask.send_from_directory("static", "index.html")


def read_ws(ws):
    '''A greenlet function that reads from the websocket and updates the world'''
    while True:
        message = ws.receive()
        # NONE MESSAGES BREAK SHIT
        if message != None:
            entity = json.loads(message)
            # entity is only one thing, this for key in allows us access to the key of it
            for key in entity:
                myWorld.set(key, entity[key])
        else:
            break

    return None


threads = []

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''

    # use queue to avoid collision
    # every thread is the "work" to be done, we use this function which is called
    # from every client's connection, to keep pulling this work to the frontend
    thread = queue.Queue()
    threads.append(thread)

    # the greenlet function will run at the same time as this one, so we enter
    # two loops, a constant pushing to the front end, and a constant pulling to the 
    # back end, each websocket is constantly running a "subscribe_socket" and a
    # "read_ws" at the same time
    gevent.spawn(read_ws, ws)
    while True:
        ws.send(thread.get())
    return None


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])




@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return json.dumps(myWorld.world())


@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return "SUCCESS", 200



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
