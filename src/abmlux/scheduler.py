"""Responsible for enabling/disabling interventions according to the schedule given."""

import logging

log = logging.getLogger("scheduler")


class Scheduler:
    """Listens to clock events and enables/disables interventions."""

    def __init__(self, clock, bus, intervention_schedules):

        # Pre-process intervention schedules into a list
        self.actions = self._pre_process(clock, intervention_schedules)

        # Hook onto the simulator's clock events.
        #
        # If there are no events, don't even bother registering the callback.  Optimisation!
        if len(self.actions):
            bus.subscribe("notify.time.tick", self.tick, self)
        else:
            log.info("No schedules given, interventions will be enabled throughout simulation")

    def tick(self, clock, t):
        """Check to see if we should en/disable any interventions at this time"""

        if t in self.actions and self.actions[t] is not None:
            for action in self.actions[t]:
                action()

    def _pre_process(self, clock, intervention_schedules):
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
                if event not in ['disable', 'enable']:
                    raise ValueError("Scheduler events should be either 'enable' or 'disable'")

                # Ignore anything in the past
                if ticks < 0:
                    continue

                events.append( (ticks, intervention, event) )

        # If we don't have any, return an empty list
        if len(events) == 0:
            return []

        # Sort events by the event_time.  Sorts in-place
        events.sort(key=lambda x: x[0])
        log.info("%i scheduled intervention change events planned", len(events))

        # This will keep things indexed by tick as a space-time tradeoff
        actions = [None] * (events[-1][0] + 1)
        for tick, intervention, event in events:
            list_of_actions = actions[tick] or []
            if event == 'disable':
                list_of_actions.append(intervention.disable)
            elif event == 'enable':
                list_of_actions.append(intervention.enable)
            actions[tick] = list_of_actions

        return actions
