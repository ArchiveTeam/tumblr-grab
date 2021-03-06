# encoding=utf8
import datetime
from distutils.version import StrictVersion
import hashlib
import os.path
import random
from seesaw.config import realize, NumberConfigValue
from seesaw.externalprocess import ExternalProcess
from seesaw.item import ItemInterpolation, ItemValue
from seesaw.task import SimpleTask, LimitConcurrent
from seesaw.tracker import GetItemFromTracker, PrepareStatsForTracker, \
    UploadWithTracker, SendDoneToTracker
import shutil
import socket
import subprocess
import sys
import time
import string
from threading import Lock

import seesaw
from seesaw.externalprocess import WgetDownload
from seesaw.pipeline import Pipeline
from seesaw.project import Project
from seesaw.util import find_executable
import json
import re

from tornado import httpclient

http_client = httpclient.HTTPClient()

# check the seesaw version
if StrictVersion(seesaw.__version__) < StrictVersion('0.8.5'):
    raise Exception('This pipeline needs seesaw version 0.8.5 or higher.')


###########################################################################
# Find a useful Wget+Lua executable.
#
# WGET_LUA will be set to the first path that
# 1. does not crash with --version, and
# 2. prints the required version string
WGET_LUA = find_executable(
    'Wget+Lua',
    ['GNU Wget 1.14.lua.20130523-9a5c', 'GNU Wget 1.14.lua.20160530-955376b'],
    [
        './wget-lua',
        './wget-lua-warrior',
        './wget-lua-local',
        '../wget-lua',
        '../../wget-lua',
        '/home/warrior/wget-lua',
        '/usr/bin/wget-lua'
    ]
)

if not WGET_LUA:
    raise Exception('No usable Wget+Lua found.')


###########################################################################
# The version number of this pipeline definition.
#
# Update this each time you make a non-cosmetic change.
# It will be added to the WARC files and reported to the tracker.

VERSION = '20181223.01'
#USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
TRACKER_ID = 'tumblr'
TRACKER_HOST = 'tracker.archiveteam.org'

with open('uax.txt') as f:
    USER_AGENTS = list(filter(lambda x: not re.match('^(#.*)?$', x), map(lambda x: x.strip(), f.readlines())))

UAX = None
PFG = None
UAX_PFG_LOCK = Lock()

###########################################################################
# This section defines project-specific tasks.
#
# Simple tasks (tasks that do not need any concurrency) are based on the
# SimpleTask class and have a process(item) method that is called for
# each item.

class UAXandPFG(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, 'UAXandPFG')
        self._reuses = 0

    def process(self, item):
        global UAX, PFG
        with UAX_PFG_LOCK:
            TMPUAX = random.choice(USER_AGENTS)
            try:
                r = http_client.fetch(
                    'https://www.tumblr.com/privacy/consent?redirect=https%3A%2F%2Fstaff.tumblr.com%2F',
                    method = 'GET',
                    headers = {
                        'User-Agent': TMPUAX
                    },
                    follow_redirects = False,
                    allow_ipv6 = False
                )
            except httpclient.HTTPError as e:
                r = e.response
            if r.code != 200:
                if r.code == 303 and r.headers['location'] and (r.headers['location'] == '/' or r.headers['location'] == 'https://staff.tumblr.com/'):
                    item.log_output('No PFG/GDPR cookie needed')
                    PFG = None
                    UAX = TMPUAX
                    self._reuses = 0
                    return None
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            m = re.search('<meta name="tumblr-form-key" id="tumblr_form_key" content="(![0-9]{13}\|[a-zA-Z0-9]+)">', r.body.decode('utf-8', 'ignore'))
            if not m:
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            tumblr_form_key = m.group(1)
            postdata = {
                'eu_resident': True,
                'gdpr_is_acceptable_age': True,
                'gdpr_consent_core': True,
                'gdpr_consent_first_party_ads': True,
                'gdpr_consent_third_party_ads': True,
                'gdpr_consent_search_history': True,
                'redirect_to': 'https://staff.tumblr.com/',
                'gdpr_reconsent': False
            }
            try:
                r = http_client.fetch(
                    'https://www.tumblr.com/svc/privacy/consent',
                    method = 'POST',
                    headers = {
                        'User-Agent': TMPUAX,
                        'x-tumblr-form-key': tumblr_form_key,
                        'content-type': 'application/json',
                        'referer': 'https://www.tumblr.com/privacy/consent?redirect=https%3A%2F%2Fstaff.tumblr.com%2F'
                    },
                    body = json.dumps(postdata),
                    follow_redirects = False,
                    allow_ipv6 = False
                )
            except httpclient.HTTPError as e:
                r = e.response
            if r.code != 200:
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            if not r.headers['set-cookie']:
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            m = re.search('pfg=([^;]+)', r.headers['set-cookie'])
            if not m:
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            TMPPFG = m.group(1)
            if TMPPFG == "deleted":
                # special string returned by tumblr when request failed
                if PFG and self._reuses < 5:
                    item.log_output('I was unable to get a PFG token, reusing existing PFG token')
                    self._reuses += 1
                    return None
                item.log_output('I was unable to get a PFG token, giving up on this item')
                raise Exception('I was unable to get a PFG token, giving up on this item')
            PFG = TMPPFG
            UAX = TMPUAX
            self._reuses = 0

