"""
Change Slack user emails
"""
from json import dumps
from requests import get, post, Timeout, TooManyRedirects, RequestException
TOKEN = ''
SLACK_API_URL = 'https://slack.com/api'
 
 
# --------------------------------------------------------------------------------------------------
def create_list():
    """
   Create list of users (name,id,email)
   """
    result = list()
    def slack_get(url, shift=None):
        user_emails = list()
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
                user_emails = [(x['id'], x['profile']['email']) 
                              for x in result['members'] if x['profile'].get('email')]
        return user_emails, next_cursor
 
    url = f'{SLACK_API_URL}/users.list?token={TOKEN}&limit=1000'
    emails, shift = slack_get(url)
    result += emails
    while shift:
        emails, shift = slack_get(url, shift)
        result += emails
    return result
 
# --------------------------------------------------------------------------------------------------
def change_user_email(user_id, new_email):
    """
   POST request to rename user
   """
    data = {
        "email": new_email
    }
    url = f'{SLACK_API_URL}/users.profile.set?token={TOKEN}&user={user_id}&profile={dumps(data)}'
    try:
        response = post(url)
        print(response.status_code)
        print(response.text)
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
    data = create_list()
    for user in data:
        if user[1].endswith('omnigon.com'):
            new_email = user[1].rstrip('omnigon.com') + 'ix.co'
            print(f'{user[1]} -> {new_email}') # juss output with no action
            #change_user_email(user[0], new_email) # uncomment in order to take action

 
 
if __name__ == '__main__':
    main()
