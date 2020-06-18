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

import math
from tqdm import tqdm

import numpy as np
import pandas as pd
from tqdm import tqdm

from diary import DiaryDay, DiaryWeek
from config import load_config

INPUT_FILENAME      = 'Data/TUS_Processed_2.xlsx'
PARAMETERS_FILENAME = 'Data/network_parameters.yaml'

# ------------------------------------------------[ Config ]------------------------------------
print(f"Loading config from {PARAMETERS_FILENAME}...")
config = load_config(PARAMETERS_FILENAME)



# ---------------------------------------------------------------------------------------------------
print(f"Loading time use data from {INPUT_FILENAME}...")
tus = pd.read_excel(INPUT_FILENAME)
tus = tus.dropna()

# FIXME: remove this in favour of len(days)
day_count = len(tus['id_jour'].unique())



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


def get_tus_code_mapping(map_config):
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
            mapping_pri[p] = abm_code
        for s in secondary:
            mapping_sec[s] = abm_code

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

    # Iterate over pairs of rows
    start_time   = tus.iloc[0]['heuredebmin']
    current_day  = DiaryDay(tus.iloc[0]['id_ind'], tus.iloc[0]['age'], tus.iloc[0]['jours_f'], tus.iloc[0]['poids_ind'], [])
    current_date = tus.iloc[0]['id_jour']
    days         = [current_day]
    for i in tqdm(range(0, tus.shape[0]-1, 2)):
        row, row_next = tus.iloc[i], tus.iloc[i+1]

        time_now  = row['heuredebmin']
        time_next = row_next['heuredebmin']

        # If the day or individual changes, create a new day
        if current_date != row['id_jour']:

            identity, age, day, weight = [row[x] for x in ['id_ind', 'age', 'jours_f', 'poids_ind']]
            current_day = DiaryDay(identity, age, day, weight, [])
            days.append(current_day)
            current_date = row['id_jour']

            # TODO: remove magic number
            time_next = 144 + start_time

        # Add to routine
        activity = map_func(row['loc1_num_f'], row['act1b_f'])
        for j in range(time_next - time_now):
            # XXX: Note that this uses the same object over and over.  We can
            #      get away with it for now since activities are immutable strings anyway.
            current_day.daily_routine.append(activity)

    return days






map_func = get_tus_code_mapping(config['tus_activity_mapping'])
days     = parse_days(tus, map_func)
print(f"Created {len(days)} days")

#For each respondent there are now two daily routines; one for a week day and one for a weekend day. 
#Copies of these routines are now concatenated so as to produce weekly routines, starting on Sunday.


import code; code.interact(local=locals())

# ---------------------------------------------------------------------------------------------------
print('Generating weekly routines...')

def create_weekly_routines(days):
    # The format of the TUS data is such that each pair of daily diaries are listed consecutively,
    # so for each person there are two rows, e.g:
    #  - personA: weekend
    #  - personA: weekday
    #  - personB: weekend
    #  - personB: weekday
    # We don't know which way around these are, though.  This routine builds a week out of the
    # weekday, repeated, plus the weekend.
    weeks = []
    for i in range(0, len(days)-1, 2):

        # Make a bold assumption
        weekend, weekday = days[i], days[i+1]

        print(f"-> {weekend.identity} == {weekday.identity}")

        # Swap if we were wrong
        if weekday.day in [1,7]:
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

numberofindividuals = len(tus['id_ind'].unique())
Init_child = [0 for i in range(14)]
Init_adult = [0 for i in range(14)]
Init_retired = [0 for i in range(14)]

for s in tqdm(range(numberofindividuals)):
    if (weeks[s].age in range(10,18)):
        Init_child[weeks[s].weekly_routine[0]] = Init_child[weeks[s].weekly_routine[0]] + weeks[s].weight
    if (weeks[s].age in range(19,65)):
        Init_adult[weeks[s].weekly_routine[0]] = Init_adult[weeks[s].weekly_routine[0]] + weeks[s].weight
    if (weeks[s].age in range(65,76)):
        Init_retired[weeks[s].weekly_routine[0]] = Init_retired[weeks[s].weekly_routine[0]] + weeks[s].weight

np.savetxt('Initial_Distributions/Init_child.csv', Init_child, fmt='%i', delimiter=',')
np.savetxt('Initial_Distributions/Init_adult.csv', Init_adult, fmt='%i', delimiter=',')
np.savetxt('Initial_Distributions/Init_retired.csv', Init_retired, fmt='%i', delimiter=',')

print('Generating weighted transition matrices...')
Trans_child = [[[0 for i in range(14)] for j in range(14)] for t in range(7*144)]
Trans_adult = [[[0 for i in range(14)] for j in range(14)] for t in range(7*144)]
Trans_retired = [[[0 for i in range(14)] for j in range(14)] for t in range(7*144)]

#The transition matrices are now constructed, for all but the final ten minute interval:

for t in tqdm(range((7*144)-1)):
    for s in range(numberofindividuals):
        if (weeks[s].age in range(10,18)):
            Trans_child[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] = Trans_child[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] + weeks[s].weight
        if (weeks[s].age in range(19,65)):
            Trans_adult[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] = Trans_adult[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] + weeks[s].weight
        if (weeks[s].age in range(65,76)):
            Trans_retired[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] = Trans_retired[t][weeks[s].weekly_routine[t]][weeks[s].weekly_routine[t+1]] + weeks[s].weight
    np.savetxt('Transition_Matrices/Trans_child_' + str(t) + '.csv', Trans_child[t], fmt='%i', delimiter=',')
    np.savetxt('Transition_Matrices/Trans_adult_' + str(t) + '.csv', Trans_adult[t], fmt='%i', delimiter=',')
    np.savetxt('Transition_Matrices/Trans_retired_' + str(t) + '.csv', Trans_retired[t], fmt='%i', delimiter=',')

#The final transition matrix is constructed by looping the weekly routine back onto itself:
    
for s in tqdm(range(numberofindividuals)):
    if (weeks[s].age in range(10,18)):
        Trans_child[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] = Trans_child[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] + weeks[s].weight
    if (weeks[s].age in range(19,65)):
        Trans_adult[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] = Trans_adult[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] + weeks[s].weight
    if (weeks[s].age in range(65,76)):
        Trans_retired[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] = Trans_retired[(7*144)-1][weeks[s].weekly_routine[(7*144)-1]][weeks[s].weekly_routine[0]] + weeks[s].weight
np.savetxt('Transition_Matrices/Trans_child_' + str((7*144)-1) + '.csv', Trans_child[t], fmt='%i', delimiter=',')
np.savetxt('Transition_Matrices/Trans_adult_' + str((7*144)-1) + '.csv', Trans_adult[t], fmt='%i', delimiter=',')
np.savetxt('Transition_Matrices/Trans_retired_' + str((7*144)-1) + '.csv', Trans_retired[t], fmt='%i', delimiter=',')

print('Done.')