class CheckIP(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, 'CheckIP')
        self._counter = 0

    def process(self, item):
        # NEW for 2014! Check if we are behind firewall/proxy

        if self._counter <= 0:
            item.log_output('Checking IP address.')
            ip_set = set()

            ip_set.add(socket.gethostbyname('twitter.com'))
            ip_set.add(socket.gethostbyname('facebook.com'))
            ip_set.add(socket.gethostbyname('youtube.com'))
            ip_set.add(socket.gethostbyname('microsoft.com'))
            ip_set.add(socket.gethostbyname('icanhas.cheezburger.com'))
            ip_set.add(socket.gethostbyname('archiveteam.org'))

            if len(ip_set) != 6:
                item.log_output('Got IP addresses: {0}'.format(ip_set))
                item.log_output(
                    'Are you behind a firewall/proxy? That is a big no-no!')
                raise Exception(
                    'Are you behind a firewall/proxy? That is a big no-no!')

        # Check only occasionally
        if self._counter <= 0:
            self._counter = 10
        else:
            self._counter -= 1


class PrepareDirectories(SimpleTask):
    def __init__(self, warc_prefix):
        SimpleTask.__init__(self, 'PrepareDirectories')
        self.warc_prefix = warc_prefix

    def process(self, item):
        item_name = item['item_name']
        escaped_item_name = item_name.replace(':', '_').replace('/', '_').replace('~', '_')
        dirname = '/'.join((item['data_dir'], escaped_item_name))

        if os.path.isdir(dirname):
            shutil.rmtree(dirname)

        os.makedirs(dirname)

        item['item_dir'] = dirname
        item['warc_file_base'] = '%s-%s-%s' % (self.warc_prefix, escaped_item_name[:50],
            time.strftime('%Y%m%d-%H%M%S'))

        open('%(item_dir)s/%(warc_file_base)s.warc.gz' % item, 'w').close()
        open('%(item_dir)s/%(warc_file_base)s_data.txt' % item, 'w').close()
        open('%(item_dir)s/%(warc_file_base)s_media.txt' % item, 'w').close()


class MoveFiles(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, 'MoveFiles')

    def process(self, item):
        # NEW for 2014! Check if wget was compiled with zlib support
        if os.path.exists('%(item_dir)s/%(warc_file_base)s.warc' % item):
            raise Exception('Please compile wget with zlib support!')

        os.rename('%(item_dir)s/%(warc_file_base)s.warc.gz' % item,
              '%(data_dir)s/%(warc_file_base)s.warc.gz' % item)
        os.rename('%(item_dir)s/%(warc_file_base)s_data.txt' % item,
              '%(data_dir)s/%(warc_file_base)s_data.txt' % item)
        os.rename('%(item_dir)s/%(warc_file_base)s_media.txt' % item,
              '%(data_dir)s/%(warc_file_base)s_media.txt' % item)

        shutil.rmtree('%(item_dir)s' % item)


def get_hash(filename):
    with open(filename, 'rb') as in_file:
        return hashlib.sha1(in_file.read()).hexdigest()

CWD = os.getcwd()
PIPELINE_SHA1 = get_hash(os.path.join(CWD, 'pipeline.py'))
LUA_SHA1 = get_hash(os.path.join(CWD, 'tumblr.lua'))

def stats_id_function(item):
    # NEW for 2014! Some accountability hashes and stats.
    d = {
        'pipeline_hash': PIPELINE_SHA1,
        'lua_hash': LUA_SHA1,
        'python_version': sys.version,
    }

    return d


