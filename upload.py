#!/usr/bin/env python

# Upload files named on ARGV as Slack emoji.
# https://github.com/smashwilson/slack-emojinator

from __future__ import print_function

import argparse
import os
import re
import requests
import json

try:
    raw_input
except NameError:
    raw_input = input

URL_ADD = "https://api.slack.com/api/emoji.add"
URL_LIST = "https://api.slack.com/api/emoji.list"


def _session(args):
    assert args.team_name, "Team name required"
    session = requests.session()
    session.url_add = URL_ADD.format(team_name=args.team_name)
    session.url_list = URL_LIST.format(team_name=args.team_name)
    session.api_token = args.token
    return session


def _argparse():
    parser = argparse.ArgumentParser(
        description='Bulk upload emoji to slack'
    )
    parser.add_argument(
        '--team-name', '-t',
        default=os.getenv('SLACK_TEAM'),
        help='Defaults to the $SLACK_TEAM environment variable.'
    )
    parser.add_argument(
        '--token',
        default=os.getenv('SLACK_TOKEN'),
        help='Defaults to the $SLACK_TOKEN environment variable.'
    )
    parser.add_argument(
        '--prefix', '-p',
        default=os.getenv('EMOJI_NAME_PREFIX', ''),
        help='Prefix to add to genereted emoji name. '
        'Defaults to the $EMOJI_NAME_PREFIX environment variable.'
    )
    parser.add_argument(
        '--suffix', '-s',
        default=os.getenv('EMOJI_NAME_SUFFIX', ''),
        help='Suffix to add to generated emoji name. '
        'Defaults to the $EMOJI_NAME_SUFFIX environment variable.'
    )
    parser.add_argument(
        'slackmoji_files',
        nargs='+',
        help=('Paths to slackmoji, e.g. if you '
              'unzipped http://cultofthepartyparrot.com/parrots.zip '
              'in your home dir, then use ~/parrots/*'),
    )
    args = parser.parse_args()
    if not args.team_name:
        args.team_name = raw_input('Please enter the team name: ').strip()
    if not args.token:
        args.token = raw_input('Please enter the token: ').strip()
    return args

def main():
    args = _argparse()
    session = _session(args)
    existing_emojis = get_current_emoji_list(session)
    uploaded = 0
    skipped = 0
    for filename in args.slackmoji_files:
        print("Processing {}.".format(filename))
        emoji_name = '{}{}{}'.format(
            args.prefix.strip(),
            os.path.splitext(os.path.basename(filename))[0],
            args.suffix.strip()
        )
        if emoji_name in existing_emojis:
            print("Skipping {}. Emoji already exists".format(emoji_name))
            skipped += 1
        else:
            upload_emoji(session, emoji_name, filename)
            print("{} upload complete.".format(filename))
            uploaded += 1
    print('\nUploaded {} emojis. ({} already existed)'.format(uploaded, skipped))


def get_current_emoji_list(session):
    response = requests.get(session.url_list + "?token=" + session.api_token)
    result = []
    if response.status_code != 200:
        return None
    else:
        for name, url in json.loads(response.content.decode('utf-8'))['emoji'].items():
            result.append(name)
        return result


def upload_emoji(session, emoji_name, filename):
    data = {
        'mode': 'data',
        'name': emoji_name,
        'token': session.api_token
    }
    files = {'image': open(filename, 'rb')}
    r = session.post(session.url_add, data=data, files=files, allow_redirects=False)
    r.raise_for_status()

    # Slack returns 200 OK even if upload fails, so check for status.
    response_json = r.json()
    if not response_json['ok']:
        print("Error with uploading %s: %s" % (emoji_name, response_json))


if __name__ == '__main__':
    main()
