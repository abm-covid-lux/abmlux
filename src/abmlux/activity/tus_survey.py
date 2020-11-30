"""
This file constructs initial distributions and transition matrices using data from the
Luxembourgish Time Use Survey (TUS). Each respondent to the TUS provided two diaries of
activities, one for a week day and one for a weekend day, together with their age and the times
at which these activities began. Associated to each respondent there is also a statistical weight
and an identification number. Activities are denoted by a numeric code and therefore a daily
routine consists of a sequence of such numbers.

Activities are grouped together according to the location in which the activity occurs.
Daily routines are then concatenated to produce, for each respondent, a typical weekly
routine. The week begins on Sunday and ends on Saturday. Three sets of transition matrices
and initial distributions are then constructed from these routines, for children, adults
and retired individuals, respectively.  In particular, for each age group a transition matrix
is constructed for each 10 minute interval of the week, of which there are 7*144 in total."""

import logging

import pandas as pd
from tqdm import tqdm

import abmlux.utils as utils
from abmlux.activity import ActivityModel
from abmlux.sim_time import SimClock
from abmlux.diary import DiaryDay, DiaryWeek, DayOfWeek
from abmlux.agent import POPULATION_RANGES
from abmlux.transition_matrix import SplitTransitionMatrix

# Number of 10min chunks in a day.  Used when parsing the input data at a 10min resolution
DAY_LENGTH_10MIN = 144

log = logging.getLogger('markov_model')


