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

    def __init__(self, prng, config, clock, bus):

        self.prng   = prng
        self.config = config
        self.clock  = clock
        self.bus    = bus

        #bus.register("message type", callback)

    def initialise_agents(self, network):
        """Initialise internal state for this intervention, potentially
        modifying the network if necessary.  Run prior to simulation start."""
        pass
        #log.warning("STUB: initialise_agents in intervention.py")

    def get_agent_updates(self, t, sim, agent_updates):
        """Return a list of (agent, activity) tuples representing changes in activity this
        intervention applies"""

        log.warning("STUB: get_activity_transitions in intervention.py")

class Laboratory(Intervention):

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        self.test_duration = int(clock.days_to_ticks(3))

        # The sets of incubating and contagious health states:
        self.incubating_states     = set(config['incubating_states'])
        self.contagious_states     = set(config['contagious_states'])
        # The set of health states in which agents will test positive with positive probability:
        self.infected_states       = self.incubating_states.union(self.contagious_states)
        # The probabilities of false positives and negatives:
        self.prob_false_positive   = config['testing']['prob_false_positive']
        self.prob_false_negative   = config['testing']['prob_false_negative']

        self.test_result_events    = DeferredEventPool(clock)
        self.agents_awaiting_results = set()

        self.bus.subscribe("testing.booked", self.handle_testing_booked)

    def handle_testing_booked(self, agent):
        if agent in self.agents_awaiting_results:
            return

        test_result = False
        if agent.health in self.infected_states:
            if random_tools.boolean(self.prng, 1 - self.prob_false_negative):
                test_result = True
        else:
            if random_tools.boolean(self.prng, self.prob_false_positive):
                test_result = True

        self.agents_awaiting_results.add(agent) # Update index
        self.test_result_events.add((agent, test_result), lifespan=self.test_duration)

    def get_agent_updates(self, t, sim, agent_updates):

        # Notify people
        for agent, result in self.test_result_events:
            self.bus.publish("testing.result", agent, result)


class BookTest(Intervention):
    """Consume a 'selected for testing' signal and wait a bit whilst getting around to it"""

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        # Time between selection for test and the time at which the test will take place
        self.time_to_arrange_test = int(clock.days_to_ticks(2))

        self.test_events       = DeferredEventPool(clock)
        self.agents_awaiting_test = set()

        self.bus.subscribe("testing.selected", self.handle_selected_for_testing)

    def handle_selected_for_testing(self, agent):
        """Someone has been selected for testing.  Insert a delay
        whilst they figure out where to go"""

        if agent not in self.agents_awaiting_test:
            self.test_events.add(agent, lifespan=self.time_to_arrange_test)
            self.agents_awaiting_test.add(agent)

    def get_agent_updates(self, t, sim, agent_updates):

        # Reading events to test agents this tick
        for agent in self.test_events:
            self.agents_awaiting_test.remove(agent) # Update index
            self.bus.publish("testing.booked", agent)


class LargeScaleTesting(Intervention):
    """Select n people per day for testing at random"""

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        # Parameters
        # self.symptomatic_states  = set(config['symptomatic_states'])

        self.agents_tested_per_day = 10
        self.current_day = None

    def get_agent_updates(self, t, sim, agent_updates):

        # Invited for testing by random selection:
        day = self.clock.now().day
        if self.current_day is None:
            self.current_day = day

        if day != self.current_day:
            test_agents_random = random_tools.random_sample(self.prng, sim.agents,
                                                            self.agents_tested_per_day)            # How many to test per day. Numbers such as these need rescaling by population size!
            for agent in test_agents_random:
                self.bus.publish('testing.selected', agent)


