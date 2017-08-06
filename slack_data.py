import sys
import csv
import datetime

from custom_slack_client import HistoryClient

TOKEN_PATH = 'slack_api_token.txt'
OVERVIEW_PATH =  'channel_data.csv'
TIMESERIES_PATH = 'timeseries.csv'


def save_dicts(dic_list, keys, filename):
    ''' Writes the info contained in a list of dictionnaries
        to a csv file, one line per dictionnary, one column per key.
        keys is a list of the keys whose values you want to save.
    '''
    with open(filename, 'w') as csv_file:
        dict_writer = csv.DictWriter(csv_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(dic_list)
        
def save_timeseries(header, timeseries, filename):
    ''' Save the timeseries results to a csv file
        the first row being the header, then one row per timeseries.
    '''
    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        for line in timeseries:
            writer.writerow(line)

def error_mess(m):
    message  = '\n---------------------\n'
    message += 'Error:\n'
    message +=  m+'\n'
    message += '---------------------\n\n'
    print(message)
        
def check_token_path():
    try:
        with open(TOKEN_PATH, 'r') as file:
            token = file.read()
    except Exception as e:
        error_mess("Please check you have created a '{}' file in this folder.".format(TOKEN_PATH))
        raise e
    if token == '':
        error_mess("Please paste the slack API token in the '{}' file.".format(TOKEN_PATH))
        raise ValueError

def parse_timezone(arg):
    m = 'Please enter an integer between -12 and +12 as first argument.'
    try: h = int(arg)
    except:
        error_mess(m)
        raise ValueError
    else:
        if abs(h) > 12:
            error_mess(m)
            raise ValueError
    name = 'UTC'
    if h != 0:
        sign = '-' if h < 0 else '+'
        name += sign + str(abs(h))
    return datetime.timezone(datetime.timedelta(hours=h), name=name)

def parse_month(arg):
    m = 'Please enter a non-negative integer as second argument.'
    try: months = int(arg)
    except:
        error_mess(m)
        raise ValueError
    else:
        if months < 0 :
            error_mess(m)
            raise ValueError
    return months
               
def parse_sys_argv():
    args = sys.argv[1:]
    if len(args) < 1: return parse_timezone(0), None
    if len(args) < 2: return parse_timezone(args[0]), None
    else: return parse_timezone(args[0]), parse_month(args[1])
        
def main():
    
    check_token_path()
    
    timezone, months_back = parse_sys_argv()
    
    client = HistoryClient(TOKEN_PATH, timezone=timezone)
    client.display_team_info()
    print('Collecting data.... This can take a few minutes, see you later.')
    
    start_ts = 0.1
    if months_back is not None:
        start_ts = time.time() - months_back*60*60*24*30
    
    try:
        client.get_message_history(start_ts=start_ts)
        client.get_message_stats()
    except Exception as e:
        error_mess(str(e))
        raise e
    else:
        print('Data collection successful!')
        
        keys = ['id','name','created','created_ts', 'creator', 'members','total_messages','total_files',
                'total_file_comments',
                'messages_1month',
                'files_1month',
                'file_comments_1month',
                'messages_6month',
                'files_6month',
                'file_comments_6month']
        save_dicts(client.channels_info, keys, OVERVIEW_PATH)
        print("Channel data overview saved in '{}'".format(OVERVIEW_PATH))
        
        client.get_message_timeseries()     
        header = ['']+client.daily_dates
        lines = [[key]+value for key, value in client.message_timeseries.items()]
        save_timeseries(header, lines, TIMESERIES_PATH)
        print("Channel timeseries saved in '{}'".format(TIMESERIES_PATH))
    
    
if __name__ == '__main__':
    main()