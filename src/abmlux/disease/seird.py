"""SEIRD-based disease models"""

import logging

from abmlux.disease import DiseaseModel
import abmlux.random_tools as random_tools

log = logging.getLogger("seird_model")

class BasicSEIRDModel(DiseaseModel):

    def __init__(self, prng, config):

        states = ['SUSCEPTIBLE', 'EXPOSED', 'INFECTED', 'RECOVERED', 'DEAD']
        super().__init__(states)

        self.prng                     = prng
        self.num_initial_infections   = config['initial_infections']
        self.infection_probabilities  = config['infection_probabilities_per_tick']
        self.incubation_period_days   = config['incubation_period_days']
        self.infectious_period_days   = config['infectious_period_days']
        self.health_state_change_time = {}
        self.p_death                  = config['probability_of_death']

    def initialise_agents(self, network):
        """Infect some people at simple random, else assign SUSCEPTIBLE state"""

        agents = network.agents

        # Infect a few people
        log.info("Infecting %i agents...", self.num_initial_infections)
        for agent in random_tools.random_sample(self.prng, agents, k=self.num_initial_infections):
            agent.health = 'INFECTED'

        # Leave everyone else SUSCEPTIBLE
        log.info("Marking remaining agents as SUSCEPTIBLE...")
        for agent in agents:
            if agent.health is None:
                agent.health = 'SUSCEPTIBLE'

        log.info("Updating health state index...")
        for agent in agents:
            self.health_state_change_time[agent] = 0


    def get_health_transitions(self, t, sim):

        # FIXME: stop doing this every iteration
        # XXX: These next three lines incur a serious performance penalty.
        incubation_ticks        = sim.clock.days_to_ticks(self.incubation_period_days)
        infectious_ticks        = sim.clock.days_to_ticks(self.infectious_period_days)
        p_death = BasicSEIRDModel._get_p_death_func(self.p_death)

        # Set of changes to return to the simulator
        next_health   = []

        # We'll be exposed n times, so compute a new overall probability of catching
        # the virus from at least one person:
        infection_probability_by_location = {l: 1 - (1-self.infection_probabilities[l.typ])**c
                                             for l, c in sim.agent_counts_by_health['INFECTED'].items()
                                             if c > 0}
        for location, p_infection in infection_probability_by_location.items():
            # All susceptible agents at this location have the given p[infection]

            susceptible_agents = [a for a in sim.attendees[location]
                                  if a.health == 'SUSCEPTIBLE']

            for agent in susceptible_agents:
                if random_tools.boolean(self.prng, p_infection):
                    next_health.append((agent, 'EXPOSED'))

        for agent in sim.agents_by_health_state['EXPOSED']:
            time_since_state_change = t - self.health_state_change_time[agent]

            # If we have incubated for long enough, become infected
            if time_since_state_change > incubation_ticks:
                next_health.append((agent, 'INFECTED'))

        for agent in sim.agents_by_health_state['INFECTED']:
            time_since_state_change = t - self.health_state_change_time[agent]
            # If we have been infected for long enough, become uninfected (i.e.
            # dead or recovered)
            if time_since_state_change > infectious_ticks:
                # die or recover?
                if random_tools.boolean(self.prng, p_death(agent.age)):
                    next_health.append((agent, 'DEAD'))
                else:
                    next_health.append((agent, 'RECOVERED'))

        # Update the counter for when agents last changed health state
        for agent, _ in next_health:
            self.health_state_change_time[agent] = t

        return next_health

    @staticmethod
    def _get_p_death_func(p_death_config):
        """Return a function that takes an age and returns
        the absolute probability of death at the end of the
        infectious period"""

        # Make a slow lookup by checking the range.
        #
        # Assumes no overlapping ranges.
        def p_death_slow(age):
            for rng, p in p_death_config:
                if age >= rng[0] and age < rng[1]:
                    return p
            return 0.0

        # Make a fast lookup. and use this for integers.
        # Fall through to the slow one if not in the list
        oldest_item = max([x[0][1] for x in p_death_config])
        fast_lookup = [p_death_slow(x) for x in range(0, oldest_item)]
        def p_death_fast(age):
            if age in fast_lookup:
                return fast_lookup[age]
            return p_death_slow(age)

        return p_death_fast
