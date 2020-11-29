import datetime
import itertools
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

import config


def main(event, context):
    padel_arenas = {'UTK': '145',
                    'Padelcenter Fyrislund': '105'}

    combinations_to_query = itertools.product(padel_arenas.values(), get_future_dates(3))

    dfs = []
    for i in combinations_to_query:
        print(i)

        dfs.append(get_available_slots_from_combo(i))
        sleep(1)

    df_with_all_results = pd.concat(dfs)

    df_with_all_results['interesting_time'] = df_with_all_results.apply(lambda x: check_for_interesting_slots(x), axis=1)

    df_with_all_results_only_matches = df_with_all_results[df_with_all_results['interesting_time'] == 'Yes']

    if df_with_all_results_only_matches.shape[0] > 0:
        messages = []
        for index, row in df_with_all_results_only_matches.iterrows():
            messages.append("Available slot! \nArena: {} \nCourt: {} \nTime: {} - {}".format(
                get_key(padel_arenas, row['arena']), row['court'], row['start_time'], row['end_time']))

        for message in messages:
            send_sms(message)
    else:
        print("No slot available")


def get_future_dates(num_in_future):
    date_list = []
    for i in range(num_in_future):
        date = datetime.date.today() + datetime.timedelta(days=i+1)
        date_list.append(str(date))

    return date_list


def get_available_slots_from_combo(arena_and_date_tuple):

    url = 'https://www.matchi.se/book/schedule?facilityId={}&date={}&sport=5&indoor=true&wl='.format(arena_and_date_tuple[0], arena_and_date_tuple[1])
    page = requests.get(url)

    if page.status_code == requests.codes.ok:

        soup = BeautifulSoup(page.content, 'html.parser')

        schedule = soup.find("table", {"class": "table-bordered daily"})

        available_slots = []

        for finding in schedule.findAll("td", {"class": "slot free"}):
            available_slots.append(finding['title'])

        arenas = []
        statuses = []
        courts = []
        time_ranges = []
        start_times = []
        end_times = []
        durations = []

        df_input = {'status': statuses,
                    'court': courts,
                    'time': time_ranges,
                    'start_time': start_times,
                    'end_time': end_times,
                    'duration': durations,
                    'arena': arenas}

        for available_slot in available_slots:
            statuses.append(available_slot.split('<br>')[0])
            courts.append(available_slot.split('<br>')[1])

            time_range = available_slot.split('<br>')[2]
            start_time = time_range.split('-')[0].strip()
            end_time = time_range.split('-')[1].strip()

            start_time_as_timeobject = datetime.datetime.strptime(str(arena_and_date_tuple[1]) + ' ' + start_time, '%Y-%m-%d %H:%M')
            end_time_as_timeobject = datetime.datetime.strptime(str(arena_and_date_tuple[1]) + ' ' + end_time, '%Y-%m-%d %H:%M')

            slot_range = end_time_as_timeobject - start_time_as_timeobject
            time_ranges.append(available_slot.split('<br>')[2])

            start_times.append(start_time_as_timeobject)
            end_times.append(end_time_as_timeobject)

            durations.append(slot_range)
            arenas.append(arena_and_date_tuple[0])

        df = pd.DataFrame(df_input).sort_values(by=['time'])

        return df


def check_for_interesting_slots(df_with_available_times):
    if df_with_available_times['start_time'].hour >= 18:
        if df_with_available_times['start_time'].hour <= 20:
            return 'Yes'
        else:
            return 'No'


def get_key(dict_name, val_to_check_for_key):
    for key, value in dict_name.items():
        if val_to_check_for_key == value:
            return key


def send_sms(message):
    response = requests.post(
      'https://api.46elks.com/a1/sms',
      auth=(config.API_USERNAME, config.API_PASSWORD),
      data={
        'from': 'PythonElk',
        'to': config.to_phonenumber,
        'message': message
      }
    )


if __name__ == '__main__':
    main('', '')
