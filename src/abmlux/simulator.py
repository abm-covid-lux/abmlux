"""This file loads the agents, locations and network connections generated by the file
NetworkModel, together with the intial distributions and transition matrices generated by the
file MarkovModel, and simulates an epidemic. Note that the population size N is determined within
the file NetworkModel. In this file, one can set the length of the simulation in weeks and the
number of initial seeds. Note that the simulation starts on a Sunday and follows the SEIRD
framework."""

import logging

import abmlux.random_tools as random_tools

from .sim_time import SimClock

log = logging.getLogger('sim')

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
        self.disease   = state.disease

        # Read-only config
        self.activity_transitions    = state.activity_transitions
        self.reporters               = reporters

        # Simulation state.  These indices represent an optimisation to prevent having to loop
        # over every single agent.
        log.info("Creating agent location indices...")
        self.attendees                     = {l: {a for a in self.agents if a.current_location == l}
                                              for l in self.locations}

        # Disease model parameters
        log.info("Creating health state indices...")
        self.agents_by_health_state        = {h: {a for a in self.agents if a.health == h}
                                              for h in self.disease.states}
        self.agent_counts_by_health = {h: {l: len([a for a in self.attendees[l] if a.health == h])
                                           for l in self.locations}
                                       for h in self.disease.states}
        self.cemeteries      = state.network.locations_by_type['Cemetery']
        self.hospitals       = state.network.locations_by_type['Hospital']
        self.dead_states     = config['dead_states']
        self.hospital_states = config['hospital_states']

    def run(self):
        """Run the simulation"""

        log.info("Simulating outbreak...")
        for reporter in self.reporters:
            reporter.start(self)

        for t in self.clock:

            # - 1 - Compute changes and pop them on the list
            health_changes   = self.disease.get_health_transitions(t, self)
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

            next_activity = self.activity_transitions[agent.agetyp]\
                            [self.clock.ticks_through_week()]\
                            .get_transition(agent.current_activity)

            # If at time t the function get_health_transitions outputs 'HOSPITALIZING' for an agent,
            # then the function _get_activity_transitions will move that agent to hospital at the
            # first time, greater than or equal to t+1, at which the agent chooses to perform a new
            # activity. In other words, agents will finish the current activity before moving to
            # hospital, and similarly as regards leaving hospital. This simple implementation could
            # be modified by allowing activity_changes at time t to depend on health_changes at time
            # t and moreover by allowing agents to enter and exit hospital independently of their
            # Markov chain.
            if agent.health in self.hospital_states:
                if agent.current_location in self.hospitals:
                    next_location = agent.current_location
                else:
                    next_location = random_tools.random_choice(self.prng, self.hospitals)
            elif agent.health in self.dead_states:
                if agent.current_location in self.cemeteries:
                    next_location = agent.current_location
                else:
                    next_location = random_tools.random_choice(self.prng, self.cemeteries)
            else:
                allowable_locations = agent.locations_for_activity(next_activity)
                next_location = random_tools.random_choice(self.prng, list(allowable_locations))

            next_activities.append( (agent, next_activity, next_location) )

        return next_activities

# #################################### INTERVENTIONS ####################################
#
# Non-pharmaceutical interventions fall into three catagories: behavioural, quantitative
# and testing. Behavioural interventions involve restricting the movement of agents. For
# example, certain location types may be blocked between certain dates or certain agents
# may be required to quarantine. A simple, although not particularly efficient,
# implementation of behavioural interventions is as follows, where the time periods
# during which locations types are blocked would be determined in a config:
#
#    allowable_locations = agent.locations_for_activity(next_activity)
#    proposed_location = random_tools.random_choice(self.prng, list(allowable_locations))
#
#    def _behavioural_interventions(self, t, agent, location):
#        """Simple model for interventions based on location choice"""
#        # If the location is blocked then redirect the agent home
#        if location.typ in blocked:
#            location = list(agent.locations_for_activity("House"))[0]
#        # If the agent is quarantining then redirect the agent home
#        if agent.quarantining:
#            location = list(agent.locations_for_activity("House"))[0]
#        # If the agent needs to go to hospital then send the agent to hospital
#        if agent.health in self.hospital_states:
#            if agent.current_location in self.hospitals:
#                location = agent.current_location
#            else:
#                location = random_tools.random_choice(self.prng, self.hospitals)
#        # If the agent has died then send the agent to the cemetery
#        if agent.health in self.dead_states:
#            if agent.current_location in self.cemeteries:
#                location = agent.current_location
#            else:
#                location = random_tools.random_choice(self.prng, self.cemeteries)
#        return location
#
#   next_location = _behavioural_interventions(t, agent, proposed_location)
#
# A simple implementation of the quantitative interventions, which includes for example
# the use of face masks or surface cleaning which reduce the probability of transmission,
# could be to simply multiply the list of probabilities self.infection_probabilities,
# appearing in compartmental.py, by a coefficient in the range [0,1], between specified
# dates.
#
# Implementations of testing, both large scale and via contact tracing, will be somewhat
# more complicated.
#
# #######################################################################################

    def _update_agents(self, health_changes, activity_changes):
        """Update the state of agents according to the lists provided."""

        # 2.1 - Update health status
        for agent, new_health in health_changes:

            # Remove from index
            self.agents_by_health_state[agent.health].remove(agent)
            self.agent_counts_by_health[agent.health][agent.current_location] -= 1

            # Update
            agent.health = new_health

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
