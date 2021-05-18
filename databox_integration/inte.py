"""
Integration between Datadog and Databox system. Sends datadog data to Databox system via API.
"""
from os import getenv
from time import sleep
from json import dumps, loads
from datetime import datetime, timedelta
from logging import getLogger, Logger
from sys import exit as sys_exit
from argparse import ArgumentParser
from base64 import b64encode
from requests import get, post
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError, ConnectionError as ComError
LOG: Logger = getLogger('inte')


def get_arguments():
    """
    Parse call arguments

    :return: arguments
    :rtype: Dict
    """
    parser = ArgumentParser()
    parser.add_argument("-Z", "--zendesk", dest="zendesk", action='store_true')
    parser.add_argument("-D", "--datadog", dest="datadog", action='store_true')
    parser.add_argument("-f", "--ids-file", dest="ids_file", type=str, default="id.txt")
    parser.add_argument("-i", "--datadog-api-key", dest="dd_api_key", type=str, default="API_KEY")
    parser.add_argument("-p", "--datadog-app-key", dest="dd_app_key", type=str, default="APP_KEY")
    parser.add_argument("-d", "--databox-token-databog", dest="dtd_token", type=str, default="DATABOX_TOKEN_DATADOG")
    parser.add_argument("-e", "--zendesk-email", dest="zen_email", type=str, default="ZEN_EMAIL")
    parser.add_argument("-t", "--zendesk-token", dest="zen_token", type=str, default="ZEN_TOKEN")
    parser.add_argument("-j", "--zendesk-json", dest="zen_json", type=str, default="zendesk.json")
    parser.add_argument("-o", "--databox-token-zendesk", dest="dtz_token", type=str, default="DATABOX_TOKEN_ZENDESK")
    return vars(parser.parse_args())


# DATADOG data
def get_slo_id(path):
    """
    Read file with slo_ids

    :param path: path to file
    :type path: str
    :return: list of ids
    :rtype: List[str]
    """
    result_id = list()
    try:
        with open(path) as ids:
            for line in ids:
                result_id.append(line.strip())
    except IOError as error:
        LOG.critical('Can\'t read file %s: %s', path, error)
        sys_exit(error)
    return result_id


def get_slo_value(api_key, app_key, slo_id, ts_from, ts_to):
    """
    Get slo value using slo_ids for given period

    :param api_key: api_key of datadog
    :type api_key: str
    :param app_key: app_key of datadog
    :type app_key: str
    :param slo_id: SLO ID
    :type slo_id: str
    :param ts_from: timestamp beginning of given period
    :type ts_from: int
    :param ts_to: timestamp end of given period
    :type ts_to: int
    :return: unique value for each slo_id and name's of slo_id's
    :rtype: Tuple
    """
    url = f"https://api.datadoghq.com/api/v1/slo/{slo_id}/history?from_ts={ts_from}&to_ts={ts_to}"
    LOG.debug('URL for datadog GET request: %s', url)
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key
    }
    try:
        req = get(url, headers=headers)
    except ComError as error:
        LOG.error('SLO with id %s GET error', slo_id)
        LOG.error('Could not connect to datadog: %s', error)
    except HTTPError as error:
        LOG.error('SLO with id %s GET error', slo_id)
        LOG.error(error)
    else:
        return (
            req.json()["data"]["overall"]["sli_value"],
            "$" + multireplace(req.json()["data"]["overall"]["name"].lower())
        )
    return 0, ""


def multireplace(string):
    """
    Multiple replaces in a given string

    :param string: string to replace in
    :type string: str
    :return: processed string
    :rtype: str
    """
    return string.replace(" ", "_").replace("[", "").replace("]", "")


def push_to_databox(post_data, databox_token):
    """
    Push data to databox

    :param post_data: data to push
    :type post_data: Dict
    :param databox_token: databox auth token
    :type databox_token: str
    :return: server response
    :rtype: Dict
    """
    url = "https://push.databox.com"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/vnd.databox.v2+json"
    }
    try:
        req = post(url, auth=HTTPBasicAuth(databox_token, ''),
                   data=dumps(post_data), headers=headers)
    except ComError as error:
        LOG.error('Could not connect to databox: %s', error)
    except HTTPError as error:
        LOG.error(error)
    else:
        return req.json()


