"""This file loads the agents, locations and network connections generated by the file
NetworkModel, together with the intial distributions and transition matrices generated by the
file MarkovModel, and simulates an epidemic. Note that the population size N is determined within
the file NetworkModel. In this file, one can set the length of the simulation in weeks and the
number of initial seeds. Note that the simulation starts on a Sunday and follows the SEIRD
framework."""

import logging

import abmlux.random_tools as random_tools

from .agent import HealthStatus
from .sim_time import SimClock

log = logging.getLogger('sim')


def get_p_death_func(p_death_config):
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




class Simulator:
    """Class that simulates an outbreak."""

    def __init__(self, state, reporters):

        # -------------------------------------------[ Config ]------------------------------------
        config                = state.config
        self.state            = state
        self.activity_manager = state.activity_manager
        self.clock            = SimClock(config['tick_length_s'], config['simulation_length_days'],
                                         config['epoch'])

        self.prng      = state.prng
        self.network   = state.network
        self.locations = state.network.locations
        self.agents    = state.network.agents

        # Read-only config
        self.incubation_ticks        = self.clock.days_to_ticks(config['incubation_period_days'])
        self.infectious_ticks        = self.clock.days_to_ticks(config['infectious_period_days'])
        self.p_death                 = get_p_death_func(config['probability_of_death'])
        self.reporters               = reporters
        self.activity_transitions    = state.activity_transitions
        self.infection_probabilities = config['infection_probabilities_per_tick']

        # Simulation state.  These indices represent an optimisation to prevent having to loop
        # over every single agent.
        log.info("Creating simulation state indices...")
        self.health_state_change_time      = {a: 0 for a in self.agents}
        log.info(" - Agents in each location...")
        self.attendees                     = {l: {a for a in self.agents if a.current_location == l}
                                              for l in self.locations}
        log.info(" - Agents by health state...")
        self.agents_by_health_state        = {h: {a for a in self.agents if a.health == h}
                                              for h in list(HealthStatus)}
        log.info(" - Infectious agents counts...")
        self.agent_counts_by_health = {h: {l: len([a for a in self.attendees[l] if a.health == h])
                                           for l in self.locations}
                                       for h in list(HealthStatus)}

    def run(self):
        """Run the simulation"""

        log.info("Simulating outbreak...")
        for reporter in self.reporters:
            reporter.start(self)

        for t in self.clock:

            # - 1 - Compute changes and pop them on the list
            health_changes =  self._get_health_transitions(t)
            activity_changes = self._get_activity_transitions()

            # - 2 - Actually enact changes in an atomic manner
            self._update_agents(t, health_changes, activity_changes)

            for reporter in self.reporters:
                reporter.iterate(self)

        for reporter in self.reporters:
            reporter.stop(self)

    def _get_activity_transitions(self):
        """Return a list of activity transitions agents should enact this tick.

        The list is given as a list of three-tuples, each containing the agent,
        activity, and location to perform that activity: (agent, activity, location)."""

        next_activities = []

        for agent in self.agents:

            if self.activity_transitions[agent.agetyp][self.clock.ticks_through_week()]\
               .get_no_trans(agent.current_activity):
                continue

            next_activity       = self.activity_transitions[agent.agetyp]\
                                  [self.clock.ticks_through_week()]\
                                  .get_transition(agent.current_activity)
            allowable_locations = agent.locations_for_activity(next_activity)

            next_activities.append( (agent,
                                     next_activity,
                                     random_tools.random_choice(self.prng, list(allowable_locations))) )

        return next_activities

    def _get_health_transitions(self, t):
        """Return a list of health transitions agents should enact this tick"""

        next_health   = []

        # We'll be exposed n times, so compute a new overall probability of catching
        # the virus from at least one person:
        infection_probability_by_location = {l: 1 - (1-self.infection_probabilities[l.typ])**c
                                             for l, c in self.agent_counts_by_health[HealthStatus.INFECTED].items()
                                             if c > 0}
        for location, p_infection in infection_probability_by_location.items():
            # All susceptible agents at this location have the given p[infection]

            susceptible_agents = [a for a in self.attendees[location]
                                  if a.health == HealthStatus.SUSCEPTIBLE]

            for agent in susceptible_agents:
                if random_tools.boolean(self.prng, p_infection):
                    next_health.append((agent, HealthStatus.EXPOSED))


        for agent in self.agents_by_health_state[HealthStatus.EXPOSED]:
            time_since_state_change = t - self.health_state_change_time[agent]

            # If we have incubated for long enough, become infected
            if time_since_state_change > self.incubation_ticks:
                next_health.append((agent, HealthStatus.INFECTED))



        for agent in self.agents_by_health_state[HealthStatus.INFECTED]:
            time_since_state_change = t - self.health_state_change_time[agent]
            # If we have been infected for long enough, become uninfected (i.e.
            # dead or recovered)
            if time_since_state_change > self.infectious_ticks:
                # die or recover?
                if random_tools.boolean(self.prng, self.p_death(agent.age)):
                    next_health.append((agent, HealthStatus.DEAD))
                else:
                    next_health.append((agent, HealthStatus.RECOVERED))

        return next_health

    def _update_agents(self, t, health_changes, activity_changes):
        """Update the state of agents according to the lists provided."""

        # 2.1 - Update health status
        for agent, new_health in health_changes:

            # Remove from index
            self.agents_by_health_state[agent.health].remove(agent)
            self.agent_counts_by_health[agent.health][agent.current_location] -= 1

            # Update
            agent.health                         = new_health
            self.health_state_change_time[agent] = t

            # Add to index
            self.agents_by_health_state[agent.health].add(agent)
            self.agent_counts_by_health[agent.health][agent.current_location] += 1


        # 2.2 - Update activity
        for agent, new_activity, new_location in activity_changes:

            # Update indices and set activity
            self.agent_counts_by_health[agent.health][agent.current_location] -= 1
            self.attendees[agent.current_location].remove(agent)
            agent.set_activity(new_activity, new_location)
            self.attendees[agent.current_location].add(agent)
            self.agent_counts_by_health[agent.health][agent.current_location] += 1
