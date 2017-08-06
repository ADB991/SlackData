# SlackData
## Collect slack channel usage data

Imagine getting an overview of all the channels in your team’s Slack, how many users are in each team and how many messages and files have been exchanged.

This is the aim of this python script. Using the official Slack APIs, it collects data about each channel and saves in just a few minutes.

### Output

At the moment, two csv files are created, which can be opened with a spreadsheet software like OpenOffice Calc, Microsoft Excel or Apple Numbers.

- *channel_data.csv* contains an overview of each channel in your slack: the date it was created, the username of the creator, the number of members, number of messages and files in the channel.

- Each line in *timeseries.csv* correspond to a channel, and each column to a day in the last 3 months. Each entry is the number of messages posted to the channel on that day.

More specific information to be found in *file_legends.txt*.

### Prerequisites

To run this script, you will need 4 things:
- Python3
- The official [Slack API client](https://github.com/slackapi/python-slackclient)
- A Slack API [testing token](https://api.slack.com/custom-integrations/legacy-tokens) for the desired channel
- The files in this repository

### Privacy

The official Slack implementation allows the token holder to access personal data of the members of the team, such as real names and email-addresses. Treat the token as a password ***Do not share your token with anyone***.
This programme accesses personal information but does not save it to disk; *with the exception of the username of the creators of the channels*. No data is being uploaded by the program.

### Usage

1. Paste your token in the *slack_api_token.txt* file.
2. In a bash window in the SlackData folder enter either of following commands:

        python3 slack_data.py
        python3 slack_data.py timezone       
        python3 slack_data.py timezone months

where:
- *timezone* is an integer from -12 to +12 representing the offset from UTC or GMT time. This is used to calculate the beginning of the day for the timeseries file. If not entered it will default to 0: your days will start at GMT.

- *months* a positive integer which will determine how far in the past will the script look for messages. If left blank, the process will look as far as possible. For free slacks, you can only access as far as 3 months in the past, but paid slack give access to the full history, in that case a limit like 3 months will make the call considerably faster.

For example, if you have a very busy slack in London, you would call:

        python3 slack_data.py 0 1

if you want to get as much info as you can, and you live in New Zealand, you would call:

        python3 slack_data.py 12

If you don’t want to scratch your head, you call:

        python3 slack_data.py


### Known Issues

This programme is slow. This is the nature of the API.
The programme will fail in certain occasions. Try to run it again and it may actually work.
Make sure you have good internet connection.

Hope it works for you!