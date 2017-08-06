import time
import datetime
from collections import namedtuple

from slackclient import SlackClient

# this 
UTC_TIMEZONE = datetime.timezone(datetime.timedelta(hours=0), name='UTC')
NZ_TIMEZONE = datetime.timezone(datetime.timedelta(hours=12), name='UTC+12')

# Definitions of internal data-types and functions to convert to them
Team = namedtuple('Team', ['id', 'name', 'domain', 'email_domain'])
Channel = namedtuple('Channel', ['id', 'name','creation_ts', 'creator_id', 'users'])
Message = namedtuple('Message', ['ts', 'type'])
Transaction = namedtuple('Transaction', ['sender', 'receiver', 'amount', 'ts'])

def message_obj_to_tuple(message):
    ''' Takes a message object from the official API,
        and returns a Message named tuple with only the
        type and timestamp information.
        Disregards user info to preserve the privacy'''
    # only simple user messages don't have a subtype
    if ('subtype' not in message):
        return Message(float(message['ts']), 'message')
    # these are the other two kinds of messages we are interested in
    elif message['subtype'] in ['file_comment', 'file_share']:
        return Message(float(message['ts']), message['subtype'])
    # otherwise return a None value: not a message
    return None

def channel_obj_to_tuple(channel):
    ''' Takes a channel object from the official API,
        and returns a Channel named tuple with only the
        id, name, creation time and creator_id information.
        Disregards user info to preserve the privacy'''
    return Channel(*(channel[key] for key in ['id', 'name','created','creator', 'num_members']))

# Other utilty functions
def count(message_list, mtype, start_time=0.1, end_time=None):
    ''' Return the appearances of a specific m(essage)type in the
        Message tuple list message_list between start_time and
        end_time. If either is not provided, counts in the whole list.'''
    if end_time is None:
        return sum([1 for m in message_list if m.type == mtype and m.ts >= start_time])
    return sum([1 for m in message_list if m.type == mtype and m.ts >= start_time and m.ts < end_time])

def set_months_back(date, months=1):
    ''' Returns the datetime object with the same day
        but months number of months previously.
    '''
    original_day, curr = int(date.day), date
    one_day = datetime.timedelta(days=1)
    for _ in range(abs(months)):
        curr = curr.replace(day=1) # go to the first of the month
        curr -= one_day            # go back one day to the last day of the previous month
    can_restore_day = curr.day >= original_day
    return curr.replace(day=original_day) if can_restore_day else curr


# Class definitions

class Client(SlackClient):
    ''' An enhanced version of the official Slack API client.
        This class defines basic functionalities for a python slack client.
        It has a custom API cal method that automatically checks for success.
        It saves information about the channels and the team.
        It saves the least amount of personal data about the users,
        although of course one can call the official APIs with it,
        with which one can get much more data.
    '''
    
    def __init__(self, token_path):
        token = self.get_token(token_path)
        super().__init__(token)
        assert self.api_call("api.test")['ok'] and self.api_call("auth.test")['ok'], 'Something wrong with the token'
        team = self.api_call("team.info")['team']
        self.team = Team(team['id'], team['name'], team['domain'], team['email_domain'])
        self.channels = [channel_obj_to_tuple(chan) for chan in self.get_channels_list()]
        self.users = self.get_users_number()
        print('Client succesfully connected to {} slack.'.format(self.team.name))
        
    def __repr__(self):
        return 'Client for {} slack'.format(self.team.name)
    
    def get_token(self, token_path):
        ''' Attempts to read token from file'''
        try:
            with open(token_path,'r') as f:
                return f.read()
        except IOError as e:
            print('There seems something wrong with the file address:')
            print(e)
    
    def api_call(self, api_string, **kwargs):
        ''' Does the standard API call, checks if ok, then returns the rest
            of the dictionnary. If it fails, it prints the error on screen'''
        call = super().api_call(api_string, **kwargs)
        if call['ok']: return call
        else:
            print('\n\nSomething went wrong:', call['error'])
            return None
            
    def display_team_info(self):
        num_users = self.get_users_number()
        num_channels = len(self.channels)
        mess = 'The {} slack has {} users in {} channels'
        print(mess.format(self.team.name, self.users, num_channels))
    
    def get_channels_list(self):
        ''' Returns a list of channel objects for this team,
            as provided by the official API'''
        return self.api_call('channels.list')['channels']
    
    def get_users_number(self):
        ''' Returns the integer number of users'''
        return len(self.api_call('users.list')['members'])
    
    def channel_ids(self):
        ''' Returns a list of all the channel ids'''
        return [chan.id for chan in self.channels]
    
    def user_dict(self):
        ''' Returns a dictionary whose keys are user ids
            and values are the current corresponding username 
        '''
        return {usr['id']: usr['name'] for usr in self.api_call('users.list')['members']}
    
