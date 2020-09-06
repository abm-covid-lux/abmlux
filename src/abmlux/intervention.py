"""Represents interventions to the system."""

import math
import logging
from tqdm import tqdm
from collections import deque, defaultdict

from abmlux.sim_time import DeferredEventPool
import abmlux.random_tools as random_tools

log = logging.getLogger("intervention")


class Intervention:
    """Represents an intervention within the system.

    Interventions are notified of simulation state on every tick, allowing them to
    build internal state and return a list of activity changes in order to affect the simulation"""

    def __init__(self, prng, config, clock):

        self.prng   = prng
        self.config = config
        self.clock  = clock

    def initialise_agents(self, network):
        """Initialise internal state for this intervention, potentially
        modifying the network if necessary.  Run prior to simulation start."""

        log.warning("STUB: initialise_agents in intervention.py")

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):
        """Return a list of (agent, activity) tuples representing changes in activity this
        intervention applies"""

        log.warning("STUB: get_activity_transitions in intervention.py")

class Laboratory(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        # The sets of incubating and contagious health states:
        self.incubating_states     = set(config['incubating_states'])
        self.contagious_states     = set(config['contagious_states'])
        # The set of health states in which agents will test positive with positive probability:
        self.infected_states       = self.incubating_states.union(self.contagious_states)
        # The probabilities of false positives and negatives:
        self.prob_false_positive   = config['testing']['prob_false_positive']
        self.prob_false_negative   = config['testing']['prob_false_negative']

    def initialise_agents(self, network):

        schedule['testing']          = {t: set() for t in self.clock}                               # DON'T HAVE ACCESS TO SIM reset clock?!
        information['test results']  = {a: None for a in network.agents}
        information['awaiting test'] = {a: False for a in network.agents}

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):

        stuff_to_do = self.pending_events

        for stuff in stuff_to_do:
            stuff.do()




        # Each agent previously selected for testing during the current tick is tested:
        for agent in schedule['testing'][t]:
            if agent.health in self.infected_states:
                if random_tools.boolean(self.prob_false_negative):
                    information['test results'][agent] = False
                else:
                    information['test results'][agent] = True
                    information['quarantine'][agent] = True
                    information['stop quarantine'][agent] = t + 2#weeks                              # ...
            else:
                if random_tools.boolean(self.prob_false_positive):
                    information['test results'][agent] = True
                    information['quarantine'][agent] = True
                    information['stop quarantine'][agent] = t + 2#weeks                              # ...
                else:
                    information['test results'][agent] = False
                information['awaiting test'][agent] = False

class LargeScaleTesting(Intervention):

    def __init__(self, prng, config, clock):
        super().__init__(prng, config, clock)

        # Parameters
        self.symptomatic_states  = set(config['symptomatic_states'])

        self.awaiting_test       = DeferredEventPool(clock)
        self.agents_awaiting_test = set()

        self.current_day = None

    def initialise_agents(self, network):
        pass

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):

        # # Volunteering to be tested due to onset of symptoms this tick (do on a daily cycle?)
        # new_agents_with_symptoms = [a for a in sim.agents if a.health in self.symptomatic_states]
                                    # and a not in self.agents_who_have_notified_app}]
        # for agent in new_agents_with_symptoms:
            # if information['awaiting test'][agent] = False:
                # if random_tools.boolean(self.prng, 0.9): # Probability they request a test
                    # delay_mins = 2880                    # Time between request and test
                    # delay_ticks = max(int(sim.clock.mins_to_ticks(delay_mins)), 1)
                    # schedule['testing'][t + delay_ticks].add(agent)
                    # information['awaiting test'][agent] = True

        # Invited for testing by random selection:
        day = self.clock.now().day
        if self.current_day is None:
            self.current_day = day

        if day != self.current_day:
            test_agents_random = random_tools.random_sample(self.prng, sim.agents, 10)            # How many to test per day. Numbers such as these need rescaling by population size!
            for agent in test_agents_random:
                if agent not in self.agents_awaiting_test:

                    # TODO: schedule people for testing in working hours only
                    self.awaiting_test.add(agent, lifespan=int(self.clock.days_to_ticks(2)))
                    self.agents_awaiting_test.add(agent)

        # Check over people waiting to be tested
        for agent in self.awaiting_test:
            self.agents_awaiting_test.remove(agent) # Update index

