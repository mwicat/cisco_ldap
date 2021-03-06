import json
import pickle
import plac
import threading
import time

import sys; sys.path.insert(0, '../pycisco')

from collections import defaultdict

import phoneldap.webfe as webfe
import phoneldap.util as util
import phoneldap.ldaputil as ldaputil

DEFAULT_PORT = 5000
DEFAULT_UPDATE_SECS = 300


def parse_groups_from_all(l, config, users):
    d = defaultdict(list)
    for user in users:
        ou = user['ou']
        d[ou].append(user)
    return d

def load_dict(groups_file):
    return json.load(open(groups_file), encoding='utf-8') if groups_file is not None else {}

def merge_groups(group_base, group_custom):

    merged_groups_users = defaultdict(list)

    for group, users in group_custom.items():
        merged_groups_users[group].extend(users)

    for group, users in group_base.items():
        merged_group = merged_groups_users[group]
        merged_group.extend(users)
        merged_group.sort(key=lambda e: (e['lastName'], e['firstName']))
    return merged_groups_users


def paginate_groups(groups_users):
    groups_pages = {}
    for group, users in groups_users.items():
        groups_pages[group] = util.paginate_users(users)
    return groups_pages
    

def update_groups(app, groups_file, custom_groups_file, config):
    if groups_file is not None:
        groups_users = load_dict(groups_file)
    else:
        l = ldaputil.setup_ldap(config)
        all_ou_users = ldaputil.get_all_ou_users(l, config)
        groups_users = parse_groups_from_all(l, config, all_ou_users)

    custom_groups_users = load_dict(custom_groups_file)
    merged_groups_users = merge_groups(groups_users, custom_groups_users)

    groups_pages = paginate_groups(merged_groups_users)
    app.groups_pages = groups_pages


def run_update_loop(app, groups_file, custom_groups_file, config):
    while True:
        time.sleep(DEFAULT_UPDATE_SECS)
        update_groups(webfe.app, groups_file, custom_groups_file, config)
        print 'updating'
        
        

@plac.annotations(
   groups_file=('Groups file', 'option', 'g', str),
   custom_groups_file=('Custom groups file', 'option', 'c', str),
   config_path=('Config path', 'option', 'C', str),
   debug=('Debug mode', 'flag', 'd'),
   port=('Port', 'option', 'p', int)
   )
def run(groups_file=None, custom_groups_file=None, port=DEFAULT_PORT, config_path=None, debug=False):
    config = util.read_config(config_path)

    config = util.read_config(config_path)
    webfe.app.rc_config = config

    update_groups(webfe.app, groups_file, custom_groups_file, config)
    update_thread = threading.Thread(target=run_update_loop, args=(webfe.app, groups_file, custom_groups_file, config))
    update_thread.daemon = True
    update_thread.start()


    webfe.app.run(host='', port=port, debug=debug)

def main():
    plac.call(run)


if __name__ == '__main__':
    main()

        
