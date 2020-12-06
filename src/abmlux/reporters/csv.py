"""Reporters that output to CSV files"""

import os
import os.path
import csv
from collections import defaultdict

from abmlux.reporters import Reporter

class HealthStateCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']
        self.health_state_counts = {}
        self.health_states = []

        self.subscribe("health_state_counts.initial", self.start_sim)
        self.subscribe("world.updates", self.tick_updates)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, run_id, created_at, health_state_counts_initial):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id

        for health_state in list(health_state_counts_initial.keys()):
            self.health_states.append(health_state)

        for health_state in self.health_states:
            self.health_state_counts[health_state] = health_state_counts_initial[health_state]

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601"]
        header += self.health_states

        self.writer.writerow(header)

    def tick_updates(self, clock, telemetry_notifications):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        health_state_updates = [n for n in telemetry_notifications if n[0] == 'health_state_counts.update']
        for _, health, old_health in health_state_updates:
            self.health_state_counts[old_health] -= 1
            self.health_state_counts[health] += 1

        row =  [clock.t, clock.iso8601()]
        row += [self.health_state_counts[k] for k in self.health_states]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class ActivityCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']
        self.activity_counts = {}
        self.activities = []

        self.subscribe("activity_counts.initial", self.start_sim)
        self.subscribe("world.updates", self.tick_updates)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, run_id, created_at, activity_counts_initial):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id

        for activity in list(activity_counts_initial.keys()):
            self.activities.append(activity)

        for activity in self.activities:
            self.activity_counts[activity] = activity_counts_initial[activity]

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601"]
        header += self.activities

        self.writer.writerow(header)

    def tick_updates(self, clock, telemetry_notifications):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        activity_updates = [n for n in telemetry_notifications if n[0] == 'activity_counts.update']
        for _, current_activity, old_activity in activity_updates:
            self.activity_counts[old_activity] -= 1
            self.activity_counts[current_activity] += 1

        row =  [clock.t, clock.iso8601()]
        row += [self.activity_counts[k] for k in self.activities]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class LocationTypeCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']
        self.location_type_counts = {}
        self.location_types = []

        self.subscribe("location_type_counts.initial", self.start_sim)
        self.subscribe("world.updates", self.tick_updates)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, run_id, created_at, location_type_counts_initial):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id

        for location_type in list(location_type_counts_initial.keys()):
            self.location_types.append(location_type)

        for location_type in self.location_types:
            self.location_type_counts[location_type] = location_type_counts_initial[location_type]

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601"]
        header += self.location_types

        self.writer.writerow(header)

    def tick_updates(self, clock, telemetry_notifications):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        location_type_updates = [n for n in telemetry_notifications if n[0] == 'location_type_counts.update']
        for _, current_location, old_location in location_type_updates:
            self.location_type_counts[old_location] -= 1
            self.location_type_counts[current_location] += 1

        row =  [clock.t, clock.iso8601()]
        row += [self.location_type_counts[k] for k in self.location_types]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class TestingCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.tests_performed    = 0
        self.positive_tests     = 0
        self.cum_positive_tests = 0

        self.filename = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("notify.testing.result", self.new_test_result)
        self.subscribe("notify.time.midnight", self.midnight_reset)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, scale_factor):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "tests performed", "positive tests", "cumulative positive tests"]

        self.writer.writerow(header)

    def midnight_reset(self, clock, t):
        """Save data and reset daily counts"""

        row =  [clock.t, clock.iso8601()]
        row += [self.tests_performed, self.positive_tests, self.cum_positive_tests]
        self.writer.writerow(row)

        self.tests_performed = 0
        self.positive_tests  = 0

    def new_test_result(self, clock, test_result, age, uuid, coord, resident):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        self.tests_performed += 1
        if test_result:
            self.positive_tests += 1
            self.cum_positive_tests += 1

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class QuarantineCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.num_in_quaratine = 0
        self.positive_tests  = 0

        self.filename = config['filename']

        self.subscribe("health_state_counts.initial", self.start_sim)
        self.subscribe("quarantine_data", self.new_quarantine_data)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, run_id, created_at, health_state_counts_initial):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "agents in quarantine", "average age"]
        header += list(health_state_counts_initial.keys())
        self.writer.writerow(header)

    def new_quarantine_data(self, clock, num_in_quaratine, agents_in_quarantine_by_health_state, total_age):
        """Save data and reset daily counts"""

        if num_in_quaratine == 0:
            average_age = "N/A"
        else:
            average_age = round(total_age/num_in_quaratine, 4)

        row =  [clock.t, clock.iso8601()]
        row += [num_in_quaratine] + list(agents_in_quarantine_by_health_state.values()) + [average_age]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class TestingEvents(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("notify.testing.result", self.new_test_result)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, scale_factor):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "date", "test result", "age", "home id", "home coordinates", "resident"]
        self.writer.writerow(header)

    def new_test_result(self, clock, test_result, age, uuid, coord, resident):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        row = [clock.t, clock.iso8601(), clock.now().date(), test_result, age, uuid, coord, resident]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class ExposureEvents(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("new_infection", self.new_infection)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, scale_factor):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "date", "location type", "location coordinates", 
                  "agent infected", "age of agent infected", "activity of agent infected" "agent responsible",
                  "age of agent responsible", "activity of agent responsible", "children in home of agent infected",
                  "adults in home of agent infected", "retired in home of agent infected"]
        self.writer.writerow(header)

    def new_infection(self, clock, location_typ, location_coord, home_profile, agent_uuid, agent_age,
                      agent_activity, agent_responsible_uuid, agent_responsible_age,
                      agent_responsible_activity):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        row = [clock.t, clock.iso8601(), clock.now().date(), location_typ, location_coord,
               agent_uuid, agent_age, agent_activity, agent_responsible_uuid, agent_responsible_age,
               agent_responsible_activity] + home_profile
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

class SecondaryInfectionCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']

        self.subscribe("agent_uuids", self.init_counts)
        self.subscribe("new_infection", self.new_infection)
        self.subscribe("simulation.end", self.stop_sim)

        self.secondary_infections_by_agent = {}

    def init_counts(self, agent_uuids):
        """Initialize secondary infection counts"""

        for agent_uuid in agent_uuids:
            self.secondary_infections_by_agent[agent_uuid] = 0

    def new_infection(self, clock, location_typ, location_coord, home_profile, agent_uuid, agent_age,
                      agent_activity, agent_responsible_uuid, agent_responsible_age,
                      agent_responsible_activity):
        """Update the secondary infection counts"""

        self.secondary_infections_by_agent[agent_responsible_uuid] += 1

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["secondary_infections", "count"]
        self.writer.writerow(header)

        max_secondary_infections = max(list(self.secondary_infections_by_agent.values()))
        secondary_infection_counts = {num : 0 for num in range(0, max_secondary_infections + 1)}
        for agent_uuid in self.secondary_infections_by_agent:
            secondary_infection_counts[self.secondary_infections_by_agent[agent_uuid]] += 1

        for count in secondary_infection_counts:
            row = [count, secondary_infection_counts[count]]
            self.writer.writerow(row)

        if self.handle is not None:
            self.handle.close()

class ContactCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("contact_data", self.contact_data)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, scale_factor):
        """Initialize contact counts"""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "date", "average contacts", "average close contacts"]
        self.writer.writerow(header)

    def contact_data(self, clock, contact_counts, total_contact_counts):
        """Update the contact counts"""

        def average_contacts(counts):
            """Calculate average counts"""
            total_contacts = 0
            total_weight = 0
            for k in counts:
                total_contacts += k*counts[k]
                total_weight   += counts[k]
            return round(total_contacts/total_weight, 4)

        average_total_contacts = average_contacts(total_contact_counts)
        average_close_contacts = average_contacts(contact_counts)

        row = [clock.t, clock.iso8601(), clock.now().date(), average_total_contacts, average_close_contacts]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        if self.handle is not None:
            self.handle.close()

class LocationProfiles(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']
        self.health_states = []
        self.location_of_interest = config['location_type']

        self.subscribe("health_state_counts.initial", self.start_s)
        self.subscribe("health_counts_by_location_type", self.health_counts_by_location_type)
        self.subscribe("simulation.end", self.stop_sim)

    def start_s(self, run_id, created_at, health_state_counts_initial):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        for health_state in list(health_state_counts_initial.keys()):
            self.health_states.append(health_state)

        # Write header
        header = ["tick", "iso8601", "date", "location type"]
        header += self.health_states
        self.writer.writerow(header)

    def health_counts_by_location_type(self, clock, health_counts_by_location_type):
        """Update the contact counts"""

        row = [clock.t, clock.iso8601(), clock.now().date(), str(self.location_of_interest)] + list(health_counts_by_location_type[self.location_of_interest].values())
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        if self.handle is not None:
            self.handle.close()
