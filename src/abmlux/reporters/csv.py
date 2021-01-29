"""Reporters that output to CSV files"""

import os
import os.path
import csv
from collections import defaultdict

from abmlux.reporters import Reporter

# TODO: handle >1 sim at the same time using the run_id

class HealthStateCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, telemetry_bus, config):
        super().__init__(telemetry_bus)

        self.filename = config['filename']

        self.subscribe("agents_by_health_state_counts.initial", self.initial_counts)
        self.subscribe("agents_by_health_state_counts.update", self.update_counts)
        self.subscribe("simulation.end", self.stop_sim)

    def initial_counts(self, agents_by_health_state_counts):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Collect initial counts
        self.health_state_counts = agents_by_health_state_counts

        # Write header
        header = ["tick", "iso8601"]
        header += list(self.health_state_counts.keys())
        self.writer.writerow(header)

    def update_counts(self, clock, agents_by_health_state_counts):
        """Update the CSV, writing a single row for every clock tick"""

        row =  [clock.t, clock.iso8601()]
        row += list(agents_by_health_state_counts.values())
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

        self.subscribe("agents_by_activity_counts.initial", self.initial_counts)
        self.subscribe("agents_by_activity_counts.update", self.update_counts)
        self.subscribe("simulation.end", self.stop_sim)

    def initial_counts(self, agents_by_activity_counts):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Collect initial counts
        self.activity_counts = agents_by_activity_counts

        # Write header
        header = ["tick", "iso8601"]
        header += list(self.activity_counts.keys())
        self.writer.writerow(header)

    def update_counts(self, clock, agents_by_activity_counts):
        """Update the CSV, writing a single row for every clock tick"""

        row =  [clock.t, clock.iso8601()]
        row += list(agents_by_activity_counts.values())
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

        self.subscribe("agents_by_location_type_counts.initial", self.initial_counts)
        self.subscribe("agents_by_location_type_counts.update", self.update_counts)
        self.subscribe("simulation.end", self.stop_sim)

    def initial_counts(self, agents_by_location_type_counts):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Collect initial counts
        self.location_type_counts = agents_by_location_type_counts

        # Write header
        header = ["tick", "iso8601"]
        header += list(self.location_type_counts.keys())
        self.writer.writerow(header)

    def update_counts(self, clock, agents_by_location_type_counts):
        """Update the CSV, writing a single row for every clock tick"""

        row =  [clock.t, clock.iso8601()]
        row += list(agents_by_location_type_counts.values())
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        if self.handle is not None:
            self.handle.close()