class ContactTracing(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        # Parameters
        self.max_per_day             = config['contact_tracing']['max_per_day']
        self.relevant_activities     = config['contact_tracing']['relevant_activities']
        self.location_type_blacklist = config['contact_tracing']['location_type_blacklist']
        self.regular_locations_dict  = {}
        self.current_day_subjects    = set()

    def initialise_agents(self, network):

        for agent in tdqm(sim.agents):
            regular_locations = set()
            for activity in self.relevant_activities:
                activity_int = sim.activity_manager.as_int(activity)                                # DON'T HAVE ACCESS TO SIM
                activity_locations = set(agent.locations_for_activity(activity_int))                # this no good: retired are assigned schools but don't attend etc.
                regular_locations.update(activity_locations)
            for location in regular_locations:
                if location.typ in self.location_type_blacklist:
                    regular_locations.remove(location)
            self.regular_locations_dict[agent] = regular_locations

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):

        day = sim.clock.now().day

        if self.current_day is None:
            self.current_day = day

        # The agents whose contacts will later be traced are those who test positive during the day
        agents_testing_positive = {a for a in schedule['testing'][t] if information['test results'][a]}
        self.current_day_subjects.update(agents_testing_positive)

        if day != self.current_day:

            # The extact list of agents consists of a sample of those who tested positive. The size
            # of the sample corresponds to the maximum number of contacts that can be manually
            # traced each day.
            number_to_sample = min(self.max_per_day, len(self.current_day_subjects))
            sample = random_tools.random_sample(self.prng, self.current_day_subjects, number_to_sample)

            # The set of regular locations among those agents in the sample
            sample_regular_locations = set()
            for agent in sample:
                sample_regular_locations.update(self.contacts_dict[agent])

            # Now determine which agents frequent the same regular locations as the agents in the
            # sample
            agents_to_quarantine_and_test = []
            for agent in sim.agents:
                if self.regular_locations_dict[agent] & sample_regular_locations:
                    agents_to_quarantine_and_test.add(agent)

            # Instruct these agents to quaratine and get tested
            for agent in agents_to_quarantine_and_test:
                if random_tools.boolean(self.prng, self.prob_do_recommendation):
                    if agent not in sample:
                        if not information['awaiting test'][agent]:
                            delay_days = random_tools.random_choice(self.prng, [4,5])
                            delay_ticks = int(sim.clock.days_to_ticks(delay_days))
                            schedule['testing'][t + delay_ticks].add(agent)
                            information['awaiting test'][agent] = True
                    information['quarantine'][agent] = True
                    information['stop quarantine'][agent] = t + 2#weeks                              # ...

            # Move day on and reset day state
            self.current_day           = day
            self.current_day_subjects  = set()

