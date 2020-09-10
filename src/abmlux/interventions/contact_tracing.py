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

    def __init__(self, prng, config, clock, bus, state):
        super().__init__(prng, config, clock, bus)

        self.max_per_day              = config['contact_tracing_manual']['max_per_day']
        self.tracing_time_window_days = config['contact_tracing_manual']['tracing_time_window_days']
        self.relevant_activities      = config['contact_tracing_manual']['relevant_activities']
        self.prob_do_recommendation   = config['contact_tracing_manual']['prob_do_recommendation']
        self.location_type_blacklist  = config['contact_tracing_manual']['location_type_blacklist']

        self.regular_locations_dict  = {}
        self.current_day_subjects    = set()
        self.relevant_activities_int = {state.activity_manager.as_int(x) for x in self.relevant_activities}
        self.activity_manager        = state.activity_manager

        self.bus.subscribe("sim.time.start_simulation", self.start_sim)
        self.bus.subscribe("sim.agent.location", self.handle_location_change)

    def start_sim(self, sim):
        self.sim = sim

    def handle_location_change(self, agent, old_location, new_location):

        # This agent has to be doing the relevant activity
        if agent.current_activity not in self.relevant_activities:
            return

        agents_of_interest = [a for a in self.sim.attendees[new_location]\
                              if a.current_activity in self.relevant_activities]
        if len(agents_of_interest) == 1:    # The person counts as an attendee him/her self
            return

        #print(f"Meeting {len(agents_of_interest)} new people!  How exciting.")

        
        # agent.current_location 


# class ContactTracingManual(Intervention):

#     def __init__(self, prng, config, clock, bus, state):
#         super().__init__(prng, config, clock, bus)

#         # Parameters
#         self.max_per_day             = config['contact_tracing']['max_per_day']
#         self.relevant_activities     = config['contact_tracing']['relevant_activities']
#         self.location_type_blacklist = config['contact_tracing']['location_type_blacklist']
#         self.regular_locations_dict  = {}
#         self.current_day_subjects    = set()

#     def initialise_agents(self, network):

#         for agent in tdqm(network.agents):
#             regular_locations = set()
#             for activity in self.relevant_activities:
#                 activity_int = XXX.activity_manager.as_int(activity)                                # DON'T HAVE ACCESS TO SIM
#                 activity_locations = set(agent.locations_for_activity(activity_int))                # this no good: retired are assigned schools but don't attend etc.
#                 regular_locations.update(activity_locations)
#             for location in regular_locations:
#                 if location.typ in self.location_type_blacklist:
#                     regular_locations.remove(location)
#             self.regular_locations_dict[agent] = regular_locations

#     def get_agent_updates(self, t, sim):

#         day = self.clock.now().day
#         if self.current_day is None:
#             self.current_day = day

#         # The agents whose contacts will later be traced are those who test positive during the day
#         agents_testing_positive = {a for a in schedule['testing'][t] if information['test results'][a]}
#         self.current_day_subjects.update(agents_testing_positive)

#         if day != self.current_day:

#             # The extact list of agents consists of a sample of those who tested positive. The size
#             # of the sample corresponds to the maximum number of contacts that can be manually
#             # traced each day.
#             number_to_sample = min(self.max_per_day, len(self.current_day_subjects))
#             sample = random_tools.random_sample(self.prng, self.current_day_subjects, number_to_sample)

#             # The set of regular locations among those agents in the sample
#             sample_regular_locations = set()
#             for agent in sample:
#                 sample_regular_locations.update(self.contacts_dict[agent])

#             # Now determine which agents frequent the same regular locations as the agents in the
#             # sample
#             agents_to_quarantine_and_test = []
#             for agent in sim.agents:
#                 if self.regular_locations_dict[agent] & sample_regular_locations:    # this no good, due to age ranges not matching etc...
#                     agents_to_quarantine_and_test.add(agent)

#             # Instruct these agents to quaratine and get tested
#             for agent in agents_to_quarantine_and_test:
#                 if random_tools.boolean(self.prng, self.prob_do_recommendation):
#                     if agent not in sample:
#                         if not information['awaiting test'][agent]:
#                             delay_days = random_tools.random_choice(self.prng, [4,5])
#                             delay_ticks = int(sim.clock.days_to_ticks(delay_days))
#                             schedule['testing'][t + delay_ticks].add(agent)
#                             information['awaiting test'][agent] = True
#                     information['quarantine'][agent] = True
#                     information['stop quarantine'][agent] = t + 2#weeks                              # ...

#             # Move day on and reset day state
#             self.current_day           = day
#             self.current_day_subjects  = set()


class ContactTracingApp(Intervention):

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