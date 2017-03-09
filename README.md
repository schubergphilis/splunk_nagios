check_splunk_cluster
====================

Description
===========
A Nagios plugin to monitor the health of a clustered Splunk environment via the Splunk REST API.
This plugin works with Nagios and other monitoring systems which support the Nagios plugin API.

Features
========
* Relays Splunk cluster messages as warning or critical events to Nagios
* Checks if a cluster is ready to index data
* Checks if cluster search and replication factor are met
* Checks is all peers (indexers) are up
* Check license usage and alert on license violations
* Optionally specifiy a list of checks to be run (if not: all checks are performed)

Supports
========
* Linux (Tested on RHEL6, other distributions should work)
* Splunk 6 and Splunk 6.1, version 5 is likely to work, but not tested
* HTTP and HTTPS
* Python 2.6/2.7

Note: if you are running this code on systems I have not been able to try it on, please
add to the list above.

Note2: if you are trying to run this code on other systems and it doesn't work for you, feel free to contact me or open an issue for
this repo.

Getting Started
===============
* Make sure you have Python 2.5 or greater installed (tested with python 2.6)
* Download check_splunk_cluster.py and nagios.py and place them inside a directory on your splunk cluster master
* Copy check.cfg.example to check.cfg on your cluster master and edit the credentials used to authenticate against the REST API.
* On your cluster master, run "python ./check_splunk_cluster.py check.cfg" to validate your configuration
* Start using check_splunk_cluster.py either manually, from Nagios or any another monitoring system you like.

Adding the check to Nagios
==========================
* Install the nrpe daemon on your Splunk cluster master node
* Add "command[check_splunk_cluster]=python /<path>/check_splunk_cluster.py /<path>/check.cfg" to your nrpe configuration, where <path>
  is replaced with the absolute path where you have the scripts installed
* Add the following command to your Nagios server config:
```
       define command {
         command_name check_splunk_cluster
         command_line $USER1$/check_nrpe -H $HOSTADDRESS$ -c check_splunk_cluster
       }
```
* For every cluster you manage, add a service to your Nagios configuration like so:
```
       define service {
         use default-service
        
           check_command check_splunk_cluster
           host_name <insert-host-name-for-your-cluster-master-here>
           service_description check_splunk_cluster
       }
```
* Restart your Nagios server and validate if the new check is working for you!

Alternative with selected checks
================================

If you want to have the different performed as single check rather than have all tests in one Nagios check,
you can specify a comma-separated list of checks as second argument. Example call:
python check_splunk_cluster.py check.cfg cluster/master/info,licenser/pools

This will perform only the check cluster/master/into and licenser/pools
