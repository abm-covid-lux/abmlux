"""SEIRD-based disease models"""

import csv
import logging
from io import StringIO

from scipy.stats import gamma

from abmlux.disease import DiseaseModel
import abmlux.random_tools as random_tools

log = logging.getLogger("adv_seird_model")

class AdvancedSEIRDModel(DiseaseModel):

    def __init__(self, prng, config):

        states = ['SUSCEPTIBLE',                                        # Not Infected
                  'ASYMPTOMATIC', 'EXPOSED', 'PRECLINICAL', 'INFECTED', # INFECTED == SYMPTOMATIC
                  'HOSPITALISED', 'VENTILATING', 'RECOVERED', 'DEAD']   # Intervention
        super().__init__(states)

        self.prng = prng
        self.agent_disease_progression = {}

        # Load disease progression values
        #
        # FIXME: change YAML config format to have an explicit range of values
        disease_progression = []
        print(f"-> {config['infection_profiles_by_age']}")
        strio = StringIO(config['infection_profiles_by_age'])
        reader = csv.reader(strio)
        for row in reader:              # each row is a list
            disease_progression.append([x.strip() for x in row])
            print(f"-> {disease_progression=}")

        # For a range of ages, creates dictionaries associating probabilities
        # to disease progression profiles
        dict_by_age = {}
        for row in range(1, len(disease_progression)):
            age = int(disease_progression[row][0])
            dict_by_age[age] = {}
            for cln in range(1, len(disease_progression[0])):
                dict_by_age[age][disease_progression[0][cln]] = float(disease_progression[row][cln])
        self.dict_by_age = dict_by_age

    def initialise_agents(self, network):
        """Infect some people at simple random, else assign SUSCEPTIBLE state"""

        # Assign a disease progression
        agents = network.agents
        for agent in agents:
            # FIXME!  This should use an index of ranges, rather than assuming row location
            age_rounded = (agent.age//5)*5
            if age_rounded >= 95:
                age_rounded = 90
            profile = random_tools.random_choices(self.prng,
                                                  list(self.dict_by_age[age_rounded].keys()),
                                                  self.dict_by_age[age_rounded].values(),
                                                  1)[0]

            durations = self._durations_for_profile(profile)
            profile = [self.state_for_letter(l) for l in profile]
            assert len(durations) == len(profile) - 1
            print(f"-> {profile=}, {durations=}")
            # list(zip(profile, durations))

    def get_health_transitions(self, t, sim):
        return []

    def _durations_for_profile(self, profile):
        if profile == "EAR":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_A()]
        if profile == "EPIR":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._duration_I()]
        if profile == "EPID":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._uniform_dur(list(range(10,15)))]
        if profile == "EPIHR":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._uniform_dur(list(range(5,9))),
                           AdvancedSEIRDModel._uniform_dur(list(range(8,21)))]
        if profile == "EPIHD":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._uniform_dur(list(range(5,9))),
                           AdvancedSEIRDModel._uniform_dur(list(range(5,16)))]
        if profile == "EPIHVHR":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._uniform_dur(list(range(5,9))),
                           AdvancedSEIRDModel._uniform_dur(list(range(3,5))),AdvancedSEIRDModel._uniform_dur(list(range(2,12))),
                           AdvancedSEIRDModel._uniform_dur(list(range(2,4)))]
        if profile == "EPIHVHD":
            trans_times = [AdvancedSEIRDModel._duration_E(),AdvancedSEIRDModel._duration_P(),AdvancedSEIRDModel._uniform_dur(list(range(5,9))),
                           AdvancedSEIRDModel._uniform_dur(list(range(3,5))),AdvancedSEIRDModel._uniform_dur(list(range(7,10)))]

        return trans_times

    @staticmethod
    def _duration_E():
        """The distribution of incubation period"""
        # FIXME: use PRNG state via random_tools lib
        return  gamma.rvs(4, loc = 0, scale = 3/4)

    @staticmethod
    def _duration_A():
        """The distribution of asymptomatic period"""
        # FIXME: use PRNG state via random_tools lib
        return  gamma.rvs(4, loc = 0, scale = 5/4)

    @staticmethod
    def _duration_P():
        """The distribution of preclinical period"""
        # FIXME: use PRNG state via random_tools lib
        return  gamma.rvs(4, loc = 0, scale = 2.1/4)

    @staticmethod
    def _duration_I():
        """The distribution of a simple infectious period"""
        # FIXME: use PRNG state via random_tools lib
        return  gamma.rvs(4, loc = 0, scale = 2.9/4)

    @staticmethod
    def _uniform_dur(prng, range_days):
        """Uniform distribution across a range of days"""
        # FIXME: use PRNG state via random_tools lib
        return  random_tools.random_choice(prng, range_days)