class TestingCounts(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.tests_performed           = 0
        self.positive_tests            = 0
        self.cumulative_positive_tests = 0

        self.filename = config['filename']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("notify.testing.result", self.new_test_result)
        self.subscribe("notify.time.midnight", self.midnight_update)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "tests performed",
                  "positive tests", "cumulative positive tests"]
        self.writer.writerow(header)

    def midnight_update(self, clock):
        """Save data and reset daily counts"""

        row =  [clock.t, clock.iso8601()]
        row += [self.tests_performed, self.positive_tests, self.cumulative_positive_tests]
        self.writer.writerow(row)

        self.tests_performed = 0
        self.positive_tests  = 0

    def new_test_result(self, clock, test_result, age, uuid, coord, resident):
        """Update the CSV, writing a single row for every clock tick"""

        self.tests_performed += 1
        if test_result:
            self.positive_tests += 1
            self.cumulative_positive_tests += 1

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

    def start_sim(self):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "date", "test result",
                  "age", "home id", "home coordinates", "resident"]
        self.writer.writerow(header)

    def new_test_result(self, clock, test_result, age, uuid, coord, resident):
        """Update the CSV, writing a single row for every clock tick"""

        row = [clock.t, clock.iso8601(), clock.now().date(), test_result,
               age, uuid, coord, resident]
        self.writer.writerow(row)

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

        self.subscribe("agents_by_health_state_counts.initial", self.health_states)
        self.subscribe("quarantine_data", self.update_quarantine_counts)
        self.subscribe("simulation.end", self.stop_sim)

    def health_states(self, agents_by_health_state_counts):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "date", "agents in quarantine", "average age"]
        header += list(agents_by_health_state_counts.keys())
        self.writer.writerow(header)

    def update_quarantine_counts(self, clock, num_in_quaratine, agents_in_quarantine_by_health_state, total_age):
        """Save data and reset daily counts"""

        if num_in_quaratine == 0:
            average_age = "N/A"
        else:
            average_age = round(total_age/num_in_quaratine, 4)

        row =  [clock.t, clock.now().date()]
        row += [num_in_quaratine, average_age] + list(agents_in_quarantine_by_health_state.values())
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

        self.subscribe("agent_data.initial", self.initial_agent_data)
        self.subscribe("new_infection", self.new_infection)
        self.subscribe("simulation.end", self.stop_sim)

    def initial_agent_data(self, agent_uuids):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "iso8601", "date", "location type", "location coordinates",
                  "agent infected", "age of agent infected", "activity of agent infected",
                  "agent responsible", "age of agent responsible", "activity of agent responsible"]
        self.writer.writerow(header)

    def new_infection(self, clock, location_typ, location_coord, agent_uuid, agent_age,
                      agent_activity, agent_responsible_uuid, agent_responsible_age,
                      agent_responsible_activity):
        """Update the CSV, writing a single row for every clock tick"""

        row = [clock.t, clock.iso8601(), clock.now().date(), location_typ, location_coord,
               agent_uuid, agent_age, agent_activity, agent_responsible_uuid, agent_responsible_age,
               agent_responsible_activity]
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

        self.subscribe("agent_data.initial", self.initial_agent_data)
        self.subscribe("new_infection", self.new_infection)
        self.subscribe("simulation.end", self.stop_sim)

        self.secondary_infections_by_agent = {}

    def initial_agent_data(self, agent_uuids):
        """Initialize secondary infection counts"""

        for agent_uuid in agent_uuids:
            self.secondary_infections_by_agent[agent_uuid] = 0

    def new_infection(self, clock, location_typ, location_coord, agent_uuid, agent_age,
                      agent_activity, agent_responsible_uuid, agent_responsible_age,
                      agent_responsible_activity):
        """Update the secondary infection counts"""

        self.secondary_infections_by_agent[agent_responsible_uuid] += 1

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

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

    def start_sim(self):
        """Initialize contact counts"""

        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "date", "average total contacts", "average regular contacts"]
        self.writer.writerow(header)

    def contact_data(self, clock, regular_contact_counts, total_contact_counts):
        """Update the contact counts"""

        def average_contacts(counts):
            """Calculate average counts"""
            total_weight   = sum(counts.values())
            total_contacts = sum([k*counts[k] for k in counts])
            if total_weight == 0:
                average = "N/A"
            else:
                average = round(total_contacts/total_weight, 4)
            return average

        average_total_contacts   = average_contacts(total_contact_counts)
        average_regular_contacts = average_contacts(regular_contact_counts)

        row = [clock.t, clock.now().date(), average_total_contacts, average_regular_contacts]
        self.writer.writerow(row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        if self.handle is not None:
            self.handle.close()

class VaccinationEvents(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.filename = config['filename']

        self.subscribe("agent_data.initial", self.initial_agent_data)
        self.subscribe("notify.vaccination.first_doses", self.first_doses)
        self.subscribe("simulation.end", self.stop_sim)

    def initial_agent_data(self, agent_uuids):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        dirname = os.path.dirname(self.filename)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename, 'w')
        self.writer = csv.writer(self.handle)

        # Write header
        header = ["tick", "date", "age", "health", "nationality", "home type", "work type"]
        self.writer.writerow(header)

    def first_doses(self, clock, agent_data):
        """Update the CSV, writing a single row for every clock tick"""

        for row in agent_data:
            self.writer.writerow([clock.t, clock.now().date()] + row)

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""

        if self.handle is not None:
            self.handle.close()
