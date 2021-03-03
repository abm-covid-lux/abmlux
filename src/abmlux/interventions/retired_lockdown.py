"""Represents interventions to the system."""

import logging

from collections import defaultdict

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("retired_lockdown")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class RetiredLockdown(Intervention):
    """Subject houses containing at least one person over 65 to lockdown restrictions."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.location_closures    = config['locations']
        self.age_limit            = config['age_limit']
        self.shop_location_type   = config['shop_location_type']
        self.prob_close           = config['prob_close']

        self.home_activity_type   = None
        self.lockdown_agents      = {}
        self.shop_restricted      = {}

    def init_sim(self, sim):
        super().init_sim(sim)

        self.home_activity_type = sim.activity_manager.as_int(self.config['home_activity_type'])
        self.bus.subscribe("request.agent.location", self.handle_location_change, self)

        # Identify those agents who live in a household containing someone over the age limit
        occupancy_dict = defaultdict(list)
        for agent in sim.world.agents:
            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            occupancy_dict[home_location].append(agent)
        for home in occupancy_dict:
            if max([agent.age for agent in occupancy_dict[home]]) >= self.age_limit:
                for occupant in occupancy_dict[home]:
                    self.lockdown_agents[occupant] = True
            else:
                for occupant in occupancy_dict[home]:
                    self.lockdown_agents[occupant] = False

        # Identify which shops sell essential items
        for location in sim.world.locations:
            if location.typ == self.shop_location_type:
                self.shop_restricted[location] = self.prng.boolean(self.prob_close)

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        # If shop sells essential items, access to it is not restricted
        if new_location.typ == self.shop_location_type:
            if not self.shop_restricted[new_location]:
                return

        if self.lockdown_agents[agent]:
            if new_location.typ in self.location_closures:
                home_location = agent.locations_for_activity(self.home_activity_type)[0]
                if new_location != home_location:
                    self.bus.publish("request.agent.location", agent, home_location)
                    return MessageBus.CONSUME
