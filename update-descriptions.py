#!/usr/bin/env python

import json

from instack_undercloud import undercloud

descriptions = {}
for group, opts in undercloud.list_opts():
    new_descriptions = {}
    for opt in opts:
        new_descriptions[opt.name] = opt.help
    descriptions[group or 'DEFAULT'] = new_descriptions
with open('opt-descriptions.json', 'w') as f:
    f.write(json.dumps(descriptions))
