"""Reporters that output to the terminal"""


from tqdm import tqdm

from abmlux.reporters import Reporter


class TimeReporter(Reporter):
    """Uses TQDM to plot a progress bar"""

    def __init__(self, host, port, config):

        super().__init__(host, port)
        self.subscribe('world.time', self.event)

        self.tqdm = None

    def event(self, clock):

        if self.tqdm is None:
            self.tqdm = tqdm(total=clock.max_ticks)

        self.tqdm.n = clock.t
        self.tqdm.set_description(f"{clock.iso8601()}")



class TickSummaryReporter(Reporter):

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.subscribe('world.updates', self.summarise_tick)
        self.subscribe('simulator.start', self.start_sim)

    def start_sim(self, run_id, created_at, clock, world, disease_states):
        print(f"Simulator run #{run_id} starting at #{created_at}")
        print(f"time, new_activities, new_health_states, new_locations")

    def summarise_tick(self, clock, update_notifications):

        new_activity_count     = 0
        new_health_state_count = 0
        new_location_count     = 0

        for event_type, *args in update_notifications:
            if event_type == 'notify.agent.activity':
                new_activity_count += 1
            if event_type == 'notify.agent.health':
                new_health_state_count += 1
            if event_type == 'notify.agent.location':
                new_location_count += 1

        print(f"{clock.t}, {new_activity_count}, {new_health_state_count}, {new_location_count}")
