import configparser
import itertools
from datetime import datetime, date, timedelta
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup


def main(event, context):
    padel_arenas = {'UTK': '145',
                    'UPC Fyrislund': '105',
                    'World Padel': '802'}

    combinations_to_query = itertools.product(
        padel_arenas.values(),
        get_future_dates(1))

    dfs = []
    for i in combinations_to_query:
        print(i)

        dfs.append(get_available_slots_from_combo(i))
        sleep(1)

    df_with_all_results = pd.concat(dfs)

    configs = load_config_file()
    all_users = [key for key in configs if key.startswith("user")]

    for user in all_users:
        user_message = get_message_for_user(
            df_with_all_results,
            user.split('_')[1],  # User id
            configs.get(user).get('min_start_hour_weekday', None),
            configs.get(user).get('max_start_hour_weekday', None),
            configs.get(user).get('min_start_hour_weekend', None),
            configs.get(user).get('max_start_hour_weekend', None),
            padel_arenas)

        if user_message:
            try:
                send_sms(
                    user_message,
                    configs.get(user).get('phonenumber'),
                    configs.get('api_username'),
                    configs.get('api_password'),
                    dryryn='no')

            except Exception as e:
                print(f"Failed to send message to {user}")
        else:
            print(f"No match for {user}")


def load_config_file():
    config_reader = configparser.ConfigParser()
    config_reader.read('pypadler.ini')

    configs = {
        'api_username': config_reader.get('46elks', 'API_USERNAME'),
        'api_password': config_reader.get('46elks', 'API_PASSWORD')}

    for user in config_reader.sections()[1:]:  # Skip first section in ini-file
        user_data = {
            'phonenumber': config_reader.get(user, 'phonenumber'),
            'min_start_hour_weekday': config_reader.get(user, 'min_start_hour_weekday', fallback=None),
            'max_start_hour_weekday': config_reader.get(user, 'max_start_hour_weekday', fallback=None),
            'min_start_hour_weekend': config_reader.get(user, 'min_start_hour_weekend', fallback=None),
            'max_start_hour_weekend': config_reader.get(user, 'max_start_hour_weekend', fallback=None)
            }

        configs[user] = user_data

    return configs


def get_message_for_user(
        df_all_results,
        user,
        min_start_hour_weekday,
        max_start_hour_weekday,
        min_start_hour_weekend,
        max_start_hour_weekend,
        padel_arenas_mapping):

    df_all_results[f'matching_slot_user_{user}'] = df_all_results.apply(
        lambda x: check_for_interesting_slots(
            x,
            min_start_hour_weekday,
            max_start_hour_weekday,
            min_start_hour_weekend,
            max_start_hour_weekend),
        axis=1)

    df_only_matches = df_all_results[df_all_results[f'matching_slot_user_{user}'] == 'Yes']

    message = create_messages_for_matches(
        df_only_matches,
        padel_arenas_mapping,
        user)

    return message


def get_future_dates(num_in_future):
    date_list = []
    for i in range(num_in_future):
        future_date = date.today() + timedelta(days=i+1)
        date_list.append(str(future_date))

    return date_list


def get_available_slots_from_combo(arena_and_date_tuple):

    url = f"https://www.matchi.se/book/schedule?facilityId={arena_and_date_tuple[0]}&date={arena_and_date_tuple[1]}&sport=5&indoor=true&wl="
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

            start_time_as_timeobject = datetime.strptime(
                str(arena_and_date_tuple[1]) +
                ' ' +
                start_time,
                '%Y-%m-%d %H:%M')
            end_time_as_timeobject = datetime.strptime(
                str(arena_and_date_tuple[1]) +
                ' ' +
                end_time,
                '%Y-%m-%d %H:%M')

            slot_range = end_time_as_timeobject - start_time_as_timeobject
            time_ranges.append(available_slot.split('<br>')[2])

            start_times.append(start_time_as_timeobject)
            end_times.append(end_time_as_timeobject)

            durations.append(slot_range)
            arenas.append(arena_and_date_tuple[0])

        df = pd.DataFrame(df_input).sort_values(by=['time'])

        if df.shape[0] > 0:
            df['dayofweek'] = df['start_time'].dt.dayofweek
            df['court'] = df['court'].str.lower()
            df['single_court'] = df['court'].str.contains('singel')
            df['today'] = pd.Timestamp.today()
            df['start_date'] = df['start_time'].dt.date

        return df


def check_for_interesting_slots(
        df_input,
        min_start_hour_weekday,
        max_start_hour_weekday,
        min_start_hour_weekend,
        max_start_hour_weekend):

    if (min_start_hour_weekday is not None) & (int(df_input['dayofweek']) not in (5, 6)):
        if df_input['start_time'].hour >= int(min_start_hour_weekday):
            if df_input['start_time'].hour <= int(max_start_hour_weekday):
                return 'Yes'

    elif (min_start_hour_weekend is not None) & (int(df_input['dayofweek']) in (5, 6)):
        if df_input['start_time'].hour >= int(min_start_hour_weekend):
            if df_input['start_time'].hour <= int(max_start_hour_weekend):
                return 'Yes'


def get_key(dict_name, val_to_check_for_key):
    for key, value in dict_name.items():
        if val_to_check_for_key == value:
            return key


def send_sms(message_to_send, user_phonenumber, api_username, api_pwd, dryryn='no'):
    try:
        response = requests.post(
          'https://api.46elks.com/a1/sms',
          auth=(api_username, api_pwd),
          data={
            'from': 'PyPadler',
            'to': user_phonenumber,
            'message': message_to_send,
            'dryrun': dryryn
          }
        )

        if response.ok:
            print(f"Message sent to {user_phonenumber} at a cost of {response.json()['estimated_cost']/100/100} SEK")
            print(f"Message characters: {len(message_to_send)} in {response.json()['parts']} part(s)")

    except Exception as e:
        print(e)


def create_messages_for_matches(df, dictionary_with_padel_arenas, user):

    user_matches = df[df[f'matching_slot_user_{user}'] == 'Yes']

    if user_matches.shape[0] > 0:
        user_matches_summarized = user_matches.groupby(
            ['start_date',
             'arena',
             'single_court',
             'time'])['court'].apply(list).reset_index()

        user_matches_summarized['arena'] = user_matches_summarized.apply(
            lambda x: get_key(
                dictionary_with_padel_arenas,
                x['arena']),
            axis=1)

        user_matches_summarized['court'] = user_matches_summarized.apply(
            lambda x: len(x['court']),
            axis=1)

        user_matches_summarized['single_court'] = user_matches_summarized['single_court'].map(
            {False: 'Double',
             True: 'Single'})

        user_matches_summarized.rename(
            columns={
                'start_date': 'date',
                'court': 'courts',
                'single_court': 'type'},
            inplace=True)

        user_matches_summarized['date'] = user_matches_summarized['date'].apply(
            lambda x: x.strftime('%Y-%m-%d'))

        message = 'Matching slot!\n'
        ending = f"\nQuestions, new accounts or contributions use +46730738491"

        for index, row in user_matches_summarized.iterrows():
            row = f"Date: {row['date']}\nArena: {row['arena']}\nType: {row['type']}\nTime: {row['time']}\nNum courts: {row['courts']}\n\n"
            message += row

        return message + ending


if __name__ == '__main__':
    main('', '')
