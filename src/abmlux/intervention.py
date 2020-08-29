"""Represents interventions to the system."""

import math
import logging
from collections import deque, defaultdict

import abmlux.random_tools as rt

log = logging.getLogger("intervention")


class Intervention:
    """Represents an intervention within the system.

    Interventions are notified of simulation state on every tick, allowing them to
    build internal state and return a list of activity changes in order to affect the simulation"""

    def __init__(self, prng, config):

        self.prng   = prng
        self.config = config

    def initialise_agents(self, network):
        """Initialise internal state for this intervention, potentially
        modifying the network if necessary.  Run prior to simulation start."""

        log.warning("STUB: initialise_agents in intervention.py")

    def get_activity_transitions(self, t, sim):
        """Return a list of (agent, activity) tuples representing changes in activity this
        intervention applies"""

        log.warning("STUB: get_activity_transitions in intervention.py")

        return []


class ContactTracingApp(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        self.agents_with_app         = []
        self.location_type_blacklist = []

        # State kept on who has seen whom during the day
        self.current_day          = None
        self.current_day_contacts = {}
        self.exposure_by_day    activity_manager.as_int("House")  = deque([], 2) # FIXME: config['contact_tracing']['tracing_time_window'])

    def initialise_agents(self, network):
        """Select a number of agents that will have the app installed."""

        num_app_installs = min(len(network.agents), math.ceil(len(network.agents) * \
                                 self.config['contact_tracing']['app_prevalence']))
        self.agents_with_app = rt.random_sample(self.prng, network.agents, num_app_installs)

        # Blacklist "outdoor" locations and other 'group'/holding locations
        self.location_type_blacklist = self.config['contact_tracing']['location_blacklist']

        log.info("Selected %i agents with app", len(self.agents_with_app))


    def get_activity_transitions(self, t, sim, activity_changes, health_changes):

        day = sim.clock.now().day

        # FIXME: This would ideally be done during initialisation, but at that point
        #        the simulation has not started the clock, so it's impossible to read
        #        the day out of it.  This FIXME is a call to move the initialisation code
        #        so that the dependency makes sense
        if self.current_day is None:
            self.current_day = day

        # Update today's records with the latest
        self._update_contact_list(sim.attendees)

        # Day has changed
        # Reset state to null for the next day
        if day != self.current_day:
            self.current_day = day
            self.exposure_by_day.append(self.current_day_contacts)
            self.current_day_contacts = {}

        # Notify people if necessary
        # TODO: if an agent is tested and returns positive, they should notify others
        agents_notifying = [a for a in self.agents_with_app if a.health == "INFECTED"]
        for agent in agents_notifying:
            agents_to_notify = self._get_notification_targets(agent)

            activity_changes += [(a,
                                 a.current_activity,    # FIXME: read out of pre-existing activity changes
                                 a.locations_for_activity(sim.activity_manager.as_int("House"))
                                for a in agents_to_notify]

        for agent in agents_notifying:
            del(self.agents_with_app[agent])

        return activity_changes


    def _update_contact_list(self, attendees):
        """Keep a record of the agents with the app that colocate with any agents with the app."""

        agents_with_app_loc_cache = {}
        for agent in self.agents_with_app:
            location = agent.current_location

            # No other app users
            # We're not interested in locations in the blacklist, obviously.
            if len(attendees[location]) <= 1 or location.typ in self.location_type_blacklist:
                continue

            # Keep track of locations we've seen before
            if location not in agents_with_app_loc_cache:
                agents_with_app_loc_cache[location] = [a for a in attendees[location] if a in self.agents_with_app]
            
            # Look through the list of 'informable' agents and add them to the list of
            # encounters for the current day
            for other_agent_with_app_loc in agents_with_app_loc_cache[location]:
                if other_agent_with_app_loc != agent:

                    # Default dict behaviour
                    if agent not in self.current_day_contacts:
                        self.current_day_contacts[agent] = defaultdict(int)

                    self.current_day_contacts[agent][other_agent_with_app_loc] += 1
    
    def _get_notification_targets(self, agent):
        """For a given agent, identify those other agents who must be notified of 
        infection."""

        return []

