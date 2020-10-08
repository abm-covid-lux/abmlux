
import logging
from time import perf_counter
from collections import defaultdict

log = logging.getLogger("message_bus")

class MessageBus:

    # Return this value from the handler to consume an event
    CONSUME = True

    def __init__(self):

        self.handlers = defaultdict(list)

        self.topics_by_owner = defaultdict(set)
        self.owners_by_topic = defaultdict(set)

        # TODO: force users to define topics before publishing to them

    def subscribe(self, topic, callback, owner):

        self.handlers[topic].append( (callback, owner) )

        if owner is not None:
            self.topics_by_owner[owner].add(topic)
            self.owners_by_topic[topic].add(owner)

        # print(f" All topics: {list(self.handlers.keys())}")

    def unsubscribe(self, callback_id):
        # FIXME: unregister function
        print(f"UNIMPLEMENTED: unsubscribe in messagebus.py")

    def publish(self, topic, *args, **kwargs):
        #print(f"[{inspect.stack()[1].function}] publish [{topic}] -> {len(self.handlers[topic])}: {args}, {kwargs}")
        # a = perf_counter()

        # print(f"Publish -> {topic}({args}, {kwargs})")
        for callback, _ in self.handlers[topic]:
            # print(f"[#{self.levels_deep}] Calling {owner.__class__}")
            if callback(*args, **kwargs) == MessageBus.CONSUME:
                break

        # b = perf_counter()
        # log.info("Publish to topic %s complete in %ds calling %i functions", \
        #          topic, b - a, len(self.handlers[topic]))

    pub = publish
    sub = subscribe