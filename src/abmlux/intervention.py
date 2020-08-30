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

    def get_agent_updates(self, t, sim, agent_updates):
        """Return a list of (agent, activity) tuples representing changes in activity this
        intervention applies"""

        log.warning("STUB: get_activity_transitions in intervention.py")


class ContactTracingApp(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        self.agents_with_app                = []
        self.location_type_blacklist        = []
        self.agents_who_have_notified_app   = set()

        # State kept on who has seen whom during the day
        self.current_day          = None
        self.current_day_contacts = {}
        self.current_day_notifications = set()
        self.exposure_by_day      = deque([], config['contact_tracing']['tracing_time_window'])

    def initialise_agents(self, network):
        """Select a number of agents that will have the app installed."""

        num_app_installs = min(len(network.agents), math.ceil(len(network.agents) * \
                                 self.config['contact_tracing']['app_prevalence']))
        self.agents_with_app = rt.random_sample(self.prng, network.agents, num_app_installs)

        # Blacklist "outdoor" locations and other 'group'/holding locations
        self.location_type_blacklist = self.config['contact_tracing']['location_blacklist']

        log.info("Selected %i agents with app", len(self.agents_with_app))


    def get_agent_updates(self, t, sim, agent_updates):

        day = sim.clock.now().day

        # FIXME: This would ideally be done during initialisation, but at that point
        #        the simulation has not started the clock, so it's impossible to read
        #        the day out of it.  This FIXME is a call to move the initialisation code
        #        so that the dependency makes sense
        if self.current_day is None:
            self.current_day = day

        # Update today's records with the latest, and store diagnosis keys
        self._update_contact_list(sim.attendees)
        self._update_diagnosis_keys()

        # Day has changed
        if day != self.current_day:

            # DEBUG
            # for a in self.current_day_notifications:
            #     print(f"NOTIFYING: {a}")

            # Update 
            self.exposure_by_day.append(self.current_day_contacts)

            # Apps download diagnosis keys and calculate whether to notify their users
            for agent in self.agents_with_app:
                risk = self._get_personal_risk(agent)
                
                if risk >= 15:    # FIXME: magic number
                    agent_updates[agent]['location'] = \
                        agent.locations_for_activity(sim.activity_manager.as_int("House"))[0]
                    # FIXME: this sends people home _once_, i.e. they won't remain quarantined

            # Move day on and reset day state
            self.current_day                = day
            self.current_day_contacts       = {}
            self.current_day_notifications  = set()


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
    
    def _update_diagnosis_keys(self):
        """Gather together everyone who is infected at this tick and add them to the list of 
        anyone with the app who has been infected during the current day.

        This list is later used by other app users to figure out if they met any of the infected
        agents."""

        agents_notifying = {a for a in self.agents_with_app 
                            if a.health == "INFECTED" and a not in self.agents_who_have_notified_app}
        self.current_day_notifications.update(agents_notifying)

        # Blacklist from notifying again
        self.agents_who_have_notified_app.update(agents_notifying)

    def _get_personal_risk(self, agent):
        """Return a number representing this user's risk exposure"""

        # Loop through the day records in reverse
        max_risk     = 0
        time_at_risk = 0
        for i in range(len(self.exposure_by_day) - 1, -1, -1):

            # Skip over agents with no contacts this day
            if agent not in self.exposure_by_day[i]:
                continue

            days_since_contact = len(self.exposure_by_day) - 1 - i
            daily_exposure     = self.exposure_by_day[i][agent]

            # exposure_by_day[i] = {agent: {other_agent: num_ticks}}

            # For this day, find agents who have notified the app AND whom this agent has met
            agents_who_have_notified_app = \
                self.current_day_notifications.intersection(daily_exposure.keys())

            for other_agent in agents_who_have_notified_app:
                # NOTE: 1, 1, 5 here all determined by the sim's
                #       time and space resolution assumptions
                risk = \
                    1 * 1 * 5 * ContactTracingApp.transmission_risk_level_base_case(days_since_contact)

                # Keep track of global maximum risk
                if risk > max_risk:
                    max_risk = risk

                # If over the threshold, note that this agent is in the 'at risk' list
                if risk >= 11:
                    # print(f"[{i}] --> {risk} ({other_agent})")
                    time_at_risk += daily_exposure[other_agent]

        return time_at_risk * max_risk / 25

    @staticmethod
    def transmission_risk_level_base_case(delay):
        """Calculates transmission risk level using the delay from exposure to consent for upload"""

        return [5, 6, 8, 8, 8, 5, 3, 1, 1, 1, 1, 1, 1, 1][delay]