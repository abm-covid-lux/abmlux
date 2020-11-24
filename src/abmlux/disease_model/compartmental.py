"""Disease models based on discrete compartments with transition probabilities"""

import logging
from tqdm import tqdm

from abmlux.disease_model import DiseaseModel

log = logging.getLogger("adv_seird_model")

class CompartmentalModel(DiseaseModel):
    """Represents a disease as a set of states with transition probabilities and a pre-determined,
    static set of potential routes through the states."""

    def __init__(self, config):

        super().__init__(config, config['health_states'])

        self.inf_probs                  = config['infection_probabilities_per_tick']
        self.num_initial_infections     = config['initial_infections']
        self.random_exposures           = config['random_exposures']
        self.contagious_states          = set(config['contagious_states'])
        self.symptomatic_states         = set(config['symptomatic_states'])
        self.asymptomatic_states        = set(config['asymptomatic_states'])
        self.incubating_states          = set(config['incubating_states'])
        self.asympt_factor              = config['asympt_factor']
        self.durations_by_profile       = config['durations_by_profile']
        self.health_state_change_time   = {}
        self.disease_profile_index_dict = {}
        self.disease_profile_dict       = {}
        self.disease_durations_dict     = {}
        self.agents_by_health_state     = {s: set() for s in self.states}

        self.ppm_strategy               = config['personal_protective_measures.ppm_strategy']
        self.ppm_force                  = config['personal_protective_measures.ppm_force']
        self.ppm_coeff                  = config['personal_protective_measures.ppm_coeff']
        self.ppm_force_updates_unparsed = config['personal_protective_measures.ppm_force_updates']
        self.ppm_force_updates          = {}

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

    def init_sim(self, sim):
        super().init_sim(sim)

        # FIXME
        self.sim   = sim
        self.world = sim.world

        self.bus.subscribe("notify.time.tick", self.get_health_transitions, self)
        self.bus.subscribe("notify.agent.health", self.update_health_indices, self)
        self.bus.subscribe("notify.time.midnight", self.random_midnight_exposures, self)

        # Initialise the state
        # Assign a disease profile to each agent. This determines which health states an agent
        # passes through and in which order.
        log.info("Assigning disease profiles and durations...")
        agents = self.world.agents
        total_contagious_time = 0
        total_incubation_time = 0
        for agent in tqdm(agents):
            age_rounded = min((agent.age//self.step_size)*self.step_size, self.max_age)
            profile = self.prng.random_choices(list(self.dict_by_age[age_rounded].keys()),
                                     self.dict_by_age[age_rounded].values(),1)[0]
            durations = self._durations_for_profile(profile, self.sim)
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
        average_contagious_time = total_contagious_time / (len(agents) * self.sim.clock.ticks_in_day)
        average_incubation_time = total_incubation_time / (len(agents) * self.sim.clock.ticks_in_day)
        log.info("Average contagious period (days): %s", average_contagious_time)
        log.info("Average incubation period (days): %s", average_incubation_time)

        # The disease profile index dictionary keeps track of the progress each agent has made
        # through their disease profile. We start by setting the index of all agents to 0.
        for agent in agents:
            self.health_state_change_time[agent] = 0
            self.disease_profile_index_dict[agent] = 0
            agent.health = self.disease_profile_dict[agent][0]
            self.agents_by_health_state[agent.health].add(agent)

        # Now infect a number of agents to begin the epidemic. This moves those agents to the next
        # state listed in their disease profile.
        log.info("Infecting %i agents...", self.num_initial_infections)
        for agent in self.prng.random_sample(agents, self.num_initial_infections):
            self.agents_by_health_state[agent.health].remove(agent)
            self.disease_profile_index_dict[agent] = 1
            agent.health = self.disease_profile_dict[agent][1]
            self.agents_by_health_state[agent.health].add(agent)

        # Parse ppm updates schedule from config, creating calendar of updates
        for param_time, param in self.ppm_force_updates_unparsed.items():
            if isinstance(param_time, str):
                ticks = int(self.sim.clock.datetime_to_ticks(param_time))
            else:
                ticks = int(param_time)
            self.ppm_force_updates[ticks] = float(param)

    def random_midnight_exposures(self, clock, t):
        """At midnight, parameters are updated and some suceptible agents are randomly exposed"""

        if t in self.ppm_force_updates.keys():
            self.ppm_force = self.ppm_force_updates[t]

        if self.random_exposures == 0:
            return

        suceptible_agents    = self.agents_by_health_state['SUSCEPTIBLE']
        expose_agents_random = self.prng.random_sample(suceptible_agents, min(self.random_exposures,len(suceptible_agents)))
        for agent in expose_agents_random:
            self.bus.publish("request.agent.health", agent, self.disease_profile_dict[agent][self.disease_profile_index_dict[agent] + 1])

    def get_health_transitions(self, clock, t):
        """Updates the health state of agents"""

        # Compute for each location the probability of catching the virus during this tick
        # TODO: count this as states change, like sim.agent_counts_by_health
        contagious_count_dict = {l: (len([a for a in self.sim.attendees[l] if a.health in self.symptomatic_states]),
                                     len([a for a in self.sim.attendees[l] if a.health in self.asymptomatic_states])) for l in self.sim.locations}

        # If p is the baseline transmission probability, q is the probability of an individual
        # wearing a mask and r is the proportion of virus particles passing through the mask,
        # then the true transmission probability between two individuals, each of which may or
        # may not be wearing a mask, is:
        #
        # p_true = p(r^2q^2 + 2rq(1-q) + (1-q)^2) = p(1-(1-r)q)^2
        #
        # Moreover q = (probabability an agent wears a mask, given that the agent follows the
        #               rules) * (probability that the agent follows the rules)
        ppm_modifier = {loc_type : ((1 - (1-self.ppm_coeff)*self.ppm_force*self.ppm_strategy[loc_type])**2) for loc_type in self.ppm_strategy}

        # Calculation of infection probabilities by location
        infection_probability_by_location = {l: 1 - (((1-self.inf_probs[l.typ]*ppm_modifier[l.typ])**c[0])*((1-self.asympt_factor*self.inf_probs[l.typ]*ppm_modifier[l.typ])**c[1]))
                                             for l, c in contagious_count_dict.items() if c[0]+c[1] > 0}

        # Determine which suceptible agents are infected during this tick
        for location, p_infection in infection_probability_by_location.items():
            susceptible_agents = [agent for agent in self.sim.attendees[location] if agent.health == 'SUSCEPTIBLE']
            for agent in susceptible_agents:
                if self.prng.boolean(p_infection):
                    self.bus.publish("request.agent.health", agent, self.disease_profile_dict[agent][self.disease_profile_index_dict[agent] + 1])

        # Determine which other agents need moving to their next health state
        for agent in self.world.agents:
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

        # This shouldn't really happen, but if it does then we're not interested
        if old_health == agent.health:
            return

        self.disease_profile_index_dict[agent] += 1
        self.health_state_change_time[agent] = self.sim.clock.t

        # Who is what state
        self.agents_by_health_state[old_health].remove(agent)
        self.agents_by_health_state[agent.health].add(agent)

    def _durations_for_profile(self, profile, sim):
        """Assigns durations for each phase in a given profile"""

        durations = []

        for i in range(len(self.durations_by_profile[profile])):
            dist = self.durations_by_profile[profile][i]
            if dist == 'None':
                durations.append(None)
            if isinstance(dist,list):
                if dist[0] == 'G':
                    dur_ticks = self.prng.gammavariate(float(dist[1][0]), float(dist[1][1]))
                if dist[0] == 'U':
                    dur_ticks = self.prng.random_choice(list(range(int(dist[1][0]), int(dist[1][1]))))
                if dist[0] == 'C':
                    dur_ticks = float(dist[1][0])
                durations.append(sim.clock.days_to_ticks(dur_ticks))

        return durations