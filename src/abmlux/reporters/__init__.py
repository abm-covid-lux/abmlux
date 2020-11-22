"""Represents a class used to report data from the simulation."""

# Allows classes to return their own type, e.g. from_file below
from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Callable
import pickle

import zmq

from abmlux.telemetry import TelemetryClient

log = logging.getLogger("reporter")

def kill_on_zmq_event(host: str, port: int, event_topic: str, reporters: list[Reporter]):

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    addr_string = f"tcp://{host}:{port}"
    socket.connect(addr_string)
    socket.subscribe(event_topic)

    # Wait for the next event on this topic
    topic, _ = socket.recv_multipart()

    # Then ask all reporters to terminate
    for reporter in reporters:
        reporter.stop()

    # And quit.
    socket.disconnect(addr_string)

class Reporter(mp.Process):
    """Reports on the status of the abm simulation.

    Used to record data to disk, report to screen, compute summary statistics,
    or stream to other logging tools over the world."""

    def __init__(self, host, port):
        super().__init__()

        # Store address of the telemtry server
        self.host = host
        self.port = port

        self.callbacks  = {}
        self.stop_event = mp.Event()
        self.running    = False

    def subscribe(self, topic, callback: Callable):

        if self.running:
            raise AttributeError("Cannot subscribe to events on a running process")
        self.callbacks[topic] = callback

    def stop(self):
        self.stop_event.set()

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        addr_string = f"tcp://{self.host}:{self.port}"
        socket.connect(addr_string)
        socket.RCVTIMEO = 1000 # in ms, give us some time to check the event

        # Subscribe to any events that were subscribed to before
        # this run call
        self.running = True
        for topic in self.callbacks.keys():
            socket.subscribe(topic)

        while not self.stop_event.is_set():

            # Read with a timeout
            try:
                topic, payload = socket.recv_multipart()
            except zmq.error.Again:
                continue

            # Decode the topic, and call the callback
            topic = topic.decode('utf-8')

            if topic in self.callbacks:
                args, kwargs = pickle.loads(payload)
                self.callbacks[topic](*args, **kwargs)

        # Nicely d/c from the server
        socket.disconnect(addr_string)
