"""Represents interventions to the system."""

import logging

from abmlux.interventions import Intervention

log = logging.getLogger("location_closures")

class LocationClosures(Intervention):

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.location_closures  = config['location_closures']['locations']
        self.home_activity_type = state.activity_manager.as_int(config['location_closures']['home_activity_type'])

        self.bus.subscribe("agent.location.change", self.handle_location_change)

    def handle_location_change(self, agent, new_location):

        if new_location.typ in self.location_closures:

            home_location = agent.locations_for_activity(self.home_activity_type)[0]
            if new_location.typ != home_location.typ:
                self.bus.publish("agent.location.change", agent, home_location)