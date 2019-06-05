#!/usr/bin/env python

# Upload files named on ARGV as Slack emoji.
# https://github.com/smashwilson/slack-emojinator

from __future__ import print_function

import argparse
import os
import re
import requests
import json
import time

try:
    raw_input
except NameError:
    raw_input = input


def _session(args):
    session = requests.session()
    session.url_add = "https://api.slack.com/api/emoji.add"
    session.url_list = "https://api.slack.com/api/emoji.list"
    session.api_token = args.token
    return session


def _argparse():
    parser = argparse.ArgumentParser(
        description='Bulk upload emoji to slack'
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
    if not args.token:
        args.token = raw_input('Please enter the token: ').strip()
    return args

def main():
    args = _argparse()
    session = _session(args)
    existing_emojis = get_current_emoji_list(session)
    uploaded = 0
    skipped = 0
    cancelled = 0
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
            result = 10
            while result > 0:
                if upload_emoji(session, emoji_name, filename):
                    result -= 1
                else:
                    break
            if result == 0:
                print("{} upload cancelled.".format(filename))
                cancelled += 1
            else:
                print("{} upload complete.".format(filename))
                uploaded += 1
    print('\nUploaded {} emojis. ({} already existed | {} cancelled)'.format(uploaded, skipped, cancelled))


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

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 429:
            print("Error with uploading %s: Server block us, will wait 100s." % emoji_name)
            time.sleep(100)
        else: 
            print(err)
            quit()
        return 1

    # Slack returns 200 OK even if upload fails, so check for status.
    response_json = r.json()
    if not response_json['ok']:
        print("Error with uploading %s: %s" % (emoji_name, response_json))
        return 1

    return 0


if __name__ == '__main__':
    main()
