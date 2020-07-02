#!/usr/bin/env python3

#Markov Model

#This file constructs initial distributions and transition matrices using data from the Luxembourgish
#Time Use Survey (TUS). Each respondent to the TUS provided two diaries of activities, one for a week
#day and one for a weekend day, together with their age and the times at which these activities began
#. Associated to each respondent there is also a statistical weight and an identification number. Act
#ivities are denoted by a numeric code and therefore a daily routine consists of a sequence of such n
#umbers. Activities are grouped together according to the location in which the activity occurs. Dail
#y routines are then concatenated to produce, for each respondent, a typical weekly routine. The week
#begins on Sunday and ends on Saturday. Three sets of transition matrices and initial distributions a
#re then constructed from these routines, for children, adults and retired individuals, respectively.
#In particular, for each age group a transition matrix is constructed for each 10 minute interval of 
#the week, of which there are 7*144 in total.

import sys
import os.path as osp
import math
import pickle

import numpy as np
import pandas as pd
from tqdm import tqdm

from .diary import DiaryDay, DiaryWeek, DayOfWeek
from .agent import AgentType, POPULATION_RANGES
from .activity import ActivityManager
import abmlux.utils as utils
import abmlux.random_tools as random_tools

DAY_LENGTH_10MIN = 144
WEEK_LENGTH_10MIN = 7 * DAY_LENGTH_10MIN

INITIAL_DISTRIBUTIONS_FILENAME = 'Initial_Activities.pickle'
TRANSITION_MATRIX_FILENAME     = 'Activity_Transition_Matrix.pickle'