class TUSMarkovActivityModel(ActivityModel):
    """Uses Time-of-Use Survey data to build a markov model of activities, which are then
    cycled through in a set of routines."""

    def __init__(self, config, activity_manager):

        super().__init__(config, activity_manager)

        # These can be computed ahead of time
        self.activity_distributions, self.activity_transitions = self._build_markov_model()

        # Runtime config
        self.stop_activity_health_states = config['stop_activity_health_states']

    def init_sim(self, sim):
        super().init_sim(sim)

        self.world = sim.world

        # Hook into the simulation's messagebus
        self.bus.subscribe("notify.time.tick", self.send_activity_change_events, self)
        self.bus.subscribe("notify.time.start_simulation", self.start_simulation, self)
        self.bus.subscribe("notify.agent.health", self.remove_agents_from_active_list, self)

    def start_simulation(self, sim):
        """Start a simulation.

        Resets the internal counters."""

        # These agents are still having activity updates
        self.active_agents = set(sim.world.agents)

        log.debug("Seeding initial activity states and locations...")
        clock = sim.clock
        for agent in self.world.agents:
            # Get distribution for this type at the starting time step
            distribution = self.activity_distributions[agent.agetyp][clock.epoch_week_offset]
            assert sum(distribution.values()) > 0
            new_activity      = self.prng.multinoulli_dict(distribution)
            allowed_locations = agent.locations_for_activity(new_activity)
            agent.set_activity(new_activity)

            # TODO: location selection code should be triggered by messaging via the bus,
            #       as it will be in the main sim.
            #
            # Warn: No allowed locations found for agent {agent.inspect()} for activity new_activity
            assert len(allowed_locations) >= 0
            new_location = self.prng.random_choice(list(allowed_locations))
            # Do this activity in a random location
            agent.set_location(new_location)

    def remove_agents_from_active_list(self, agent, new_health):
        """If the new health state is in the 'dead list', remove the agent from the list
        of people who get told to change activity."""

        if new_health in self.stop_activity_health_states:
            self.active_agents.remove(agent)

    def send_activity_change_events(self, clock, t):
        """Return a list of activity transitions agents should enact this tick.

        The list is given as a list of three-tuples, each containing the agent,
        activity, and location to perform that activity: (agent, activity, location)."""

        ticks_through_week = clock.ticks_through_week()

        for agent in self.active_agents:

            if self.activity_transitions[agent.agetyp][ticks_through_week] \
               .get_no_trans(agent.current_activity):
                continue

            next_activity = self.activity_transitions[agent.agetyp] \
                            [ticks_through_week].get_transition(agent.current_activity)

            self.bus.publish("request.agent.activity", agent, next_activity)

    def _get_tus_code_mapping(self, map_config):
        """Return a function mapping TUS activity codes onto those used in this model.

        TUS codes are defined in two fields, primary and secondary.
        If primary == 7, we switch to secondary.

        Primary and secondary mappings are defined in map_config as a dict
        of abm labels and primary/secondary keys containing a list of TUS
        codes, e.g.:

        {'House': {'primary': [1], 'secondary': [11,12,13,14]},
        'Work': {'primary': [2]}}

        The resulting function takes two arguments, namely the TUS primary
        and secondary codes, as ints.  It returns one of the keys
        from the mapping given to _this_ function.
        """
        # pylint doesn't like our primary, secondary shorthand below.
        # pylint: disable=invalid-name

        # Compute primary and secondary together.
        mapping_pri = {}
        mapping_sec = {}
        for abm_code, v in map_config.items():
            primary   = v['primary']   or [] if 'primary'   in v else []
            secondary = v['secondary'] or [] if 'secondary' in v else []

            for p in primary:
                mapping_pri[p] = self.activity_manager.as_int(abm_code)
            for s in secondary:
                mapping_sec[s] = self.activity_manager.as_int(abm_code)

        # Define mapping function, enclosing the above mapping
        def tus_activity_to_abm_activity(tus_pri, tus_sec):
            if tus_pri != 7:
                return mapping_pri[tus_pri]
            return mapping_sec[tus_sec]

        return tus_activity_to_abm_activity


    def _create_weekly_routines(self, days):
        """Create weekly routines for individuals, reading their daily routines
        as example days

        The format of the TUS data is such that each pair of daily diaries are listed consecutively,
        so for each person there are two rows, e.g:
        - personA: weekend
        - personA: weekday
        - personB: weekend
        - personB: weekday
        We don't know which way around these are, though.  This routine builds a week out of the
        weekday, repeated, plus the weekend.

        Parameters:
            days (list):List of abmlux.DiaryDay objects representing individuals' routines from the
                        time-of-use survey daya

        Returns:
            weeks: A list of weekly routines built out of the daily routines.
        """

        weeks = []
        for i in range(0, len(days)-1, 2):

            # Make a bold assumption
            weekend, weekday = days[i], days[i+1]

            # Swap if we were wrong
            if weekday.day in [DayOfWeek.SUNDAY, DayOfWeek.SATURDAY]:
                weekday, weekend = weekend, weekday

            # Check the identity is the same
            assert weekday.identity == weekend.identity

            # Create a week with most things the same, but with a whole week's worth of activities
            week = DiaryWeek(weekday.identity, weekday.age, weekday.weight,
                             weekend.daily_routine + weekday.daily_routine \
                             * 5 + weekend.daily_routine)
            weeks.append(week)

        return weeks


    def _parse_days(self, tus, map_func, tick_length_s):
        """Returns a list of DiaryDay functions built from the TUS data provided.

        The following piece of code constructs the daily routines. This takes into account the fact
        that diaries appearing in the TUS do not all start at the same time and do not all run for
        24 hours.
        This is achieved by first extending the duration of the last activity, to create a 24 hour
        routine, after which the piece of the routine extending beyong the end of the day is
        repositioned to the start of the day. This way, all routines cover a 24 hour period running
        from midnight to midnight.

        Parameters:
            tus (pandas dataframe):The TUS dataset loaded from excel
            map_func (function):A function taking two ints and returning
                                the activity code for this row.
            tick_length_s:The length of ticks in the simulation, in seconds

        Returns:
            days(list):A list of DiaryDay objects.
        """
        # We use so many variables to be clearer in the parsing logic
        # pylint: disable=too-many-locals

        days  = []
        clock = SimClock(tick_length_s, 1)
        for date in tqdm(tus['id_jour'].unique()):
            tus_date  = tus.loc[tus['id_jour'] == date]
            durations = [y-x for x, y in
                         list(zip(tus_date['heuredebmin'], tus_date['heuredebmin'][1:]))]

            end_activity = map_func(tus_date.iloc[-1]['loc1_num_f'], tus_date.iloc[-1]['act1b_f'])
            start_time = tus_date.iloc[0]['heuredebmin']

            # Build variables for object at 10min resolution
            identity, age, day, weight = [tus_date.iloc[0][x]
                                          for x in ['id_ind', 'age', 'jours_f', 'poids_ind']]
            daily_routine_tenmin = [end_activity] * start_time \
                        + utils.flatten([[map_func(tus_date.iloc[i]['loc1_num_f'], tus_date.iloc[i]['act1b_f'])] * d
                                         for i, d in enumerate(durations)]) \
                        + [end_activity] * (DAY_LENGTH_10MIN - sum(durations) - start_time)

            # Resample into the clock resolution
            log.debug("Resampling 10 minute chunks into clock resolution (%is)...", clock.tick_length_s)
            daily_routine = []
            clock.reset()
            for _ in clock:
                seconds_through_day = clock.seconds_elapsed()
                tenmin_bin = int(seconds_through_day / (10 * 60))
                daily_routine.append(daily_routine_tenmin[tenmin_bin])

            # Create the list entry
            day = DiaryDay(identity, age, day, weight, daily_routine)
            days.append(day)

        return days


    def _get_transitions(self, weeks):
        """Converts weekly routines into a set of transition matrices and initial distributions
        for each type of agent.

        We start by building weights for each action at each time step, indexed by the agent
        type.  This describes the initial distribution of actions for every time tick through
        the week, allowing us to start a simulation at any time.

            AgentType.ADULT: [{action: weight, action2: weight2},
                            {action: weight, action2: weight2}...],

        Transitions are then read from the weekly diaries and a transition matrix is built showing
        the probability of transitioning from one activity to the next at each time tick.  This is
        also indexed by agent type.

        Parameters:
            weeks (list):List of DiaryWeek objects containing weekly routines.

        Returns:
            activity_distributions:The initial distribution structure above
            activity_transitions:Tick-to-tick transition weights between activities
        """

        # We keep reusing this throughout
        week_length = len(weeks[0].weekly_routine)  # Assume the first week is representative

        log.info("Generating activity distributions...")
        activity_distributions = {typ: [{activity: 0 for activity in self.activity_manager.types_as_int()}
                                        for i in range(week_length)]
                                  for typ in POPULATION_RANGES}
        for typ, rng in POPULATION_RANGES.items():
            log.debug(" - %s %s", typ, rng)
            for week in tqdm(weeks):
                if week.age in rng:
                    for i, _ in enumerate(week.weekly_routine):
                        activity_distributions[typ][i][week.weekly_routine[i]] += week.weight

        log.info('Generating weighted activity transition matrices...')
        # Activity -> activity transition matrix
        #
        # AgentType.CHILD: [[[activity, activity], [activity, activity]]]
        #
        #  - Each activity has a W[next activity]
        #  - Each 10 minute slice has a transition matrix between activities
        #
        activity_transitions = {typ: [SplitTransitionMatrix(self.prng,\
                                                            self.activity_manager.types_as_int())
                                      for _ in range(week_length)]
                                for typ in POPULATION_RANGES}

        # Do all but the last item, which should loop around
        for t in tqdm(range(week_length)):
            for week in weeks:
                for typ, rng in POPULATION_RANGES.items():
                    if week.age in rng:

                        # Wrap around to zero to make the week
                        # one big loop
                        next_t = (t+1) % week_length

                        # Retrieve the activity transition
                        activity_from = week.weekly_routine[t]
                        activity_to   = week.weekly_routine[next_t]

                        activity_transitions[typ][t].add_weight(activity_from, activity_to,\
                                                                week.weight)


        # Debug output
        #
        # for t in tqdm(range(week_length)):
        #     distribution = activity_distributions[AgentType.RETIRED][t]
        #     transitions  = activity_transitions[AgentType.RETIRED][t]

        #     for activity in self.activity_manager.types_as_int():
        #         if distribution[activity] > 0 and transitions.x_marginal(activity) == 0:

        #             print(f"-> {t=}")
        #             print(f"-> {activity=}")
        #             print(f"-> {distribution=}")
        #             print(f"-> {distribution[activity]=}")
        #             print(f"-> {transitions.transitions[activity]=}")
        #             print(f"-> {transitions.x_marginals=}")

        #             import code; code.interact(local=locals())

        return activity_distributions, activity_transitions


    def _build_markov_model(self):
        """Constructs activity transition matrices for the world given.

        Returns:
            activity_distributions(dict):A list of initial distributions indexed by AgentType
            activity_transitions(dict):A list of activity transitions indexed by AgentType
        """

        # ------------------------------------------------------------------------------------------
        log.info("Loading time use data from %s...", self.config.filepath('time_use_filepath'))
        # TODO: force pandas to read the numeric ID columns as factors or ints
        #       same for weights
        tus = pd.read_csv(self.config.filepath('time_use_filepath'))
        tus = tus.dropna()

        # ------------------------------------------------------------------------------------------
        log.info('Generating daily routines...')

        # As mentioned above, activities are numerically coded. The file FormatsTUS displays the
        # codification of primary and secondary activities used by the TUS. The primary activities
        # will be grouped together according to datamap_primary while the secondary activities will
        # be grouped together according to datamap_secondary.
        #
        # The latter is used if and only if a respondent recorded 'Other specified location' as the
        # primary activity, in which case referal to the secondary activity is necessary. Activities
        # are consquently recoded as numbers in the set {0,...,13}, as described in the file
        # FormatActivities.

        map_func = self._get_tus_code_mapping(self.config['activity_code_map'])
        days     = self._parse_days(tus, map_func, self.config['tick_length_s'])
        log.info("Created %i days", len(days))

        # print('\n'.join([''.join([d[0] for d in days[x].daily_routine]) for x in \
        # range(len(days))]))
        # For each respondent there are now two daily routines; one for a week day and one for a
        # weekend day.  Copies of these routines are now concatenated so as to produce weekly
        # routines, starting on Sunday.

        # ------------------------------------------------------------------------------------------
        log.info("Generating weekly routines...")
        weeks = self._create_weekly_routines(days)
        log.debug("Created %i weeks", len(weeks))

        # ------------------------------------------------------------------------------------------
        # Now the statistical weights are used to construct the intial distributions and transition
        # matrices:
        activity_distributions, activity_transitions = self._get_transitions(weeks)


        return activity_distributions, activity_transitions
