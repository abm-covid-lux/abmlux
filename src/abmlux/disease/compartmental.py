"""Disease models based on discrete compartments with transition probabilities"""

import logging
from tqdm import tqdm

from abmlux.disease import DiseaseModel
from abmlux.random_tools import random_choice, random_choices, random_sample, boolean, gammavariate

log = logging.getLogger("adv_seird_model")

class CompartmentalModel(DiseaseModel):
    """Represents a disease as a set of states with transition probabilities and a pre-determined,
    static set of potential routes through the states."""

    def __init__(self, prng, config, bus, state):

        states = config['health_states']
        super().__init__(states)

        self.prng                       = prng
        self.infection_probabilities    = config['infection_probabilities_per_tick']
        self.ppm_coeff                  = config['personal_protective_measures']['ppm_coeff']
        self.num_initial_infections     = config['initial_infections']
        self.contagious_states          = set(config['contagious_states'])
        self.incubating_states          = set(config['incubating_states'])
        self.durations_by_profile       = config['durations_by_profile']
        self.health_state_change_time   = {}
        self.disease_profile_index_dict = {}
        self.disease_profile_dict       = {}
        self.disease_durations_dict     = {}
        self.bus                        = bus
        self.state                      = state
        self.network                    = state.network

        profiles  = config['disease_profile_distribution_by_age']
        labels    = config['disease_profile_list']
        step_size = config['disease_profile_distribution_by_age_step_size']

        self.max_age = max(age for age in profiles)
        self.step_size = step_size
        self.dict_by_age = {}
        # Pylint doesn't like the comprehension below but I _think_ it's fine.
        #pylint: disable=unnecessary-comprehension
        for age in profiles:
            self.dict_by_age[age] = {k:v for k,v in zip(labels, profiles[age])}

        self.bus.subscribe("notify.time.start_simulation", self.initialise_agents, self)
        self.bus.subscribe("notify.time.tick", self.get_health_transitions, self)
        self.bus.subscribe("notify.agent.health", self.update_health_indices, self)

    def initialise_agents(self, sim):
        """Assign a disease profile and durations to each agent and infect some people at random
        to begin the epidemic"""

        self.sim = sim
        network = sim.network

        # Assign a disease profile to each agent. This determines which health states an agent
        # passes through and in which order.
        log.info("Assigning disease profiles and durations...")
        agents = network.agents
        total_contagious_time = 0
        total_incubation_time = 0
        for agent in tqdm(agents):
            age_rounded = min((agent.age//self.step_size)*self.step_size, self.max_age)
            profile = random_choices(self.prng, list(self.dict_by_age[age_rounded].keys()),
                                     self.dict_by_age[age_rounded].values(),1)[0]
            durations = self._durations_for_profile(profile)
            profile = [self.state_for_letter(l) for l in profile]
            assert len(durations) == len(profile)
            self.disease_profile_dict[agent] = profile
            self.disease_durations_dict[agent] = durations
            # For information purposes, we calculate the mean incubation and contagious periods
            for i in range(len(profile)):
                if profile[i] in self.incubating_states:
                    total_incubation_time += durations[i]
                if profile[i] in self.contagious_states:
                    total_contagious_time += durations[i]
        average_contagious_time = total_contagious_time / len(agents)
        average_incubation_time = total_incubation_time / len(agents)
        log.info("Average contagious period (days): %s", average_contagious_time)
        log.info("Average incubation period (days): %s", average_incubation_time)

        # The disease profile index dictionary keeps track of the progress each agent has made
        # through their disease profile. We start by setting the index of all agents to 0.
        for agent in agents:
            self.disease_profile_index_dict[agent] = 0
            agent.health = self.disease_profile_dict[agent][0]

        # Now infect a number of agents to begin the epidemic. This moves those agents to the next
        # state listed in their disease profile.
        log.info("Infecting %i agents...", self.num_initial_infections)
        for agent in random_sample(self.prng, agents, self.num_initial_infections):
            self.disease_profile_index_dict[agent] = 1
            agent.health = self.disease_profile_dict[agent][1]

        # Initialize the health state change time dictionary
        log.info("Updating health state index...")
        for agent in agents:
            self.health_state_change_time[agent] = 0

    def get_health_transitions(self, clock, t):
        """Updates the health state of agents"""

        # Start by using the simulation clock to convert durations from days to ticks
        if t == 0:
            for agent in self.network.agents:
                for index in range(len(self.disease_durations_dict[agent])):
                    duration_days = self.disease_durations_dict[agent][index]
                    if duration_days is not None:
                        duration_ticks = self.state.clock.days_to_ticks(duration_days)
                        self.disease_durations_dict[agent][index] = duration_ticks

        # Compute for each location the probability of catching the virus during this tick
        # TODO: count this as states change, like sim.agent_counts_by_health
        contagious_count_dict = {l: len([a for a in self.sim.attendees[l]
                                         if a.health in self.contagious_states])
                                 for l in self.sim.locations}
        infection_probability_by_location = {l: 1 - (1-self.ppm_coeff*self.infection_probabilities[l.typ])**c
                                             for l, c in contagious_count_dict.items() if c > 0}

        # Determine which suceptible agents are infected during this tick
        for location, p_infection in infection_probability_by_location.items():
            susceptible_agents = [agent for agent in self.sim.attendees[location]
                                  if self.disease_profile_index_dict[agent] == 0]
            for agent in susceptible_agents:
                if boolean(self.prng, p_infection):
                    self.bus.publish("request.agent.health", agent, self.disease_profile_dict[agent][1])

        # Determine which other agents need moving to their next health state
        for agent in self.network.agents:
            duration_ticks = self.disease_durations_dict[agent]\
                             [self.disease_profile_index_dict[agent]]

            # duration_ticks is None if agent.health is susceptible, recovered or dead
            # pylint: disable=line-too-long
            if duration_ticks is not None:
                time_since_state_change = t - self.health_state_change_time[agent]
                if time_since_state_change > duration_ticks:
                    self.bus.publish("request.agent.health", agent, \
                        self.disease_profile_dict[agent][self.disease_profile_index_dict[agent] + 1])
            # pylint: enable=line-too-long


    def update_health_indices(self, agent, old_health):
        """Update internal counts."""

        if old_health == agent.health:
            return

        self.disease_profile_index_dict[agent] += 1
        self.health_state_change_time[agent] = self.sim.clock.t

    def _durations_for_profile(self, profile):
        """Assigns durations for each phase in a given profile"""

        durations = []

        for i in range(len(self.durations_by_profile[profile])):
            dist = self.durations_by_profile[profile][i]
            if dist == 'None':
                durations.append(None)
            if isinstance(dist,list):
                if dist[0] == 'G':
                    durations.append(gammavariate(self.prng, float(dist[1][0]), float(dist[1][1])))
                if dist[0] == 'U':
                    durations.append(random_choice(self.prng,
                                                   list(range(int(dist[1][0]), int(dist[1][1])))))
                if dist[0] == 'C':
                    durations.append(float(dist[1][0]))

        return durations
