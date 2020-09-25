# Puppet Checkin Module

This module will report on Puppet facts and (optionally) state to Sal.

## Disabling state reporting

You may have other reporting methods for Puppet state change, and if you are managing a large number of resources, the client submission may be large. To disable the reporting of state, set `ReportPuppetState` to `False` (boolean) on the `com.github.salopensource.sal` preference domain (the same as used for the rest of Sal).
