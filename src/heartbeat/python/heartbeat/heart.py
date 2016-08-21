#!/usr/bin/env python

import threading

import rospy

from heartbeat.msg import Heartbeat


class Heart(object):
    def __init__(self, name, topic='/heartbeat', delay=1.0, connect=True):
        self.name = name
        self.topic = topic
        self.delay = delay
        self.pub = None
        if connect:
            self.connect()

    def connect(self, queue_size=10):
        #rospy.init_node(self.name)
        self.pub = rospy.Publisher(
            self.topic, Heartbeat, queue_size=queue_size)
        rospy.Subscriber(
            self.topic, Heartbeat, self.receive_beat)

    def receive_beat(self, hb):
        raise NotImplemented("Heart is an abstract base class")

    def send_beat(self):
        hb = Heartbeat()
        hb.source = self.name
        hb.header.stamp = rospy.Time.now()
        self.pub.publish(hb)

    def check(self):
        raise NotImplemented("Heart is an abstract base class")


class ClientHeart(Heart):
    def __init__(
            self, name, master,
            topic='/heartbeat', delay=1.0, connect=True):
        super(ClientHeart, self).__init__(
            name, topic=topic, delay=delay, connect=False)
        self.master = master
        self.last_heartbeat = None
        if connect:
            self.connect()

    def receive_beat(self, hb):
        if hb.source == self.master:
            self.last_heartbeat = hb
            self.send_beat()

    def check(self):
        if self.last_heartbeat is None:
            return None
        t = rospy.Time.now()
        if (t - self.last_heartbeat.header.stamp).to_sec() > self.delay:
            return False
        return True


class ServerHeart(Heart):
    def __init__(
            self, name, clients=None, topic='/heartbeat',
            delay=1.0, publish_delay=0.5, connect=True):
        super(ServerHeart, self).__init__(
            name, topic=topic, delay=delay, connect=False)
        self.clients = {}
        if clients is not None:
            [self.add_client(c) for c in clients]
        self.publish_delay = publish_delay
        self._thread = None
        if connect:
            self.connect()
            self.run_thread()

    def receive_beat(self, hb):
        if hb.source == self.name:
            return
        self.clients[hb.source] = hb

    def add_client(self, name):
        if name not in self.clients:
            self.clients[name] = None

    def remove_client(self, name):
        if name in self.clients:
            del self.clients[name]

    def check(self):
        if len(self.clients) == 0:
            return None
        t = rospy.Time.now()
        for name in self.clients:
            if self.clients[name] is None:
                return None
            ct = self.clients[name].header.stamp
            if (t - ct).to_sec() > self.delay:
                return False
        return True

    def _thread_function(self):
        while not rospy.is_shutdown():
            self.send_beat()
            rospy.sleep(self.publish_delay)

    def run_thread(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._thread_function)
        self._thread.daemon = True
        self._thread.start()
