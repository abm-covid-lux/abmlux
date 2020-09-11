"""Represents the manual and app-based contact tracing."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention
import abmlux.random_tools as random_tools

log = logging.getLogger("contact_tracing")

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

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.max_per_day_raw          = config['contact_tracing_manual']['max_per_day']
        self.tracing_time_window_days = config['contact_tracing_manual']['tracing_time_window_days']
        self.relevant_activities      = {state.activity_manager.as_int(x) for x in \
                                         config['contact_tracing_manual']['relevant_activities']}
        self.prob_do_recommendation   = config['contact_tracing_manual']['prob_do_recommendation']
        self.location_type_blacklist  = config['contact_tracing_manual']['location_type_blacklist']

        self.daily_notification_count = 0
        scale_factor = config['n'] / sum(config['age_distribution'])
        self.max_per_day = max(int(self.max_per_day_raw * scale_factor), 1)

        self.regular_locations_dict  = {}
        self.activity_manager        = state.activity_manager

        # Keep state on who has been colocated with whom
        self.contacts_archive       = deque(maxlen=self.tracing_time_window_days)
        self.contacts_archive.appendleft(defaultdict(set))

        # Listen for interesting things
        self.bus.subscribe("sim.time.start_simulation", self.start_sim)
        self.bus.subscribe("sim.agent.location", self.handle_location_change)
        self.bus.subscribe("sim.time.midnight", self.update_contact_lists)
        self.bus.subscribe("testing.result", self.notify_if_testing_positive)

    def start_sim(self, sim):
        self.sim = sim

    def notify_if_testing_positive(self, agent, result):
        """If the contact tracing system is not overcapacity, then agents newly testing positive
        will have their contacts selected for testing and quarantine."""

        # We can only respond to this many positive tests per day
        if self.daily_notification_count > self.max_per_day:
            return

        # Don't respond if the person has tested false
        if not result:
            return

        # Look up people from past several days (and today) who this agent has been with
        # and send them a message to get tested and quarantine.
        for day in self.contacts_archive:
            for other_agent in day[agent]:
                if random_tools.boolean(self.prng, self.prob_do_recommendation):
                    self.bus.publish("testing.selected", other_agent)
                    self.bus.publish("quarantine", other_agent)

        self.daily_notification_count += 1

    def update_contact_lists(self, clock, t):
        """Archive today's contacts and make a new structure to store the coming day's"""

        # Update contact lists
        # print(f"End of day.  {len(self.contacts_archive[0])} people contacted others today")
        self.contacts_archive.appendleft(defaultdict(set))
        self.daily_notification_count = 0

    def handle_location_change(self, agent, old_location, new_location):

        # Don't record colocation in any blacklisted locations
        if new_location.typ in self.location_type_blacklist:
            return

        # This agent has to be doing the relevant activity
        if agent.current_activity not in self.relevant_activities:
            return

        agents_of_interest = [a for a in self.sim.attendees[new_location]\
                              if a.current_activity in self.relevant_activities]
        if len(agents_of_interest) <= 1:    # The person counts as an attendee him/her self
            return

        # print(f"Meeting {len(agents_of_interest)} new people!  How exciting.")
        self.contacts_archive[0][agent].update(agents_of_interest)


class ContactTracingApp(Intervention):
    """The intervention ContactTracingApp refers to contact tracing perform not manually, but via an
    application installed on the phones of agents. A certain proportion of the population is assumed
    to possess the app from the very beginning. The app works according to the Corona-Warn-App,
    which is the official COVID-19 exposure notification app developed for Germany. The window of
    time over which contacts are considered is specified."""

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.app_prevalence              = config['contact_tracing_app']['app_prevalence']
        self.exposure_by_day             = deque([], config['contact_tracing_app']['tracing_time_window_days'])
        self.duration_wgt                = config['contact_tracing_app']['duration_wgt']
        self.attenuation_wgt             = config['contact_tracing_app']['attenuation_wgt']
        self.days_since_last_expsr_wgt   = config['contact_tracing_app']['days_since_last_expsr_wgt']
        self.trans_risk_level_base_case  = config['contact_tracing_app']['trans_risk_level_base_case']
        self.trans_risk_threshold        = config['contact_tracing_app']['trans_risk_threshold']
        self.time_at_risk_threshold_mins = config['contact_tracing_app']['time_at_risk_threshold_mins']
        self.av_risk_mins                = config['contact_tracing_app']['av_risk_mins']
        self.prob_do_recommendation      = config['contact_tracing_app']['prob_do_recommendation']
        self.location_type_blacklist     = self.config['contact_tracing_app']['location_blacklist']

        self.agents_with_app             = []
        self.current_day_contacts        = {}
        self.current_day_notifications   = set()

        self.bus.subscribe("testing.result", self.handle_test_result)
        self.bus.subscribe("sim.time", self.tick)
        self.bus.subscribe("sim.time.midnight", self.midnight)
        self.bus.subscribe("sim.time.start_simulation", self.start_sim)

        # Check that window is equal to transmission_risk list length...

    def start_sim(self, sim):
        self.sim = sim

    def handle_test_result(self, agent, result):
        #print(f"CTA: {agent} tested {result}")
        if result == True and agent in self.agents_with_app:
            self.current_day_notifications.add(agent)

    def initialise_agents(self, network):
        """Select a number of agents that will have the app installed."""

        num_app_installs = min(len(network.agents), math.ceil(len(network.agents) * \
                               self.app_prevalence ))
        self.agents_with_app = random_tools.random_sample(self.prng, network.agents, num_app_installs)

        log.info("Selected %i agents with app", len(self.agents_with_app))

    def midnight(self, clock, t):

        self.exposure_by_day.append(self.current_day_contacts)
        # Apps download diagnosis keys and calculate whether to notify their users
        for agent in self.agents_with_app:
            risk = self._get_personal_risk(agent)
            if risk >= clock.mins_to_ticks(self.time_at_risk_threshold_mins):
                if random_tools.boolean(self.prng, self.prob_do_recommendation):
                    self.bus.publish("testing.selected", agent)
                    self.bus.publish("quarantine", agent)

        # Move day on and reset day state
        self.current_day_contacts       = {}
        self.current_day_notifications  = set()

    def tick(self, clock, t):

        # Update today's records with the latest, and store diagnosis keys
        self._update_contact_list(self.sim.attendees)

    def _update_contact_list(self, attendees):
        """Keep a record of the agents with the app that colocate with any agents with the app."""

        agents_with_app_loc_cache = {}
        for agent in self.agents_with_app:
            location = agent.current_location
            if len(attendees[location]) <= 1 or location.typ in self.location_type_blacklist:
                continue
            # Keep track of locations we've seen before
            if location not in agents_with_app_loc_cache:
                agents_with_app_loc_cache[location] =\
                [a for a in attendees[location] if a in self.agents_with_app]
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
            transmission_risk = [5, 6, 8, 8, 8, 5, 3, 1, 1, 1, 1, 1, 1, 1][days_since_contact]
            # transmission_risk = config['contact_tracing_app']['trans_risk_level_base_case'][days_since_contact]
            for other_agent in contacted:
                risk = self.duration_wgt * self.attenuation_wgt * self.days_since_last_expsr_wgt \
                       * transmission_risk
                # Keep track of global maximum risk
                if risk > max_risk:
                    max_risk = risk
                # If over the threshold, note that this agent is in the 'at risk' list
                if risk > self.trans_risk_threshold:
                    # print(f"[{i}] --> {risk} ({other_agent})")
                    time_at_risk += daily_exposure[other_agent]
        return time_at_risk * max_risk / self.av_risk_mins