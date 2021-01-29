"""Represents the manual and app-based contact tracing."""

import math
import logging
from collections import deque, defaultdict

from abmlux.interventions import Intervention

log = logging.getLogger("contact_tracing")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class ContactTracingManual(Intervention):
    """The intervention ContactTracingManual refers to the manual tracing of contacts of agents with
    postive test results. The maximum number of positive agents whose contacts can be traced is
    specified, as is the window of time over which such contacts are registered. Contacts are
    considered to be agents who performed one of the specified regular activities in the same
    location as the agent, so long as the agent was also performing one such activity. For example,
    if the agent was working in a given location and another agent was also working there, at the
    same time, then the agent would remember the contact with the other agent. Conversely, if the
    location was, for example, a shop with the other agent only shopping there, then the first agent
    would not remember this. Other agents traced though this proceedure are instructed to get tested
    and quarantine in the meantime. With a certain probability, agents do not follow this advice and
    continue as normal."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.register_variable('max_per_day')

    def init_sim(self, sim):

        self.scale_factor             = sim.world.scale_factor
        self.max_per_day              = self.scale_factor * self.config['max_per_day']
        self.tracing_time_window_days = self.config['tracing_time_window_days']
        self.relevant_activities      = {sim.activity_manager.as_int(x) for x in \
                                         self.config['relevant_activities']}
        self.prob_do_recommendation   = self.config['prob_do_recommendation']
        self.location_type_blacklist  = self.config['location_type_blacklist']

        self.activity_manager         = sim.activity_manager
        self.bus                      = sim.bus
        self.sim                      = sim

        # Keep state on who has been colocated with whom while peforming relevant activities
        self.regular_contacts_archive = deque(maxlen=self.tracing_time_window_days)
        self.regular_contacts_archive.appendleft(defaultdict(set))

        # Keep state on who has been colocated with whom regardless of performed activities. Note
        # that this archive is not used by the intervention. It is recorded only for telemetry
        # purposes
        self.total_contacts_archive = defaultdict(set)

        # Keeps track of the number of agents whose contacts are notified, since this should not
        # exceed the daily capacity of the contact tracing system
        self.daily_notification_count = 0

        # Listen for interesting things
        self.bus.subscribe("notify.agent.location", self.handle_location_change, self)
        self.bus.subscribe("notify.time.midnight", self.update_contact_lists, self)
        self.bus.subscribe("notify.testing.result", self.notify_if_testing_positive, self)

    def notify_if_testing_positive(self, agent, result):
        """If the contact tracing system is not overcapacity, then agents newly testing positive
        will have their contacts selected for testing and quarantine."""

        # If disabled, stop this mechanism
        if not self.enabled:
            return

        # We can only respond to this many positive tests per day
        if self.daily_notification_count > self.scale_factor * self.max_per_day:
            return

        # Don't respond if the person has tested false
        if not result:
            return

        # Look up people from past several days (and today) who this agent has been with
        # and send them a message to get tested and quarantine.
        for day in self.regular_contacts_archive:
            for other_agent in day[agent]:
                if self.prng.boolean(self.prob_do_recommendation):
                    self.bus.publish("request.testing.book_test", other_agent)
                    self.bus.publish("request.quarantine.start", other_agent)

        self.daily_notification_count += 1

    def update_contact_lists(self, clock, t):
        """Archive today's contacts and make a new structure to store the coming day's"""

        # Extract from the contacts archives data to send to telemetry
        regular_contact_counts = {}
        for agent in self.regular_contacts_archive[0]:
            num_regular_contacts = len(self.regular_contacts_archive[0][agent]) - 1
            regular_contact_counts[num_regular_contacts] = regular_contact_counts.get(num_regular_contacts, 1) + 1
        total_contact_counts = {}
        for agent in self.total_contacts_archive:
            num_total_contacts = len(self.total_contacts_archive[agent]) - 1
            total_contact_counts[num_total_contacts] = total_contact_counts.get(num_total_contacts, 1) + 1
        self.telemetry_server.send("contact_data", clock, regular_contact_counts, total_contact_counts)

        # Update contact lists
        self.regular_contacts_archive.appendleft(defaultdict(set))
        self.total_contacts_archive = defaultdict(set)
        self.daily_notification_count = 0

    def handle_location_change(self, agent, old_location):
        """Callback run when an agent is moved within the world."""

        # If disabled, stop this mechanism
        # if not self.enabled:
        #    return

        # Don't record colocation in any blacklisted locations
        if agent.current_location.typ in self.location_type_blacklist:
            return
        
        # Collect the set of all agents in the current location
        total_local_agents = set().union(*self.sim.attendees_by_activity[agent.current_location].values())

        # If the agent is the only one present then nothing more needs to be done
        if len(total_local_agents) <= 1:
            return

        # Now collect the subset of all regular agents in the current location
        regular_local_agents = set().union(*[self.sim.attendees_by_activity[agent.current_location][act] for act in self.relevant_activities])

        # Add the local agents to the contacts archive of the newly arrived agent
        self.regular_contacts_archive[0][agent].update(regular_local_agents)
        self.total_contacts_archive[agent].update(total_local_agents)

        # Add the newly arrived agent to the contacts archive of the agents already present
        for local_agent in total_local_agents:
            self.total_contacts_archive[local_agent].update([agent])
            if local_agent in regular_local_agents:
                self.regular_contacts_archive[0][local_agent].update([agent])

class ContactTracingApp(Intervention):
    """The intervention ContactTracingApp refers to contact tracing perform not manually, but via an
    application installed on the phones of agents. A certain proportion of the population is assumed
    to possess the app from the very beginning. The app works according to the Corona-Warn-App,
    which is the official COVID-19 exposure notification app developed for Germany. The window of
    time over which contacts are considered is specified."""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        self.app_prevalence              = config['app_prevalence']
        self.exposure_by_day             = deque([], config['tracing_time_window_days'])
        self.duration_wgt                = config['duration_wgt']
        self.attenuation_wgt             = config['attenuation_wgt']
        self.days_since_last_expsr_wgt   = config['days_since_last_expsr_wgt']
        self.trans_risk_level_base_case  = config['trans_risk_level_base_case']
        self.trans_risk_threshold        = config['trans_risk_threshold']
        self.time_at_risk_threshold_mins = config['time_at_risk_threshold_mins']
        self.av_risk_mins                = config['av_risk_mins']
        self.prob_do_recommendation      = config['prob_do_recommendation']
        self.location_type_blacklist     = self.config['location_blacklist']

        self.agents_with_app             = []
        self.current_day_contacts        = {}
        self.current_day_notifications   = set()

        # Check that window is equal to transmission_risk list length...

    def init_sim(self, sim):
        """Select a number of agents that will have the app installed."""

        super().init_sim(sim)

        world = sim.world #FIXME: interim patch during component conversion
        self.bus = sim.bus
        self.sim = sim

        # Initialisation of internal state
        num_app_installs = min(len(world.agents), math.ceil(len(world.agents) * \
                               self.app_prevalence ))
        self.agents_with_app = self.prng.random_sample(world.agents, \
                                                          num_app_installs)
        log.info("Selected %i agents with app", len(self.agents_with_app))

        # Create attachments to messagebus
        self.bus.subscribe("notify.testing.result", self.handle_test_result, self)
        self.bus.subscribe("notify.time.tick", self.tick, self)
        self.bus.subscribe("notify.time.midnight", self.midnight, self)

    def handle_test_result(self, agent, result):
        """Callback run when an agent receives a test result."""
        #print(f"CTA: {agent} tested {result}")

        # If disabled, stop this mechansim
        if not self.enabled:
            return

        if result and agent in self.agents_with_app:
            self.current_day_notifications.add(agent)


    def midnight(self, clock, t):
        """Callback run at midnight every day."""

        self.exposure_by_day.append(self.current_day_contacts)
        # Apps download diagnosis keys and calculate whether to notify their users
        for agent in self.agents_with_app:
            risk = self._get_personal_risk(agent)
            if risk >= clock.mins_to_ticks(self.time_at_risk_threshold_mins):
                if self.prng.boolean(self.prob_do_recommendation):
                    self.bus.publish("request.testing.book_test", agent)
                    self.bus.publish("request.quarantine.start", agent)

        # Move day on and reset day state
        self.current_day_contacts      = {}
        self.current_day_notifications = set()

    def tick(self, clock, t):
        """Callback run on every simulator tick.

        Used to update contact lists of who has seen whom during this day."""

        # If disabled, stop this mechansim
        if not self.enabled:
            return

        # Update today's records with the latest, and store diagnosis keys
        self._update_contact_list(self.sim.attendees_by_activity)

    def _update_contact_list(self, attendees):
        """Keep a record of the agents with the app that colocate with any agents with the app."""

        agents_with_app_loc_cache = {}
        for agent in self.agents_with_app:
            location = agent.current_location
            local_agents = set().union(*attendees[location].values())
            if len(local_agents) <= 1 or location.typ in self.location_type_blacklist:
                continue
            # Keep track of locations we've seen before
            if location not in agents_with_app_loc_cache:
                agents_with_app_loc_cache[location] =\
                [a for a in local_agents if a in self.agents_with_app]
            # Add other agents to the list of encounters for the current day
            for other_agent_with_app_loc in agents_with_app_loc_cache[location]:
                if other_agent_with_app_loc != agent:
                    # Default dict behaviour
                    if agent not in self.current_day_contacts:
                        self.current_day_contacts[agent] = defaultdict(int)
                    self.current_day_contacts[agent][other_agent_with_app_loc] += 1

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
            # For this day, find agents who have notified the app and whom this agent has met
            contacted = self.current_day_notifications.intersection(daily_exposure.keys())
            transmission_risk = self.trans_risk_level_base_case[days_since_contact]
            for other_agent in contacted:
                risk = self.duration_wgt * self.attenuation_wgt \
                       * self.days_since_last_expsr_wgt * transmission_risk
                # Keep track of global maximum risk
                if risk > max_risk:
                    max_risk = risk
                # If over the threshold, note that this agent is in the 'at risk' list
                if risk > self.trans_risk_threshold:
                    # print(f"[{i}] --> {risk} ({other_agent})")
                    time_at_risk += daily_exposure[other_agent]
        return time_at_risk * max_risk / self.av_risk_mins
