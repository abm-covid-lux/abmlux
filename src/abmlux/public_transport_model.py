import os
import string
import datetime
from tqdm import tqdm
from collections import Counter

#Numbers need rescaling according to population, remember...

INPUT_DIRECTORY  = 'Data/opendata-20191104-20191214'

route_type = {
    'AVL':      'bus',
    'CFLBUS':   'bus',
    'RGTR':     'bus',
    'TIC':      'bus',
    'C':        'train',
    'LUTRAM':   'train'
}

carriage_decks = {
    'bus':      1,
    'train':    10
}

def route_operator(filename):

    ascii_letters = set(string.ascii_letters)

    for position in range(len(filename)):
            if (filename[position] not in ascii_letters):
                operator = filename[0:position]
                break
    return operator

def days_of_operation(code):

    if (code == '000000'):
        hexcode = 'FFFFFFFFFFFF'
    else:
        bitfeld = open(INPUT_DIRECTORY + '/bitfeld', 'r')
        for line in bitfeld:
            if(line[0:6] == code):
                hexcode = line[7:19]
        bitfeld.close()
    return str('{0:08b}'.format(int(hexcode, 16)))[2:-5]

def time_conversion(timecode):

    return int(timecode[1:3])*6+int(timecode[3:5])//10

class Timetable:

  def __init__(self, days_of_operation, departure_time, arrival_time, bus_or_train):
    self.days_of_operation = days_of_operation
    self.departure_time = departure_time
    self.arrival_time = arrival_time
    self.bus_or_train = bus_or_train
    
timetables = []

for filename in os.listdir(INPUT_DIRECTORY):
    if filename.endswith('.LIN'):
        file = open(INPUT_DIRECTORY + '/' + filename, 'r')
        for line in file:
            if(line[0:5]=='*A VE'):
                new_timetable = Timetable(days_of_operation(line[26:32]),line[34:39],line[41:46],route_type[route_operator(filename)])
                timetables.append(new_timetable)
        file.close()

dates_file = open(INPUT_DIRECTORY + '/eckdaten', 'r')
lines = dates_file.readlines()
start_date = datetime.datetime(int(lines[2][6:10]),int(lines[2][3:5]),int(lines[2][0:2]))
end_date = datetime.datetime(int(lines[3][6:10]),int(lines[3][3:5]),int(lines[3][0:2])) + datetime.timedelta(days=1)
starting_day = int(start_date.strftime('%w'))

day_numbers: dict = Counter()

for day in range((end_date - start_date).days):
    day_numbers[(start_date + datetime.timedelta(day)).strftime('%a')] += 1

number_of_week_days = day_numbers['Mon'] + day_numbers['Tue'] + day_numbers['Wed'] + day_numbers['Thu'] + day_numbers['Fri']
number_of_weekend_days = day_numbers['Sat'] + day_numbers['Sun']

week_day_counts = [0 for ten_min in range(144)]
weekend_day_counts = [0 for ten_min in range(144)]

for day in tqdm(range((end_date - start_date).days)):
    for ten_min in range(144):
        for timetable in timetables:
            if (timetable.days_of_operation[day] == '1'):
                if (time_conversion(timetable.departure_time) <= ten_min and time_conversion(timetable.arrival_time) >= ten_min):
                    if ((day+starting_day)%7 in {0,6}):
                        weekend_day_counts[ten_min] += carriage_decks[timetable.bus_or_train]
                    else:
                        week_day_counts[ten_min] += carriage_decks[timetable.bus_or_train]
                
mean_active_week_day = [int(counts / number_of_week_days) for counts in week_day_counts]
mean_active_weekend_day = [int(counts / number_of_weekend_days) for counts in weekend_day_counts]

print(mean_active_week_day)
print(mean_active_weekend_day)