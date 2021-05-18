"""
Batch rename of Slack channels
"""
from json import dumps
from re import fullmatch
from requests import get, post, Timeout, TooManyRedirects, RequestException
import sys
TOKEN = ''
SLACK_API_URL = 'https://slack.com/api'


# --------------------------------------------------------------------------------------------------
def create_list():
    """
    Create list of channels
    """
    result = list()

    def slack_get(url, shift=None):
        ch_list = list()
        if shift:
            url += f'&cursor={shift}'
        try:
            response = get(url)
        except Timeout:
            print('Connection timeout')
        except TooManyRedirects:
            print(f'Too many redirects. Check URL: {url}')
        except RequestException as error:
            print(f'{url}\n{error}')
        except ValueError as error:
            print(f'Malformed JSON: {error}')
        else:
            if response.status_code == 200:
                result = response.json()
                next_cursor = result['response_metadata']['next_cursor']
                ch_list = [(x['name'], x['id']) for x in result['channels']]
        return ch_list, next_cursor
    
    url = f'{SLACK_API_URL}/conversations.list?token={TOKEN}&exclude_archived=true&types=public_channel,private_channel&limit=1000'
    channels, shift = slack_get(url)
    result += channels
    while shift:
        channels, shift = slack_get(url, shift)
        result += channels
    return result


# --------------------------------------------------------------------------------------------------
def rename_channel(channel_id, new_name):
    """
    POST request to rename channel
    """
    url = f'{SLACK_API_URL}/channels.rename?token={TOKEN}&channel={channel_id}&name={new_name}'
    try:
        response = post(url)
    except Timeout:
        print('Connection timeout')
    except TooManyRedirects:
        print(f'Too many redirects. Check URL: {url}')
    except RequestException as error:
        print(f'{url}\n{error}')
    except ValueError as error:
        print(f'Malformed JSON: {error}')
    else:
        if response.status_code == 200:
            return True
    return False


# --------------------------------------------------------------------------------------------------
def main():
    """
    Main function
    """
    data = create_list()
    for channel in data:
        if fullmatch('^og-.*$', channel[0]):
            new_name = 'ix' + channel[0].lstrip('og')
            print(f'{channel[0]} -> {new_name}') # just output with no action
           #rename_channel(channel[1], new_name) # uncomment in order to take action



if __name__ == '__main__':
    main()
