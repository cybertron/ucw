#!/bin/bash

if [ ! -d 'update-descriptions' ]
then
    virtualenv update-descriptions
fi
./update-descriptions/bin/pip install -U git+https://git.openstack.org/openstack/instack-undercloud
./update-descriptions/bin/python ./update-descriptions.py
