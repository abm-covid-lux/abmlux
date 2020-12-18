"""Disease models based on discrete compartments with transition probabilities"""

import logging
import numpy as np
from tqdm import tqdm
from collections import defaultdict

from abmlux.disease_model import DiseaseModel

log = logging.getLogger("adv_seird_model")

class CompartmentalModel(DiseaseModel):
    """Represents a disease as a set of states with transmission probabilities
    and a pre-determined satic set of potential routes through the states"""

    def __init__(self, config):
        super().__init__(config, config['health_states'])

        self.inf_probs                  = config['infection_probabilities_per_tick']
        self.num_initial_infections     = config['initial_infections']
        self.random_exposures           = config['random_exposures']

        self.susceptible_states         = set(config['susceptible_states'])
        self.incubating_states          = set(config['incubating_states'])
        self.asymptomatic_states        = set(config['asymptomatic_states'])
        self.symptomatic_states         = set(config['symptomatic_states'])

        self.asympt_factor              = config['asympt_factor']
        self.durations_by_profile       = config['durations_by_profile']

        self.new_symptomatics           = []
        self.new_asymptomatics          = []
        self.health_state_change_time   = {}
        self.disease_profile_dict       = {}
        self.disease_profile_index_dict = {}
        self.disease_durations_dict     = {}

        self.ppm_strategy               = config['personal_protective_measures.ppm_strategy']
        self.ppm_force                  = config['personal_protective_measures.ppm_force']
        self.ppm_coeff                  = config['personal_protective_measures.ppm_coeff']
        self.ppm_force_updates_unparsed = config['personal_protective_measures.ppm_force_updates']
        self.ppm_force_updates          = {}

        self.profiles                   = config['disease_profile_distribution_by_age']
        self.labels                     = config['disease_profile_list']
        self.step_size                  = config['disease_profile_distribution_by_age_step_size']

    def init_sim(self, sim):
        super().init_sim(sim)

        self.sim   = sim
        self.world = sim.world
        self.activity_manager = sim.activity_manager

        self.bus.subscribe("notify.time.tick", self.get_health_transitions, self)
        self.bus.subscribe("notify.agent.health", self.update_health_indices, self)
        self.bus.subscribe("notify.time.midnight", self.midnight_updates, self)

        agents = self.world.agents

        # Assign a disease profile to each agent. This determines which health states an agent
        # passes through, in which order and how long each agent will spend in each state
        log.info("Assigning disease profiles and durations...")
        labelled_profiles_by_age = {}
        for age in self.profiles:
            labelled_profiles_by_age[age] = {k:v for k,v in zip(self.labels, self.profiles[age])}
        max_age = max(age for age in self.profiles)

        # Used to calculate average incubation and contagious periods
        total_contagious_time = 0
        total_incubation_time = 0

        for agent in tqdm(agents):
            # Disease progression is determined in terms of age
            age_rounded = min((agent.age//self.step_size)*self.step_size, max_age)

            # The sequence of health states that an agent will follow through the disease model
            profile = self.prng.multinoulli_dict(labelled_profiles_by_age[age_rounded])

            # The durations of time the agent will spend in state in that sequence
            durations = self._durations_for_profile(profile, self.sim)

            # Store the profile and durations for this agent
            profile = [self.state_for_letter(l) for l in profile]
            assert len(durations) == len(profile)
            self.disease_profile_dict[agent] = profile
            self.disease_durations_dict[agent] = durations

            # Used to calculate average incubation and contagious periods
            for i in range(len(profile)):
                if profile[i] in self.incubating_states:
                    total_incubation_time += durations[i]
                if profile[i] in self.asymptomatic_states.union(self.symptomatic_states):
                    total_contagious_time += durations[i]

        average_contagious_time = total_contagious_time / (len(agents)*self.sim.clock.ticks_in_day)
        average_incubation_time = total_incubation_time / (len(agents)*self.sim.clock.ticks_in_day)
        log.info("Average contagious period (days): %s", average_contagious_time)
        log.info("Average incubation period (days): %s", average_incubation_time)

        # The disease profile index dictionary keeps track of the progress each agent has made
        # through their disease profile. We start by setting the index of all agents to 0.
        for agent in agents:
            self.health_state_change_time[agent] = 0
            self.disease_profile_index_dict[agent] = 0
            agent.health = self.disease_profile_dict[agent][0]

        # Now infect a number of agents to begin the epidemic. This moves those agents to the next
        # state listed in their disease profile.
        log.info("Infecting %i agents...", self.num_initial_infections)
        for agent in self.prng.random_sample(agents, self.num_initial_infections):
            self.disease_profile_index_dict[agent] = 1
            agent.health = self.disease_profile_dict[agent][1]

        # Parse ppm updates schedule from config, creating calendar of updates
        for param_time, param in self.ppm_force_updates_unparsed.items():
            if isinstance(param_time, str):
                ticks = int(self.sim.clock.datetime_to_ticks(param_time))
            else:
                ticks = int(param_time)
            self.ppm_force_updates[ticks] = float(param)

    def midnight_updates(self, clock, t):
        """At midnight, parameters are updated and some suceptible agents are randomly exposed"""

        # Update ppm force parameter, if necessary
        if t in self.ppm_force_updates.keys():
            self.ppm_force = self.ppm_force_updates[t]

        # Randomly expose a number of sucesptibles
        if self.random_exposures == 0:
            return
        suceptible_agents = [a for a in self.world.agents if a.health in self.susceptible_states]
        num_to_expose = min(self.random_exposures,len(suceptible_agents))
        for agent in self.prng.random_sample(suceptible_agents, num_to_expose):
            self.bus.publish("request.agent.health", agent,\
            self.disease_profile_dict[agent][self.disease_profile_index_dict[agent] + 1])

    def get_health_transitions(self, clock, t):
        """Updates the health state of agents"""

        # Recalculate the ppm_modifier, in case the ppm_force has been updated
        ppm_modifier = {loc_type : ((1 - (1-self.ppm_coeff)*self.ppm_force*self.ppm_strategy[loc_type])**2) for loc_type in self.ppm_strategy}

        # Determine which suceptible agents are infected during this tick
        for location in self.sim.locations:
            # Extract the relavent sets of agents from the attendees dict
            symptomatics_sets  = [self.sim.attendees_by_health[location][h] for h in self.symptomatic_states]
            asymptomatics_sets = [self.sim.attendees_by_health[location][h] for h in self.asymptomatic_states]
            # Take unions to get sets of symptomatic and asymptomatic agents for this location
            symptomatics  = set().union(*symptomatics_sets)
            asymptomatics = set().union(*asymptomatics_sets)
            # Check if there are any symptomatics or asymptomatics in this location
            if len(symptomatics) + len(asymptomatics) > 0:
                # If so then calculate the probabilities to be using in the transmission calculation
                p_sym  = self.inf_probs[location.typ]*ppm_modifier[location.typ]
                p_asym = self.asympt_factor*self.inf_probs[location.typ]*ppm_modifier[location.typ]
                # Determine which agents are susceptible
                susceptible_sets = [self.sim.attendees_by_health[location][h] for h in self.susceptible_states]
                susceptibles = set().union(*susceptible_sets)
                # Loop through susceptibles and decide if each one gets infected or not
                for agent in susceptibles:
                    # Check if the agent has been vaccinated
                    if not agent.vaccinated:
                        # Decide if this agent will be infected
                        sym_successes = np.random.binomial(len(symptomatics), p_sym) # TODO: optimize binomial sampling, this is slow in certain cases (see: Poisson_binomial_distribution perhapss)...
                        asym_successes = np.random.binomial(len(asymptomatics), p_asym)
                        # If at least one successful transmission then publish the health state change
                        if asym_successes + sym_successes > 0:
                            self.bus.publish("request.agent.health", agent, self.disease_profile_dict[agent][self.disease_profile_index_dict[agent] + 1])
                            # Decide who caused the infection
                            if self.prng.random_randrange(sym_successes + asym_successes) < sym_successes:
                                # The case in which it was a symptomatic
                                agent_responsible = self.prng.random_choice(list(symptomatics))
                            else:
                                # The case in which it was an asymptomatic
                                agent_responsible = self.prng.random_choice(list(asymptomatics))
                            # Send this information to the telemetry server
                            self.telemetry_server.send("new_infection", clock, location.typ,
                                                    location.coord, agent.uuid, agent.age,
                                                    self.activity_manager.as_str(agent.current_activity),
                                                    agent_responsible.uuid, agent_responsible.age,
                                                    self.activity_manager.as_str(agent_responsible.current_activity))

        # Determine which other agents need moving to their next health state, where duration_ticks
        # is None if agent.health is susceptible, recovered or dead
        for agent in self.world.agents:
            duration_ticks = self.disease_durations_dict[agent]\
                             [self.disease_profile_index_dict[agent]]
            if duration_ticks is not None:
                time_since_state_change = t - self.health_state_change_time[agent]
                if time_since_state_change > duration_ticks:
                    self.bus.publish("request.agent.health", agent, \
                         self.disease_profile_dict[agent][self.disease_profile_index_dict[agent]+1])

    def update_health_indices(self, agent, old_health):
        """Update internal counts."""

        # This shouldn't really happen, but if it does then we're not interested
        if old_health == agent.health:
            return

        self.disease_profile_index_dict[agent] += 1
        self.health_state_change_time[agent] = self.sim.clock.t

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