class ContactTracingApp(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        self.agents_with_app                = []

        # State kept on who has seen whom during the day
        self.current_day                 = None
        self.current_day_contacts        = {}
        self.current_day_notifications   = set()
        self.exposure_by_day      = deque([], config['contact_tracing_app']['tracing_time_window_days'])
        self.time_at_risk_threshold_mins = config['contact_tracing_app']['time_at_risk_threshold_mins']
        self.av_risk_mins                = config['contact_tracing_app']['av_risk_mins']
        self.trans_risk_threshold        = config['contact_tracing_app']['trans_risk_threshold']
        self.prob_do_recommendation      = config['contact_tracing_app']['prob_do_recommendation']
        self.duration_wgt                = config['contact_tracing_app']['duration_wgt']
        self.attenuation_wgt             = config['contact_tracing_app']['attenuation_wgt']
        self.days_since_last_expsr_wgt   = config['contact_tracing_app']['days_since_last_expsr_wgt']
        self.trans_risk_level_base_case  = config['contact_tracing_app']['trans_risk_level_base_case']
        # Blacklist "outdoor" locations and other 'group'/holding locations
        self.location_type_blacklist = self.config['contact_tracing_app']['location_blacklist']

    def initialise_agents(self, network):
        """Select a number of agents that will have the app installed."""

        num_app_installs = min(len(network.agents), math.ceil(len(network.agents) * \
                                 self.config['contact_tracing_app']['app_prevalence']))
        self.agents_with_app = random_tools.random_sample(self.prng, network.agents, num_app_installs)

        log.info("Selected %i agents with app", len(self.agents_with_app))

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):

        day = sim.clock.now().day

        # FIXME: This would ideally be done during initialisation, but at that point
        #        the simulation has not started the clock, so it's impossible to read
        #        the day out of it.  This FIXME is a call to move the initialisation code
        #        so that the dependency makes sense
        if self.current_day is None:
            self.current_day = day

        # Update today's records with the latest, and store diagnosis keys
        self._update_contact_list(sim.attendees)

        # Gather together everyone who is infected at this tick and add them to the list of anyone
        # with the app who has been infected during the current day.This list is later used by other
        # agent app users to figure out if they met any of the infected agents.
        agents_notifying = {a for a in schedule['testing'][t] if information['test results'][a]}
        self.current_day_notifications.update(agents_notifying)

        if day != self.current_day:
            self.exposure_by_day.append(self.current_day_contacts)
            # Apps download diagnosis keys and calculate whether to notify their users
            for agent in self.agents_with_app:
                risk = self._get_personal_risk(agent)
                if risk >= sim.clock.mins_to_ticks(self.time_at_risk_threshold_mins):
                    if random_tools.boolean(self.prng, self.prob_do_recommendation):
                        if not information['awaiting test'][agent]:
                            delay_days = random_tools.multinoulli(self.prng, [0.007, 0.0935, 0.355, 0.3105, 0.1675, 0.055, 0.0105, 0.001])
                            delay_ticks = max(int(sim.clock.days_to_ticks(delay_days)), 1)
                            schedule['testing'][t + delay_ticks].add(agent)
                            information['awaiting test'][agent] = True
                        information['quarantine'][agent] = True
                        information['stop quarantine'][agent] = t + 2#weeks                          # ...
            # Move day on and reset day state
            self.current_day                = day
            self.current_day_contacts       = {}
            self.current_day_notifications  = set()

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

class Quarantine(Intervention):

    def __init__(self, prng, config):
        super().__init__(prng, config)

        self.quarantine_duration    = config['quarantine']['duration_days']
        self.hospital_location_type = config['quarantine']['hospital_location_type']
        self.cemetery_location_type = config['quarantine']['cemetery_location_type']
        self.home_activity_type     = config['quarantine']['home_activity_type']

    def initialise_agents(self, network):

        information['stop quarantine'] = {a: None for a in network.agents} # Values will be ticks or dates
        information['quarantine']  = {a: False for a in network.agents}
        self.time_in_quarantine    = {a: 0 for a in network.agents}

    def get_agent_updates(self, t, sim, agent_updates, schedule, information):



        # End the quarantine of these agents
        for agent in sim.agents:
            if information['stop quarantine'][agent] == t:
                information['quarantine'][agent] = False

        # Check for any new quarantine victims
        home_activity = sim.activity_manager.as_int(self.home_activity_type)
        for agent in sim.agents:
            if information['quarantine'][agent]:
                agent_updates[agent]['location'] = agent.locations_for_activity(home_activity)[0]
                self.time_in_quarantine[agent]  += 1

        #t + sim.clock.days_to_ticks(self.quarantine_duration)

        # for agent in agent_updates.keys():
            # if information['quarantine'][agent]:
                # home_activity = sim.activity_manager.as_int(self.home_activity_type)
                # agent_updates[agent]['location'] = agent.locations_for_activity(home_activity)[0]
                # self.time_in_quarantine[agent]  += 1


        # Update quarantine list
        # self.time_in_quarantine = {a: qt for a, qt in self.time_in_quarantine.items() if t < qt}

        # print(f"-> {len(self.time_in_quarantine)} people in quarantine")

        # # All people in quarantine list should go home, unless they are
        # # in hospital or dead
        # for agent, deadline in self.time_in_quarantine.items():
            # if agent.current_location.typ == self.hospital_location_type:
                # continue
            # if agent.current_location.typ == self.cemetery_location_type:
                # continue

            # agent_updates[agent]['location'] = agent.locations_for_activity(sim.activity_manager.as_int(self.home_activity_type))[0]