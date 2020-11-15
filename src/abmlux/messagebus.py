"""Simple synchronous messagebus implementation."""

import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger("messagebus")

class MessageBus:
    """Message broker.

    Objects subscribe to this bus by providing a callback function that is invoked whenever
    a message is published.  Multiple callbacks may be registered for a single topic, in which case
    they are invoked in-order.

    Callbacks may return a value, MessageBus.CONSUME, which stops propagation of the event.

    Topics do not need creating explicitly.
    """

    # Return this value from the handler to consume an event
    CONSUME = True

    def __init__(self):

        self.handlers = defaultdict(list)

        self.topics_by_owner = defaultdict(set)
        self.owners_by_topic = defaultdict(set)

    def topics_for_owner(self, owner: Any) -> list[str]:
        """Return a list of topics the given owner is subscribed to.

        Parameters:
            owner: The object that owns some callbacks

        Returns: A set of topic strings
        """

        return self.topics_by_owner[owner]

    def subscribe(self, topic: str, callback: Callable, owner: Any) -> None:
        """Subscribe to a topic, providing a callback function that will be invoked when
        an event is published on that topic.

        Parameters:
            topic (str): The topic to respond to
            callback (callable): The function to invoke when an event is called
            owner (object): The object 'owning' this subscription.  Used to unsubscribe.
        """

        log.debug("Subscribing %s to topic %s", owner, topic)
        self.handlers[topic].append( (callback, owner) )

        if owner is not None:
            self.topics_by_owner[owner].add(topic)
            self.owners_by_topic[topic].add(owner)

    def unsubscribe_all(self, owner: Any) -> None:
        """Unsubscribe the given owner from all topics.

        Parameters:
            owner: The object registered as the owner of some callbacks
        """

        log.debug("Unsubscribing %s from %d topics", owner, len(self.topics_by_owner[owner]))
        for topic in self.topics_by_owner[owner]:
            self.handlers[topic] = [(cb, ownr) for cb, ownr in self.handlers[topic] \
                                    if ownr != owner]

    def publish(self, topic: str, *args, **kwargs) -> None:
        """Publish an event to the messagebus on the topic given.

        All handlers will be called in the order they subscribed.

        Parameters:
            topic (str): The topic to publish on
            *args: Positional arguments to the callback
            **kwargs: Keyword arguments to the callback
        """
        #print(f"[{inspect.stack()[1].function}] publish [{topic}] -> {len(self.handlers[topic])}:
        #  {args}, {kwargs}")
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
