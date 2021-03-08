"""Represents vaccination schemes"""

import logging
import math

from abmlux.sim_time import DeferredEventPool
from abmlux.interventions import Intervention

log = logging.getLogger("vaccination")

# This file uses callbacks and interfaces which make this hit many false positives
#pylint: disable=unused-argument
#pylint: disable=attribute-defined-outside-init
class Vaccination(Intervention):
    """Vaccinate agents using a two dose vaccine prioritizing certain agents first"""

    def __init__(self, config, init_enabled):
        super().__init__(config, init_enabled)

        # This represents the daily vaccination capacity
        self.register_variable('max_first_doses_per_day')

    def init_sim(self, sim):
        super().init_sim(sim)

        # This controls how many first doses are able to be distributed per day. The total number
        # of doses per day will be this number plus the number of second doses delivered that day.
        self.scale_factor = sim.world.scale_factor
        self.max_first_doses_per_day = self.config['max_first_doses_per_day']

        # A certain amount of time after the first dose, a second dose will be administered
        time_between_doses_days       = int(self.config['time_between_doses_days'])
        self.time_between_doses_ticks = int(sim.clock.days_to_ticks(time_between_doses_days))
        self.second_dose_events = DeferredEventPool(self.bus, sim.clock)

        self.bus.subscribe("notify.time.midnight", self.midnight, self)
        # self.bus.subscribe("notify.testing.result", self.update_vaccination_priority_list, self)
        self.bus.subscribe("request.vaccination.second_dose", self.administer_second_dose, self)

        # A list of agents to be vaccinated
        self.vaccination_priority_list = []

        # A precomuted record of where agents live and work, for telemetry purposes
        self.home_location_type_dict = {}
        self.work_location_type_dict = {}

        # Order the agents according to the desired preferential scheme
        carehome_residents_workers = []
        hospital_workers           = []
        other_agents               = []

        care_home_location_type = self.config['care_home_location_type']
        hospital_location_type  = self.config['hospital_location_type']
        home_activity_type      = sim.activity_manager.as_int(self.config['home_activity_type'])
        work_activity_type      = sim.activity_manager.as_int(self.config['work_activity_type'])

        self.first_dose_successful  = self.config['prob_first_dose_successful']
        self.second_dose_successful = self.config['prob_second_dose_successful']

        min_age = self.config['min_age']

        age_low  = self.config['age_low']
        age_high = self.config['age_high']

        prob_low  = self.config['prob_low']
        prob_med  = self.config['prob_med']
        prob_high = self.config['prob_high']

        # A dictionary of who doesn't refuse the vaccine
        self.agent_wants_vaccine = {}

        # Decide in advance who will refuse the vaccine
        for agent in sim.world.agents:
            if agent.age >= min_age:
                if agent.age < age_low:
                    self.agent_wants_vaccine[agent] = self.prng.boolean(prob_low)
                if agent.age >= age_low and agent.age < age_high:
                    self.agent_wants_vaccine[agent] = self.prng.boolean(prob_med)
                if agent.age >= age_high:
                    self.agent_wants_vaccine[agent] = self.prng.boolean(prob_high)

        # Dictionaries of efficacy for each agent
        self.first_dose_effective  = {}
        self.second_dose_effective = {}

        # Determine in advance the effecitveness of the vaccine on each agent
        for agent in sim.world.agents:
            if agent.age >= min_age:
                self.first_dose_effective[agent] = self.prng.boolean(self.first_dose_successful)
                self.second_dose_effective[agent] = self.prng.boolean(self.second_dose_successful)

        # Determine which agents live or work in carehomes and which agents work in hospitals. Note
        # that workplaces are assigned to everybody, so some agents will be assigned hospitals or
        # carehomes as places of work but, due to their routines, will not actually go to work at
        # these places due to not working at all. So this is somewhat approximate.
        for agent in sim.world.agents:
            if agent.age >= min_age:
                home_location = agent.locations_for_activity(home_activity_type)[0]
                self.home_location_type_dict[agent] = home_location.typ
                work_location = agent.locations_for_activity(work_activity_type)[0]
                self.work_location_type_dict[agent] = work_location.typ
                if home_location.typ in care_home_location_type or\
                    work_location.typ in care_home_location_type:
                    carehome_residents_workers.append(agent)
                elif work_location.typ in hospital_location_type:
                    hospital_workers.append(agent)
                else:
                    other_agents.append(agent)

        # Sort the lists of agents by age, with the oldest first
        def return_age(agent):
            return agent.age
        carehome_residents_workers.sort(key=return_age, reverse=True)
        hospital_workers.sort(key=return_age, reverse=True)
        other_agents.sort(key=return_age, reverse=True)

        # Combine these lists together to get the order of agents to be vaccinated
        self.vaccination_priority_list = carehome_residents_workers + hospital_workers\
                                                                    + other_agents

    # def update_vaccination_priority_list(self, agent, test_result):
    #     """Agents who have tested positive are removed from the list of agents to be vaccinated"""

    #     if test_result:
    #         try:
    #             self.vaccination_priority_list.remove(agent)
    #         except ValueError:
    #             pass

    def administer_second_dose(self, agent):
        """Administers agents with a second dose of the vaccine"""

        if self.second_dose_effective[agent]:
            agent.vaccinated = True

    def midnight(self, clock, t):
        """At midnight, remove from the priority list agents who have tested positive that day
        and vaccinate an appropriate number of the remainder"""

        if not self.enabled:
            return

        if self.max_first_doses_per_day == 0:
            return

        max_rescaled =  math.ceil(self.scale_factor * self.max_first_doses_per_day)
        num_to_vaccinate = min(max_rescaled, len(self.vaccination_priority_list))

        agents_to_vaccinate = self.vaccination_priority_list[0:num_to_vaccinate]
        del self.vaccination_priority_list[0:num_to_vaccinate]

        agent_data = []
        for agent in agents_to_vaccinate:
            if self.agent_wants_vaccine[agent]:
                if self.first_dose_effective[agent]:
                    agent.vaccinated = True
                self.second_dose_events.add("request.vaccination.second_dose",
                                            self.time_between_doses_ticks, agent)

                # For telemetry
                agent_data.append([agent.age, agent.health, agent.nationality,
                                self.home_location_type_dict[agent],
                                self.work_location_type_dict[agent]])

        self.report("notify.vaccination.first_doses", clock, agent_data)
