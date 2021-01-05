#!/usr/local/sal/Python.framework/Versions/Current/bin/python3
# Copyright 2019 Sal Opensource Project

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
import json
import os
import re
import subprocess
import sys
import pprint

import sal

sys.path.insert(0, "/usr/local/sal")
import yaml

PUPPET_LAST_RUN_SUMMARY = "/opt/puppetlabs/puppet/cache/state/last_run_report.yaml"

__version__ = "1.1.0"


def main():
    results = dict(facts={}, managed_items={})
    facts = get_facter_report()
    state_pref = sal.sal_pref("ReportPuppetState", True)
    if os.path.exists(PUPPET_LAST_RUN_SUMMARY):
        report_time, items = get_puppet_state()
        sal_facts = create_sal_facts(facts, items, report_time)
        facts.update(sal_facts)
        if state_pref:
            results["managed_items"] = items
    results["facts"] = facts
    sal.set_checkin_results("Puppet", results)


def get_puppet_state():
    yaml.add_multi_constructor("", default_ctor, Loader=yaml.SafeLoader)
    if not os.path.exists(PUPPET_LAST_RUN_SUMMARY):
        sys.exit(0)
    with open(PUPPET_LAST_RUN_SUMMARY, "r") as stream:
        data_loaded = yaml.safe_load(stream)

    items = {}
    report_time = data_loaded.get("time", None)
    for _, resource in iter(data_loaded.get("resource_statuses", {}).items()):
        if not resource.get("skipped", False) and not resource.get("failed", False):
            status = "PRESENT"
        else:
            status = "ERROR"
        items[resource.get("resource")] = {
            "date_managed": resource.get("time"),
            "status": status,
            "data": {"corrective_change": resource.get("corrective_change")},
        }
    return (report_time, items)


def create_sal_facts(facts, items, report_time):
    sal_facts = {}
    errors = [res for res in items.values() if res['status'] == 'ERROR']
    sal_facts['puppet_errors'] = len(errors)
    if report_time is not None:
        sal_facts['last_puppet_run'] = report_time
    return sal_facts


def default_ctor(loader, tag_suffix, node):
    # print loader
    # print tag_suffix
    # print node
    value = loader.construct_mapping(node)
    return value


def hashrocket_flatten_dict(input_dict):
    """Flattens the output from Facter 3"""

    result_dict = {}
    for fact_name, fact_value in input_dict.items():
        if type(fact_value) == dict:
            # Need to recurse at this point
            # pylint: disable=line-too-long
            for new_key, new_value in hashrocket_flatten_dict(fact_value).items():
                result_dict["=>".join([fact_name, new_key])] = new_value
        else:
            result_dict[fact_name] = fact_value
    return result_dict


def dict_clean(items):
    result = {}
    for key, value in items:
        if value is None:
            value = "None"
        result[key] = value

    return result


def get_facter_report():
    """Check for facter and sal-specific custom facts"""
    # Set the FACTERLIB environment variable if not already what we want
    facter = {}
    desired_facter = "/usr/local/sal/facter"
    current_facterlib = os.environ.get("FACTERLIB")
    facterflag = False
    if current_facterlib:
        if desired_facter not in current_facterlib:
            # set the flag to true, we need to put it back
            facterflag = True
    os.environ["FACTERLIB"] = desired_facter

    # if Facter is installed, perform a run
    facter_path = "/opt/puppetlabs/bin/puppet"
    if not os.path.exists(facter_path):
        return facter

    report = None
    command = [facter_path, "facts", "--render-as", "json"]
    if facter_path:
        try:
            report = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            return facter

    if report:
        try:
            facter = json.loads(report, object_pairs_hook=dict_clean)
        except:
            pass
    if "values" in facter:
        facter = facter["values"]

    if facterflag:
        # restore pre-run facterlib
        os.environ["FACTERLIB"] = current_facterlib
    facter["checkin_module_version"] = __version__
    return hashrocket_flatten_dict(facter)


if __name__ == "__main__":
    main()