class WgetArgs(object):
    def realize(self, item):
        print('Running wget-lua with uax={} pfg={}'.format(UAX, PFG))
        wget_args = [
            WGET_LUA,
            '-U', UAX,
            '-nv',
            '--lua-script', 'tumblr.lua',
            '-o', ItemInterpolation('%(item_dir)s/wget.log'),
            '--no-check-certificate',
            '--output-document', ItemInterpolation('%(item_dir)s/wget.tmp'),
            '--truncate-output',
            '-e', 'robots=off',
            '--rotate-dns',
            '--recursive', '--level=inf',
            '--no-parent',
            '--page-requisites',
            '--timeout', '30',
            '--tries', 'inf',
            '--domains', 'tumblr.com',
            '--span-hosts',
            '--waitretry', '30',
            '--warc-file', ItemInterpolation('%(item_dir)s/%(warc_file_base)s'),
            '--warc-header', 'operator: Archive Team',
            '--warc-header', 'tumblr-dld-script-version: ' + VERSION,
            '--warc-header', ItemInterpolation('tumblr-blog: %(item_name)s')
        ]
        if PFG:
            wget_args.extend(['--header', 'Cookie: pfg={}'.format(PFG)])

        item_name = item['item_name']
        assert ':' in item_name
        item_type, item_value = item_name.split(':', 1)

        item['item_type'] = item_type
        item['item_value'] = item_value

        if item_type == 'tumblr-blog':
            split_items = item_value.split(':')
            for x in split_items:
                wget_args.extend(['--warc-header', 'tumblr-blog: ' + x])
                wget_args.append('http://{}.tumblr.com/'.format(x))
                wget_args.append('http://{}.tumblr.com/sitemap.xml'.format(x))
        else:
            raise Exception('Unknown item')

        if 'bind_address' in globals():
            wget_args.extend(['--bind-address', globals()['bind_address']])
            print('')
            print('*** Wget will bind address at {0} ***'.format(
                globals()['bind_address']))
            print('')

        return realize(wget_args, item)

###########################################################################
# Initialize the project.
#
# This will be shown in the warrior management panel. The logo should not
# be too big. The deadline is optional.
project = Project(
    title = 'Tumblr',
    project_html = '''
    <img class="project-logo" alt="logo" src="https://archiveteam.org/images/b/ba/Tumblr_on_white.png" height="50px"/>
    <h2>Tumblr <span class="links"><a href="https://www.tumblr.com/">Website</a> &middot; <a href="https://tracker.archiveteam.org/tumblr/">Leaderboard</a></span></h2>
    '''
)

pipeline = Pipeline(
    CheckIP(),
    UAXandPFG(),
    GetItemFromTracker('http://%s/%s' % (TRACKER_HOST, TRACKER_ID), downloader,
        VERSION),
    PrepareDirectories(warc_prefix='tumblr'),
    WgetDownload(
        WgetArgs(),
        max_tries=2,
        accept_on_exit_code=[0, 4, 8],
        env={
            'item_dir': ItemValue('item_dir'),
            'item_value': ItemValue('item_value'),
            'item_type': ItemValue('item_type'),
            'warc_file_base': ItemValue('warc_file_base'),
        }
    ),
    PrepareStatsForTracker(
        defaults={'downloader': downloader, 'version': VERSION},
        file_groups={
            'data': [
                ItemInterpolation('%(item_dir)s/%(warc_file_base)s.warc.gz')
            ]
        },
        id_function=stats_id_function,
    ),
    MoveFiles(),
    LimitConcurrent(NumberConfigValue(min=1, max=20, default='20',
        name='shared:rsync_threads', title='Rsync threads',
        description='The maximum number of concurrent uploads.'),
        UploadWithTracker(
            'http://%s/%s' % (TRACKER_HOST, TRACKER_ID),
            downloader=downloader,
            version=VERSION,
            files=[
                ItemInterpolation('%(data_dir)s/%(warc_file_base)s_data.txt'),
                ItemInterpolation('%(data_dir)s/%(warc_file_base)s_media.txt'),
                ItemInterpolation('%(data_dir)s/%(warc_file_base)s.warc.gz')
            ],
            rsync_target_source_path=ItemInterpolation('%(data_dir)s/'),
            rsync_extra_args=[
                '--recursive',
                '--partial',
                '--partial-dir', '.rsync-tmp',
            ]
        ),
    ),
    SendDoneToTracker(
        tracker_url='http://%s/%s' % (TRACKER_HOST, TRACKER_ID),
        stats=ItemValue('stats')
    )
)
