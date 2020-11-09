"""Represents interventions to the system."""

import logging

from collections import defaultdict
from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("retired_lockdown")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class RetiredLockdown(Intervention):
    """Close a given set of locations during given hours.

    In response to a request to change location during these hours, this will consume the event and
    re-publish a request to change location to move home instead."""

    def __init__(self, prng, config, clock, bus, state, init_enabled):
        super().__init__(prng, config, clock, bus, init_enabled)

        self.lockdown_locations = config['locations']
        self.age_limit          = config['age_limit']
        self.home_activity_type = state.activity_manager.as_int(config['home_activity_type'])

        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

        self.lockdown_agents = set()

    def initialise_agents(self, network):
        """Determine which agents will be subject to restrictions."""

        occupancy_dict = defaultdict(list)
        for agent in network.agents:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            occupancy_dict[home_location].append(agent)
        for home in occupancy_dict:
            if max([agent.age for agent in occupancy_dict[home]]) >= self.age_limit:
                for occupant in occupancy_dict[home]:
                    self.lockdown_agents.add(occupant)

    def handle_location_change(self, agent, new_location):
        """If the agent is subject to restrictions and the new location is in the blacklist,
        send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        if agent in self.lockdown_agents:
            if new_location.typ in self.lockdown_locations:
                home_location = agent.locations_for_activity(self.home_activity_type)[0]
                if new_location != home_location:
                    self.bus.publish("request.agent.location", agent, home_location)
                    return MessageBus.CONSUME
