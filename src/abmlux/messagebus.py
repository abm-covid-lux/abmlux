
import logging
from time import perf_counter
from collections import defaultdict
import uuid
import inspect

log = logging.getLogger("message_bus")

class MessageBus:

    def __init__(self):

        self.handlers = defaultdict(list)

    # TODO: force users to define topics before publishing to them

    def subscribe(self, topic, callback):
        self.handlers[topic].append(callback)

        #print(f" All topics: {list(self.handlers.keys())}")

    def unsubscribe(self, callback_id):
        # FIXME: unregister function
        print(f"UNIMPLEMENTED: unsubscribe in messagebus.py")

    def publish(self, topic, *args, **kwargs):
        #print(f"[{inspect.stack()[1].function}] publish [{topic}] -> {len(self.handlers[topic])}: {args}, {kwargs}")
        # a = perf_counter()
        for callback in self.handlers[topic]:
            # print(f"-> {callback.__name__}")
            callback(*args, **kwargs)
        # b = perf_counter()
        # log.info("Publish to topic %s complete in %ds calling %i functions", \
        #          topic, b - a, len(self.handlers[topic]))

    pub = publish
    sub = subscribe