def build_markov_model(config):
    activity_manager = ActivityManager(config['activities'])

    # ---------------------------------------------------------------------------------------------------
    print(f"Loading time use data from {config.filepath('time_use_fp')}...")
    # TODO: force pandas to read the numeric ID columns as factors or ints
    #       same for weights
    tus = pd.read_csv(config.filepath('time_use_fp'))
    tus = tus.dropna()


    # ---------------------------------------------------------------------------------------------------
    print('Generating daily routines...')

    # As mentioned above, activities are numerically coded. The file FormatsTUS displays the codification
    # of primary and secondary activities used by the TUS. The primary activities will be grouped together
    # according to datamap_primary while the secondary activities will be grouped together according to
    # datamap_secondary.
    #
    # The latter is used if and only if a respondent recorded 'Other specified location' as the primary
    # activity, in which case referal to the secondary activity is necessary. Activities are consquently
    # recoded as numbers in the set {0,...,13}, as described in the file FormatActivities.


    def get_tus_code_mapping(map_config, ActivityType):
        """Return a function mapping TUS activity codes onto those used
        in this model.

        TUS codes are defined in two fields, primary and secondary.  If
        primary == 7, we switch to secondary.

        Primary and secondary mappings are defined in map_config as a dict
        of abm labels and primary/secondary keys containing a list of TUS
        codes, e.g.:

        {'Home': {'primary': [1], 'secondary': [11,12,13,14]},
         'Other Work': {'primary': [2]}}

        The resulting function takes two arguments, namely the TUS primary
        and secondary codes, as ints.  It returns one of the keys
        from the mapping given to _this_ function.
        """


        # Compute primary and secondary together.
        mapping_pri = {}
        mapping_sec = {}
        for abm_code, v in map_config.items():
            primary   = v['primary']   or [] if 'primary'   in v else []
            secondary = v['secondary'] or [] if 'secondary' in v else []

            for p in primary:
                mapping_pri[p] = ActivityType[abm_code].value
            for s in secondary:
                mapping_sec[s] = ActivityType[abm_code].value

        # Define mapping function, enclosing the above mapping
        def tus_activity_to_abm_activity(tus_pri, tus_sec):
            if tus_pri != 7:
                return mapping_pri[tus_pri]
            return mapping_sec[tus_sec]

        return tus_activity_to_abm_activity



    def parse_days(tus, map_func):
        """
        Returns a list of DiaryDay functions built from the TUS data provided.

        The following piece of code constructs the daily routines. This takes into account the fact that diaries
        appearing in the TUS do not all start at the same time and do not all run for 24 hours. This is
        achieved by first extending the duration of the last activity, to create a 24 hour routine, after which
        the piece of the routine extending beyong the end of the day is repositioned to the start of the
        day. This way, all routines cover a 24 hour period running from midnight to midnight.

        Parameters:
            tus (pandas dataframe):The TUS dataset loaded from excel
            map_func (function):A function taking two ints and returning
                                the activity code for this row.

        Returns:
            days(list):A list of DiaryDay objects.
        """

        days = []
        for date in tqdm(tus['id_jour'].unique()):
            tus_date  = tus.loc[tus['id_jour'] == date]
            durations = [y-x for x, y in list(zip(tus_date['heuredebmin'], tus_date['heuredebmin'][1:]))]

            end_activity = map_func(tus_date.iloc[-1]['loc1_num_f'], tus_date.iloc[-1]['act1b_f'])
            start_time = tus_date.iloc[0]['heuredebmin']

            # Build variables for object
            identity, age, day, weight = [tus_date.iloc[0][x] for x in ['id_ind', 'age', 'jours_f', 'poids_ind']]
            daily_routine = [end_activity] * start_time \
                          + utils.flatten([[map_func(tus_date.iloc[i]['loc1_num_f'], tus_date.iloc[i]['act1b_f'])] * d
                                      for i, d in enumerate(durations)]) \
                          + [end_activity] * (DAY_LENGTH_10MIN - sum(durations) - start_time)

            # Create the list entry
            day = DiaryDay(identity, age, day, weight, daily_routine)
            days.append(day)

        return days


    map_func = get_tus_code_mapping(config['activities'], activity_manager.map_class)
    days     = parse_days(tus, map_func)
    print(f"Created {len(days)} days")

    # print('\n'.join([''.join([d[0] for d in days[x].daily_routine]) for x in range(len(days))]))
    #For each respondent there are now two daily routines; one for a week day and one for a weekend day. 
    #Copies of these routines are now concatenated so as to produce weekly routines, starting on Sunday.

    # ---------------------------------------------------------------------------------------------------
    print('Generating weekly routines...')

    def create_weekly_routines(days):
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
        """

        weeks = []
        for i in range(0, len(days)-1, 2):

            # Make a bold assumption
            weekend, weekday = days[i], days[i+1]

            # Swap if we were wrong
            if weekday.day in [DayOfWeek.SUNDAY, DayOfWeek.SATURDAY]:
                weekday, weekend = weekend, weekday

            # Check the identity is the same
            assert(weekday.identity == weekend.identity)

            # Create a week with most things the same, but with a whole week's worth of activities
            week = DiaryWeek(weekday.identity, weekday.age, weekday.weight,
                             weekend.daily_routine + weekday.daily_routine * 5 + weekend.daily_routine)
            weeks.append(week)

        return weeks


    weeks = create_weekly_routines(days)
    print(f"Created {len(weeks)} weeks")

    # ---------------------------------------------------------------------------------------------------
    #Now the statistical weights are used to construct the intial distributions and transition matrices:
    print('Generating weighted initial distributions...')

    # Weights for how many of each type of agent is performing each type of action
    # AgentType.CHILD: {Home: 23,
    #                   Other Work: 12},
    # AgentType.ADULT: {action: weight,
    #                   action2: weight2},
    #
    init_distribution_by_type = {typ: {activity: 0 for activity in activity_manager.types_as_int}
                       for typ in POPULATION_RANGES.keys()}
    for week in weeks:
        for typ, rng in POPULATION_RANGES.items():
            if week.age in rng:
                init_distribution_by_type[typ][week.weekly_routine[0]] += week.weight

    initial_distributions_filename = osp.join(config.filepath('working_dir', True), INITIAL_DISTRIBUTIONS_FILENAME)
    print(f"Writing initial distributions to {initial_distributions_filename}...")
    with open(initial_distributions_filename, 'wb') as fout:
        pickle.dump(init_distribution_by_type, fout)
    del(init_distribution_by_type)


    print('Generating weighted activity transition matrices...')
    # Activity -> activity transition matrix
    #
    # AgentType.CHILD: [[[activity, activity], [activity, activity]]]
    #
    #  - Each activity has a W[next activity]
    #  - Each 10 minute slice has a transition matrix between activities
    #  - Each agent type has one of those ^
    #

    # TODO: simplify this structure.  It's far too hard to follow
    transition_matrix = {typ:
                         [
                          {x: {y: 0 for y in activity_manager.types_as_int}
                           for x in activity_manager.types_as_int}
                          for _ in range(WEEK_LENGTH_10MIN)]
                         for typ in POPULATION_RANGES.keys()}

    # Do all but the last item, which should loop around
    for t in tqdm(range(WEEK_LENGTH_10MIN)):
        for week in weeks:
            for typ, rng in POPULATION_RANGES.items():
                if week.age in rng:

                    # Wrap around to zero to make the week
                    # one big loop
                    next_t = (t+1) % WEEK_LENGTH_10MIN

                    # Retrieve the activity transition
                    activity_from = week.weekly_routine[t]
                    activity_to   = week.weekly_routine[next_t]

                    transition_matrix[typ][t][activity_from][activity_to] += week.weight

    transition_matrix_filename = osp.join(config.filepath('working_dir', True), TRANSITION_MATRIX_FILENAME)
    print(f"Writing transition matrices to {transition_matrix_filename}...")
    with open(transition_matrix_filename, 'wb') as fout:
        pickle.dump(transition_matrix, fout)

    print('Done.')
