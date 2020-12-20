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

    df_with_all_results['interesting_time_user1'] = df_with_all_results.apply(lambda x: check_for_interesting_slots(x, 18, 20, 8, 20), axis=1)
    df_with_all_results['interesting_time_user2'] = df_with_all_results.apply(lambda x: check_for_interesting_slots(x, 19, 21, None, None), axis=1)
    df_with_all_results['interesting_time_user3'] = df_with_all_results.apply(lambda x: check_for_interesting_slots(x, 18, 20, 9, 20), axis=1)

    df_matches_user_1 = df_with_all_results[df_with_all_results['interesting_time_user1'] == 'Yes']
    df_matches_user_2 = df_with_all_results[df_with_all_results['interesting_time_user2'] == 'Yes']
    df_matches_user_3 = df_with_all_results[df_with_all_results['interesting_time_user3'] == 'Yes']

    user_1_messages = create_messages_for_matches(df_matches_user_1, padel_arenas)
    user_2_messages = create_messages_for_matches(df_matches_user_2, padel_arenas)
    user_3_messages = create_messages_for_matches(df_matches_user_3, padel_arenas)

    send_sms(user_1_messages, config.to_phonenumber_user1)
    send_sms(user_2_messages, config.to_phonenumber_user2)
    send_sms(user_3_messages, config.to_phonenumber_user3)


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

        if df.shape[0] > 0:
            df['dayofweek'] = df['start_time'].dt.dayofweek

        return df


def check_for_interesting_slots(df_input, min_start_hour_weekday, max_start_hour_weekday, min_start_hour_weekend, max_start_hour_weekend):
    if (min_start_hour_weekday is not None) & (df_input['dayofweek'] not in (5, 6)):
        if df_input['start_time'].hour >= min_start_hour_weekday:
            if df_input['start_time'].hour <= max_start_hour_weekday:
                return 'Yes'

    elif (min_start_hour_weekend is not None) & (df_input['dayofweek'] in (5, 6)):
        if df_input['start_time'].hour >= min_start_hour_weekend:
            if df_input['start_time'].hour <= max_start_hour_weekend:
                return 'Yes'


def get_key(dict_name, val_to_check_for_key):
    for key, value in dict_name.items():
        if val_to_check_for_key == value:
            return key


def send_sms(list_of_messages_to_send, user_phonenumber):

    if len(list_of_messages_to_send) > 0:
        for message in list_of_messages_to_send:
            response = requests.post(
              'https://api.46elks.com/a1/sms',
              auth=(config.API_USERNAME, config.API_PASSWORD),
              data={
                'from': 'PyPadler',
                'to': user_phonenumber,
                'message': message
              }
            )
        print(f"Message sent to {user_phonenumber}")
    else:
        print(f"No message for {user_phonenumber}")


def create_messages_for_matches(df, dictionary_with_padel_arenas):

    messages_to_send = []

    if df.shape[0] > 0:
        for index, row in df.iterrows():
            messages_to_send.append("Available slot! \nArena: {} \nCourt: {} \nTime: {} - {}".format(
                get_key(dictionary_with_padel_arenas, row['arena']), row['court'], row['start_time'], row['end_time']))

    return messages_to_send


if __name__ == '__main__':
    main('', '')
