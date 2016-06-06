#!/usr/bin/env python

import json

from instack_undercloud import undercloud

descriptions = {}
for group, opts in undercloud.list_opts():
    for opt in opts:
        key = '%s_%s' % (group or 'DEFAULT', opt.name)
        descriptions[key] = opt.help
with open('opt-descriptions.json', 'w') as f:
    f.write(json.dumps(descriptions))
