"""Responsible for enabling/disabling interventions according to the schedule given."""

import logging
from collections import defaultdict
from typing import Callable

from abmlux.sim_time import SimClock

log = logging.getLogger("scheduler")


class Scheduler:
    """Listens to clock events and enables/disables interventions."""

    def __init__(self, clock: SimClock, intervention_schedules: dict):

        # Pre-process intervention schedules into a list
        self.actions = self._pre_process(clock, intervention_schedules)

    def tick(self, t: int) -> None:
        """Check to see if we should en/disable any interventions at this time"""

        if t in self.actions and self.actions[t] is not None:
            for action in self.actions[t]:
                log.debug("Scheduled action at t=%i: %s", t, action)
                action()

    def _pre_process(self, clock: SimClock,
                     intervention_schedules: dict) -> defaultdict[int, list[Callable]]:
        """Pre-process schedules to identify the tick number at which an action should occur.

        Outputs an array indicating the tick at which actions will occur using the clock given in
        the constructor."""

        events = []
        for intervention, schedules in intervention_schedules.items():

            # Skip if no schedules are given
            if schedules is None:
                continue

            for event_time, event in schedules.items():
                # Parse event time to find the tick number
                if isinstance(event_time, str):
                    ticks = int(clock.datetime_to_ticks(event_time))
                else:
                    ticks = int(event_time)

                # Check event is in the right format
                if event not in ['disable', 'enable'] and not isinstance(event, dict):
                    raise ValueError("Scheduler events should be either 'enable' or 'disable', "
                                     "or be a dict showing what variables to set")

                # Ignore anything in the past
                if ticks < 0:
                    continue

                events.append( (ticks, intervention, event) )

        # If we don't have any, return an empty list
        if len(events) == 0:
            return defaultdict(list)

        # Sort events by the event_time.  Sorts in-place
        events.sort(key=lambda x: x[0])
        log.info("%i scheduled intervention change events planned", len(events))

        # This will keep things indexed by tick as a space-time tradeoff
#        actions = [None] * (events[-1][0] + 1)
        actions: defaultdict[int, list[Callable]] = defaultdict(list)
        action_factory = lambda i, vn, vv: lambda: i.set_registered_variable(vn, vv)
        for tick, intervention, event in events:
            list_of_actions = actions[tick] or []
            if event == 'disable':
                list_of_actions.append(intervention.disable)
            elif event == 'enable':
                list_of_actions.append(intervention.enable)

            # Set a variable to a value
            elif isinstance(event, dict):
                for variable_name, new_value in event.items():
                    new_action = action_factory(intervention, variable_name, new_value)
                    list_of_actions.append(new_action)
            actions[tick] = list_of_actions

        return actions
