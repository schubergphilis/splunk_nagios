#!/usr/bin/env python
#
# Copyright 2014, Schuberg Philis B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# check_splunk_cluster.py
#
# Nagios plugin to the the health of a Splunk cluster via the REST API
# cluster/master/info:
#	Check maintenance mode: WARN if true
#	Check indexing_ready_flag:
#		1 = OK
#		not 1 = CRITICAL
#
#cluster/master/peers:
#	Check peer status:
#		Up = OK
#		Down = CRITICAL
#		Other states: WARNING
#	Return stats: pending_job_count
#
#
#cluster/master/generation
#	Check "search_factor_met"
#		1 = OK
#		not 1 = CRITICAL
#		
#	Check "replication_factor_met"
#		1 = OK
#		not 1 = CRITICAL
#
#messages
#	List must be empty
#		return messages to Nagios (and assert at least WARNING status)
#
#
#licenser/messages
#	Check all messages:
#		INFO/WARN => WARNING
#		ERROR => CRITICAL
#	Return messages (description) to Nagios
#
#licenser/pools
#	per pool (calculate used_bytes/effective_quota)*100%
#		if % > 90
#			Usage warning
#	return stats: license pool usage
#
# This check must be run against the splunkd port (default 8089) on the 
# cluster master

import urllib2
import json
import sys
import time
from nagios import Nagios
from ConfigParser import ConfigParser

class SplunkCluster(object):

   endpoints = [
      {
         "end_point" : "messages",
         "checks" : [ 
            "_cluster_messages" 
         ]
      },
      {
         "end_point" : "cluster/master/info",
         "checks" : [ 
            "_check_maintenance_mode", 
            "_check_indexing_ready", 
         ]
      },
      {
         "end_point" : "cluster/master/peers",
         "checks" : [
            "_check_peer_status",
            "_get_pending_job_count"
         ]
      },
      {
         "end_point" : "cluster/master/generation",
         "checks" : [
            "_is_search_factor_met",
            "_is_replication_factor_met"
         ]
      },
      {
         "end_point" : "licenser/messages",
         "checks" : [
            "_check_licensing_messages"
         ]
      },
      {
         "end_point" : "licenser/pools",
         "checks" : [
            "_check_license_pool_usage"
         ]
      },

   ]

   def __init__(self, baseurl, username, password,nagios):
      self.baseurl = baseurl
      passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
      passwd_mgr.add_password(None,baseurl, username, password)
      self.http_client = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passwd_mgr))
      self.nagios = nagios

   def _load_json(self,endpoint):
      return json.loads(self.http_client.open(self.baseurl+endpoint+"?output_mode=json").read())

   def run_checks(self):
      for checker in self.endpoints:
         json = self._load_json(checker["end_point"])
         for check in checker["checks"]:
            self.__getattribute__(check)(json)

   # Check functions
   def _cluster_messages(self,json):
      for message in json["entry"]:
         m=message["content"]
         self.nagios.AppendStatus("Splunk system message %s: %s" % (m["severity"],m["message"]))
         self.nagios.SetExitCode("WARNING")

   def _check_maintenance_mode(self,json):
      maint_mode = json["entry"][0]["content"]["maintenance_mode"]
      if maint_mode:
         self.nagios.AppendStatus("Cluster is in maintenance mode.")
         self.nagios.SetExitCode("WARNING")

   def _check_indexing_ready(self,json):
      idx_rdy = json["entry"][0]["content"]["indexing_ready_flag"]
      if not idx_rdy:
         self.nagios.AppendStatus("Cluster is not able to index data")
         self.nagios.SetExitCode("CRITICAL")

   def _check_peer_status(self,json):
      for peer in json["entry"]:
         p = peer["content"]
         if p["status"] == "Up":
            pass # all is well with this peer
         elif p["status"] == "Down":
            self.nagios.AppendStatus("indexer %s is down" % ( p["label"]))
            self.nagios.SetExitCode("CRITICAL")
         else:
            self.nagios.AppendStatus("indexer %s has status %s" % (p["label"], p["status"]))
            self.nagios.SetExitCode("WARNING")

   def _get_pending_job_count(self,json):
      for peer in json["entry"]:
         p=peer["content"]
         self.nagios.AddPerfData( "jobcount_%s" % p["label"], p["pending_job_count"])

   def _is_search_factor_met(self,json):
      if int(json["entry"][0]["content"]["search_factor_met"]) != 1:
         self.nagios.AppendStatus("Cluster search factor not met")
         self.nagios.SetExitCode("CRITICAL")

   def _is_replication_factor_met(self,json):
      if int(json["entry"][0]["content"]["replication_factor_met"]) != 1:
         self.nagios.AppendStatus("Cluster replication factor not met")
         self.nagios.SetExitCode("CRITICAL")

   def _check_licensing_messages(self,json):
     
      now=int(time.time()) 

      for message in json["entry"]:
         m=message["content"]

         if m["description"].startswith("This pool has exceeded its configured poolsize") and \
            ( now - m["create_time"] ) < 3600:
            self.nagios.AppendStatus("Splunk licensing message ERROR: %s" % (m["description"]))
            self.nagios.SetExitCode("CRITICAL")
            break
         elif ( now - m["create_time"] ) < 3600*48:     
            self.nagios.AppendStatus("Splunk licensing message %s: %s" % (m["severity"],m["description"]))
            self.nagios.SetExitCode("WARNING")


   def _check_license_pool_usage(self,json):
      for lic_pool in json["entry"]:
         l = lic_pool["content"]
         try:
            usage_pct = int((l["used_bytes"] / l["effective_quota"])*100)
            self.nagios.AddPerfData("lic_pool_usage_%s" % l["description"], "%d%%" % usage_pct)
            if usage_pct > 90:
               self.nagios.SetExitCode("WARNING")
               self.nagios.AppendStatus("License pool %s usage is high = %d%%" % (l["description"], usage_pct))
         except ZeroDivisionError:
            pass



if __name__ == "__main__":

   nag = Nagios("CHECK_SPLUNK_CLUSTER")

   try: 
      cfg = ConfigParser()
      cfg.read(sys.argv[1])
      splunk = SplunkCluster( 
                    cfg.get("splunk","baseurl"),
                    cfg.get("splunk","username"),
                    cfg.get("splunk","password"),
                    nag
      )

   except:
      nag.SetStatus("Unable to get configuration data, usage: %s <cfg_file>"%(sys.argv[0]))
      nag.BuildResponseAndExit()

   nag.SetStatus("")
   nag.SetExitCode("OK")
   splunk.run_checks()
    
   nag.BuildResponseAndExit()