class HistoryClient(Client):
    ''' This client class inherits all the functionalities of the
        custom client class Client, and has additional methods to retrieve
        and store data about message histories in the slack channel.
    '''
    
    def __init__(self, token_path, timezone=UTC_TIMEZONE):
        super().__init__(token_path)
        self.timezone = timezone
        # Variables to be filled by method calls:
        self.histories = None           # list of lists of Message tuples of the channel at the same index in self.channels
        self.message_history = None     # dictionnary: key is channel id, value is the correpsonding list in self.histories
        self.channels_info = None       # list of dictionnaires containing coarse info about each channel
        self.daily_dates = None         # list of string dates for each day in the past 3 months
        self.message_timeseries = None  # dictionnary: key is channel name, value is a list of number of messages per day
    
    def __repr__(self):
        return 'HistoryClient for {} slack, {} timezone.'.format(self.team.name, self.tz.tzname())
    
    def get_channel_message_history(self, channel_id, start_ts=1.0):
        ''' Returns a list of Message(timestamp, type) tuples available from a given channel.
            Set start_ts to a different time to get only messages younger than that.          
        '''
        history = []
        oldest = start_ts
        # with the current arguments, the API returns the 1000 messages
        # closest to the value of oldest.  Until call['has_more'] is True,
        # we have to keep calling the API.
        while True:
            call = self.api_call('channels.history', channel=channel_id, oldest=oldest, count=1000)
            new = [message_obj_to_tuple(message) for message in call['messages']]
            history = [m for sublist in [new, history] for m in sublist if m is not None]
            if not call['has_more']: break
            try:
                oldest = call['latest']
            except:
                break
        return history
    
    def get_message_history(self, start_ts=1.0):
        ''' Returns a list of dictionaries, the keys being the channel_ids and the 
            values being the returns of the get_channel_message_history method.
            Set start_ts to a different time to get only messages younger than that.
        '''
        histories = []
        total = len(self.channels)
        start = time.time()
        for current, chan_id in enumerate(self.channel_ids()):
            loop_start = time.time()
            line = "Getting info for channel {:5} of {:5} {:6.0f}s"
            line = line.format(current+1, total, time.time()-start)
            print(line, end='')
            histories.append(self.get_channel_message_history(chan_id, start_ts=start_ts))
            time.sleep(max(1-time.time()+loop_start,0))
            print('\r', end='')
        else: print('\nFinished!')

        self.message_history ={ chan_id: history
                                   for chan_id, history in zip(self.channel_ids(), histories)}
        self.histories = histories

    
    def get_message_stats(self):
        ''' Returns a list of dictionaries'''
        now = datetime.datetime.now(tz=self.timezone)
        today = datetime.datetime(now.year, now.month, now.day, tzinfo=self.timezone)
        month = set_months_back(today, 1)
        six_months = set_months_back(today, 6)

        today, month, six_months = today.timestamp(), month.timestamp(), six_months.timestamp()

        if self.message_history is None:
            self.get_message_history()
        
        channels_info = []
        user_id_to_name = self.user_dict()
        for chan in self.channels:
            history = self.message_history[chan.id]
            channels_info.append(
                {'id': chan.id, 'name': chan.name,
                 'created': str(datetime.date.fromtimestamp(chan.creation_ts)),
                 'created_ts': chan.creation_ts,
                 'creator': user_id_to_name[chan.creator_id],
                 'members': chan.users,
                 'total_messages': count(history,'message'),
                 'total_files': count(history,'file_share'),
                 'total_file_comments': count(history,'file_comment'),
                 'messages_1month': count(history,'message', month),
                 'files_1month': count(history,'file_share', month),
                 'file_comments_1month': count(history,'file_comment', month),
                 'messages_6month': count(history,'message', six_months),
                 'files_6month': count(history,'file_share', six_months),
                 'file_comments_6month': count(history,'file_comment', six_months)
                }
            )
        self.channels_info = channels_info
        
        
    def get_message_timeseries(self):
        '''Returns a dictionary of lists'''
        now = datetime.datetime.now(tz=self.timezone)
        today = datetime.datetime(now.year, now.month, now.day, tzinfo=self.timezone)
        
        daily_dates = [today - i*datetime.timedelta(days=1) for i in range(31*3+1,1,-1)]
        daily_timestamps = [date.timestamp() for date in daily_dates]
        
        message_timeseries = {}
        for chan in self.channels:
            history = self.message_history[chan.id]
            timeseries = []
            for start, end in zip(daily_timestamps, daily_timestamps[1:]):
                timeseries.append(count(history, 'message', start_time=start, end_time=end))
            message_timeseries[chan.name] = timeseries
        
        self.message_timeseries = message_timeseries
        self.daily_dates = [str(day.date()) for day in daily_dates[:-1]]