def read_json(path):
    """
    Read file with json data

    :param path: path to file
    :type path: str
    :return: json condition dict
    :rtype: Dict
    """
    result = dict()
    try:
        with open(path) as json_file:
            result = loads(json_file.read())
    except ValueError as error:
        LOG.error("Json Error %s", error)
    except IOError as error:
        LOG.critical('Can\'t read file %s: %s', path, error)
        sys_exit(error)
    return result


def zendesk_preview(email, token, data):
    """
    Show zendesk preview

    :param email: zendesk email
    :type email: str
    :param token: zendesk token
    :type token: str
    :param data: data to push
    :type data: Dict
    :return: zendesk response
    :rtype: Dict
    """
    url = "https://thisisix.zendesk.com//api/v2/views/preview/count.json"
    LOG.debug('URL for datadog GET request: %s', url)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + b64encode(f"{email}/token:{token}".encode("ascii")).decode("ascii")
    }
    try:
        req = post(url, data=dumps(data), headers=headers)
    except ComError as error:
        LOG.error('Could not connect to zendesk: %s', error)
    except HTTPError as error:
        LOG.error(error)
    else:
        return req.json()
    return dict()


# TODO: JIRA SERVICE


def main():
    """
    Main function

    :return: exit code
    :rtype: int
    """
    args = get_arguments()
    api_key = getenv(args.get("dd_api_key"))
    app_key = getenv(args.get("dd_app_key"))
    zen_email = getenv(args.get("zen_email"))
    zen_token = getenv(args.get("zen_token"))
    databox_token_datadog = getenv(args.get("dtd_token"))
    databox_token_zendesk = getenv(args.get("dtz_token"))
    today = datetime.utcnow()
    post_data = dict()
    if args.get("datadog"):
        post_data["datadog"] = dict()
        post_data["datadog"]["data"] = list()
        ids = get_slo_id(args.get("ids_file"))
        week_ago = today - timedelta(days=7)
        for slo_id in ids:
            sli_value, sli_name = get_slo_value(
                api_key,
                app_key,
                slo_id,
                int(week_ago.timestamp()),
                int(today.timestamp())
            )
            post_data["datadog"]["data"].append({"date": today.strftime('%Y-%m-%d %H:%M:%S'), sli_name: sli_value})
    if args.get("zendesk"):
        post_data["zendesk"] = dict()
        post_data["zendesk"]["data"] = list()
        zendesk_data = read_json(args.get("zen_json"))
        zendesk_results = dict()
        for key in zendesk_data:
            response = dict()
            count = 0
            while not response.get("view_count", {}).get("fresh"):
                response = zendesk_preview(zen_email, zen_token, zendesk_data[key]["params"])
                if count < 3:
                    count += 1
                    sleep(1)
                else:
                    break
            if response:
                if zendesk_results.get(zendesk_data[key]["databox_name"]):
                    zendesk_results[zendesk_data[key]["databox_name"]] += response["view_count"]["value"]
                else:
                    zendesk_results[zendesk_data[key]["databox_name"]] = response["view_count"]["value"]
            else:
                LOG.error("Zendesk view %s failed", key)
        for key in zendesk_results:
            post_data["zendesk"]["data"].append({"date": today.strftime('%Y-%m-%d %H:%M:%S'), key: zendesk_results[key]})
    if args.get("datadog"):
        print(dumps(post_data["datadog"], indent=4))
        print(push_to_databox(post_data["datadog"], databox_token_datadog))
    if args.get("zendesk"):
        print(dumps(post_data["zendesk"], indent=4))
        print(push_to_databox(post_data["zendesk"], databox_token_zendesk))


if __name__ == "__main__":
    main()
