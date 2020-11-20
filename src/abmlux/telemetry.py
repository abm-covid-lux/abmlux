"""Handles the reporting of statistics and events over a network interface using pub/sub
semantics"""

import logging
from typing import Callable
from time import sleep

import zmq
import pickle

log = logging.getLogger("telemetry")

class TelemetryServer:

    def __init__(self, host, port):

        self.host = host
        self.port = port

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)

        self.socket.bind(f"tcp://{host}:{port}")

        # Avoid ZMQ 'slow joiner prolem' to ensure our first
        # messages are picked up by subscribers
        sleep(0.1)

    def send(self, topic: str, *args, **kwargs) -> None:

        payload = (args, kwargs)
        pyobj = pickle.dumps(payload)
        self.socket.send_multipart([topic.encode('utf-8'), pyobj])



class TelemetryClient:

    def __init__(self, host, port):

        self.host = host
        self.port = port

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{host}:{port}")

    def subscribe(self, topic: str):

        self.socket.subscribe(topic)

    def recv(self):

        items = self.socket.recv_multipart()

        topic = items[0]
        if len(items) < 2:
            payload = None
        else:
            payload = pickle.loads(items[1])

        return topic, payload
