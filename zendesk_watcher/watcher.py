#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack alerting for SLA breaching tickets
"""
from datetime import datetime, timedelta, timezone
import os
from json import dumps
from argparse import ArgumentParser
from logging import getLogger, basicConfig, INFO
from requests import post
from requests.exceptions import Timeout, TooManyRedirects, RequestException
from zenpy import Zenpy
basicConfig(level=INFO, format='%(asctime)s %(levelname)12s: %(message)s')
LOG = getLogger('slack-notify')
PICTURE = "https://i2.wp.com/4inim.ru/wp-content/uploads/2018/09/attention.png"


def send_message_to_slack(text, cfg):
    """
    Send message to slack channel

    :param text: text to send
    :type text: str
    :param cfg: config dict
    :type cfg: Dict
    """
    json_data = dumps(
        {
            'username': 'SLA Watcher',
            'attachments': [
                {
                    'fallback': 'High-Sev',
                    'color': '#ba0d1e',
                    'text': f'{text}',
                    'thumb_url': PICTURE
                }
            ]
        }
    )
    try:
        LOG.info("Sent message to tcss: %s", text)
        response = post(
            cfg['webhook'],
            data=json_data.encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 200:
            raise ValueError(
                f'Request to slack returned an error {response.status_code},'
                + f'the response is:\n{response.text}'
            )
    except Timeout:
        LOG.error('Request timed out')
    except TooManyRedirects:
        LOG.error('Request failed with too many redirects')
    except RequestException as err:
        LOG.error('Request failed: %s', err)


def sla_breach(ticket, cfg):
    """
    Determine if ticket breach SLA

    :param ticket: ticket dict
    :type ticket: Dict
    :param cfg: parameters dict
    :type cfg: Dict
    :return: breach type
    :rtype: int
    """
    status: int = 0
    severity = list(filter(
        lambda field: field['id'] == cfg['sev_field_id'],
        ticket.custom_fields
    ))[0]['value']
    last_update = datetime.strptime(ticket.updated_at, '%Y-%m-%dT%H:%M:%SZ')
    if (severity == 'sev_1') and (last_update <= cfg['two_hours_ago']):
        status = 1
    elif (severity == 'sev_2') and (last_update <= cfg['day_ago']):
        status = 2
    return status


def zd_link(zd_url):
    """
    URL replacement

    :param zd_url: API URL
    :return: HTTPS URL
    """
    return (zd_url.replace("api/v2/tickets", "hc/requests")).replace(".json", "")


def ticket_line(ticket, cfg):
    """
    Form text line with ticket info

    :param ticket: ticket dict
    :type ticket: Dict
    :param cfg: parameters dict
    :type cfg: Dict
    :return: String to send
    :rtype: str
    """
    severity = list(filter(
        lambda field: field['id'] == cfg['sev_field_id'],
        ticket.custom_fields
    ))[0]['value']
    org_name = 'Unknown org'
    if ticket.organization:
        org_name = ticket.organization.name
    line = ' | '.join(
        [
            str(ticket.id),
            ticket.subject,
            org_name,
            f"Updated: {ticket.updated_at}",
            f"Severity: {severity}",
            f"Link: {zd_link(ticket.url)}"
        ]
    )
    return line


def main():
    """
    Main function
    """
    cfg = {
        'two_hours_ago': (
                datetime.now(timezone.utc) - timedelta(hours=2)
        ).replace(tzinfo=None, microsecond=0),
        'day_ago': (
                datetime.now(timezone.utc) - timedelta(days=1)
        ).replace(tzinfo=None, microsecond=0),
        'email': os.environ.get('ZD_EMAIL'),
        'token': os.environ.get('ZD_TOKEN'),
        'webhook': os.environ.get('SLACK_WEBHOOK'),
        'subdomain': 'thisisix',
        'sev_field_id': 58614488
    }
    sev_1_list = []
    sev_2_list = []
    credentials = {
        'email': cfg['email'],
        'token': cfg['token'],
        'subdomain': cfg['subdomain']
    }
    search_criteria = {
        'status_less_than': 'pending',
        'type': 'ticket',
        'sort_by': 'created_at',
        'sort_order': 'desc',
        'group_id': '360015150233'
    }
    zenpy_client = Zenpy(**credentials)
    search_result = zenpy_client.search(**search_criteria)
    if search_result:
        for ticket in search_result:
            if high_sev := sla_breach(ticket, cfg):
                if high_sev == 1:
                    sev_1_list.append(ticket_line(ticket, cfg))
                elif high_sev == 2:
                    sev_2_list.append(ticket_line(ticket, cfg))
    if sev_1_list:
        LOG.info('%s SEV-1 tickets breached 2 hours SLA', len(sev_1_list))
        send_message_to_slack(
            "The list of open *SEV-1* incidents that have not been updated for 2 hours:",
            cfg
        )
        for i in sev_1_list:
            send_message_to_slack(i, cfg)
    if sev_2_list:
        LOG.info('%s SEV-2 tickets breached 1 day SLA', len(sev_2_list))
        send_message_to_slack(
            "The list of open *SEV-2* incidents that have not been updated for a day:",
            cfg
        )
        for i in sev_2_list:
            send_message_to_slack(i, cfg)
    if not (sev_1_list or sev_2_list):
        LOG.info("There are currently no open High-Severity tickets breaching SLA for updates")


if __name__ == "__main__":
    print(os.environ.get('SLACK_WEBHOOK'))
    main()
