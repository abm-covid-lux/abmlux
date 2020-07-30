"""Tool to produce an area plot showing activity probabilities through the week"""

import logging

import matplotlib.pyplot as plt

from abmlux.agent import AgentType

log = logging.getLogger("plot_activity_routines")

DESCRIPTION = "Plots initial distributions of agent activity throughout the week"
HELP        = """[AGENT_TYPE]"""

def main(state, agent_type=None):
    """Plots initial distributions for activities through the weekly routine.

    Shows roughly what agents will be doing at a given time step.
    """

    activity_manager = state.activity_manager
    activity_distributions = state.activity_distributions
    routine_length = len(activity_distributions[AgentType.ADULT])

    # Compute different colours for each activity
    counts_by_routine_time = {a: [0] * routine_length for a in activity_manager.types_as_str()}

    # Agent types to plot
    agent_types_filter = list(AgentType)
    if agent_type is not None:
        agent_types_filter = [AgentType[agent_type]]
    log.info("Rendering initial distribution for agent type %s", agent_types_filter)

    # For each time t, iterate through the agents and count people's routine
    for agetyp in agent_types_filter:
        for i in range(routine_length):
            for activity, weight in activity_distributions[agetyp][i].items():
                counts_by_routine_time[activity_manager.as_str(activity)][i] += weight

    test = [values for _, values in counts_by_routine_time.items()]

    plt.stackplot(range(routine_length), test, labels=list(counts_by_routine_time.keys()))
    plt.legend(loc="lower left")
    plt.title(f"Initial activity weights for agent types {agent_types_filter}")
    plt.show()
