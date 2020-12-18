"""Simple location selection without bias for proximity."""

import logging
import math

from abmlux.movement_model import MovementModel
from abmlux.messagebus import MessageBus

log = logging.getLogger("simple_movement_model")

class SimpleRandomMovementModel(MovementModel):
    """Uses simple random sampling to select locations in response to activity changes."""

    def init_sim(self, sim):
        super().init_sim(sim)

        self.location_types = self.config['location_types']
        self.no_move_states = self.config['no_move_health_states']

        self.scale_factor                   = sim.world.scale_factor
        self.units_available_week_day       = self.config['units_available_week_day']
        self.units_available_weekend_day    = self.config['units_available_weekend_day']
        self.public_transport_activity_type = sim.activity_manager.as_int(self.config['public_transport_activity_type'])
        self.public_transport_location_type = sim.activity_manager.get_location_types(self.public_transport_activity_type)
        self.public_transport_units         = sim.world.locations_for_types(self.public_transport_location_type)
        self.max_units_available            = len(self.public_transport_units)
        self.units_available                = len(self.public_transport_units)

        self.bus.subscribe("request.agent.activity", self.handle_activity_change, self)
        self.bus.subscribe("notify.time.tick", self.update_unit_availability, self)

    def update_unit_availability(self, clock, t):
        """Updates the number of units of public transport available during each tick"""

        seconds_through_day = clock.now().hour * 3600 + clock.now().minute * 60 + clock.now().second
        index = int(seconds_through_day / clock.tick_length_s)
        if clock.now().weekday() in [5,6]:
            self.units_available = max(math.ceil(self.units_available_weekend_day[index] * self.scale_factor), 1)
        else:
            self.units_available = max(math.ceil(self.units_available_week_day[index] * self.scale_factor), 1)

    def handle_activity_change(self, agent, new_activity):
        """Respond to an activity by sending location change requests."""

        # If agent is hospitalised or dead, don't change location in response to new activity
        if agent.health not in self.no_move_states:
            if new_activity == self.public_transport_activity_type:
                length = min(self.units_available, self.max_units_available)
                allowable_locations = self.public_transport_units[0:length]
                self.bus.publish("request.agent.location", agent, \
                self.prng.random_choice(list(allowable_locations)))
            else:
                allowable_locations = agent.locations_for_activity(new_activity)
                self.bus.publish("request.agent.location", agent, \
                self.prng.random_choice(list(allowable_locations)))
