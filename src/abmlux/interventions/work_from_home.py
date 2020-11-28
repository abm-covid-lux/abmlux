"""Represents interventions to the system."""

import logging

from abmlux.interventions import Intervention
from abmlux.messagebus import MessageBus

log = logging.getLogger("work_from_home")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
class WorkFromHome(Intervention):
    """With a certain probability, force people to work from home.

    In response to a request to change location, with a certain probability, this will consume the
    event and re-publish a request to change location to move home instead."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.prob_work_from_home = config['prob_work_from_home']
        self.locations           = config['locations']
        self.working_from_home   = {}
        self.home_locations_dict = {}
        self.work_locations_dict = {}
        self.affected_agents     = []

        self.register_variable('prob_work_from_home')

    def init_sim(self, sim):
        super().init_sim(sim)

        self.home_activity_type  = sim.activity_manager.as_int(self.config['home_activity_type'])
        self.work_activity_type  = sim.activity_manager.as_int(self.config['work_activity_type'])

        self.agents = sim.world.agents

        for agent in self.agents:
            work_location = agent.locations_for_activity(self.work_activity_type)[0]
            if work_location.typ in self.locations:
                self.affected_agents.append(agent)
                self.working_from_home[agent] = self.prng.boolean(self.prob_work_from_home)
                home_location = agent.locations_for_activity(self.home_activity_type)[0]
                self.home_locations_dict[agent] = home_location
                self.work_locations_dict[agent] = work_location
            else:
                self.working_from_home[agent] = False

        self.bus.subscribe("request.agent.location", self.handle_location_change, self)
        self.bus.subscribe("notify.time.midnight", self.refresh_working_from_home_dict, self)

    def refresh_working_from_home_dict(self, clock, t):
        """Refresh list of agents working from home"""

        for agent in self.affected_agents:
            self.working_from_home[agent] = self.prng.boolean(self.prob_work_from_home)

    def handle_location_change(self, agent, new_location):
        """If the new location is in the blacklist, send the agent home."""

        # If disabled, don't intervene
        if not self.enabled:
            return

        if self.working_from_home[agent]:
            if new_location == self.work_locations_dict[agent]:
                self.bus.publish("request.agent.location", agent, self.home_locations_dict[agent])
                return MessageBus.CONSUME