class ContactTracing(Intervention):

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        # Parameters
        self.max_per_day             = config['contact_tracing']['max_per_day']
        self.relevant_activities     = config['contact_tracing']['relevant_activities']
        self.location_type_blacklist = config['contact_tracing']['location_type_blacklist']
        self.regular_locations_dict  = {}
        self.current_day_subjects    = set()

    def initialise_agents(self, network):

        for agent in tdqm(network.agents):
            regular_locations = set()
            for activity in self.relevant_activities:
                activity_int = XXX.activity_manager.as_int(activity)                                # DON'T HAVE ACCESS TO SIM
                activity_locations = set(agent.locations_for_activity(activity_int))                # this no good: retired are assigned schools but don't attend etc.
                regular_locations.update(activity_locations)
            for location in regular_locations:
                if location.typ in self.location_type_blacklist:
                    regular_locations.remove(location)
            self.regular_locations_dict[agent] = regular_locations

    def get_agent_updates(self, t, sim, agent_updates):

        day = self.clock.now().day
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

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        self.agents_with_app                = []

        # State kept on who has seen whom during the day
        self.current_day                 = None
        self.current_day_contacts        = {}
        self.current_day_notifications   = set()
        self.exposure_by_day             = deque([], config['contact_tracing_app']['tracing_time_window_days'])
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

        self.bus.subscribe("testing.result", self.handle_test_result)

    def handle_test_result(self, agent, result):
        print(f"CTA: {agent} tested {result}")
        if result == True and agent in self.agents_with_app:
            self.current_day_notifications.add(agent)

    def initialise_agents(self, network):
        """Select a number of agents that will have the app installed."""

        num_app_installs = min(len(network.agents), math.ceil(len(network.agents) * \
                                 self.config['contact_tracing_app']['app_prevalence']))
        self.agents_with_app = random_tools.random_sample(self.prng, network.agents, num_app_installs)

        log.info("Selected %i agents with app", len(self.agents_with_app))

    def get_agent_updates(self, t, sim, agent_updates):

        # FIXME: This would ideally be done during initialisation, but at that point
        #        the simulation has not started the clock, so it's impossible to read
        #        the day out of it.  This FIXME is a call to move the initialisation code
        #        so that the dependency makes sense
        day = self.clock.now().day
        if self.current_day is None:
            self.current_day = day

        # Update today's records with the latest, and store diagnosis keys
        self._update_contact_list(sim.attendees)

        if day != self.current_day:
            self.exposure_by_day.append(self.current_day_contacts)
            # Apps download diagnosis keys and calculate whether to notify their users
            for agent in self.agents_with_app:
                risk = self._get_personal_risk(agent)
                if risk >= sim.clock.mins_to_ticks(self.time_at_risk_threshold_mins):
                    if random_tools.boolean(self.prng, self.prob_do_recommendation):

                        self.bus.publish("testing.selected", agent)
                        self.bus.publish("quarantine", agent)

                        #if not information['awaiting test'][agent]:
                        #    delay_days = random_tools.multinoulli(self.prng, [0.007, 0.0935, 0.355, 0.3105, 0.1675, 0.055, 0.0105, 0.001])
                        #    delay_ticks = max(int(sim.clock.days_to_ticks(delay_days)), 1)
                        #    schedule['testing'][t + delay_ticks].add(agent)

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

    def __init__(self, prng, config, clock, bus):
        super().__init__(prng, config, clock, bus)

        self.quarantine_duration    = int(self.clock.days_to_ticks(config['quarantine']['duration_days']))
        self.hospital_location_type = config['quarantine']['hospital_location_type']
        self.cemetery_location_type = config['quarantine']['cemetery_location_type']
        self.home_activity_type     = config['quarantine']['home_activity_type']

        self.end_quarantine_events = DeferredEventPool(self.clock)
        self.agents_in_quarantine  = set()

        self.bus.subscribe("testing.result", self.handle_test_result)
        self.bus.subscribe("quarantine", self.handle_quarantine_request)

    def handle_test_result(self, agent, result):

        if agent in self.agents_in_quarantine:
            return

        if result == True:
            self.agents_in_quarantine.add(agent)
            self.end_quarantine_events.add(agent, lifespan=self.quarantine_duration)

    def handle_quarantine_request(self, agent):

        if agent in self.agents_in_quarantine:
            return

        self.agents_in_quarantine.add(agent)
        self.end_quarantine_events.add(agent, lifespan=self.quarantine_duration)

    def get_agent_updates(self, t, sim, agent_updates):

        # Update index for agents that are ending quarantine now
        for agent in self.end_quarantine_events:
            self.agents_in_quarantine.remove(agent)

        # If an agent is in quarantine, override any location changes
        home_activity = sim.activity_manager.as_int(self.home_activity_type)
        for agent, payload in agent_updates.items():
            if 'location' in payload and agent in self.agents_in_quarantine:
                print(f"_ Overriding {payload['location']} to home")
                agent_updates[agent]['location'] = \
                    agent.locations_for_activity(sim.activity_manager.as_int(self.home_activity_type))[0]