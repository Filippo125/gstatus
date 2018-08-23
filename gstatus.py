#!/usr/bin/env python
from __future__ import print_function
import json
from optparse import OptionParser  # command line option parsing
from datetime import datetime

import gstatus.gstatuscfg.config as cfg
from gstatus.libutils.utils import display_bytes, version_ok
from gstatus.libgluster.cluster import Cluster

DEBUG_INDENT = 2

def console_mode():
    """ Produce the output to the users console - stdout """

    if cluster.messages:
        status_msg = "%s(%d)" % (cluster.status.upper(), len(cluster.messages))
    else:
        status_msg = cluster.status.upper()

    # General Status Header
    print("     Product: %s  Capacity:%s(raw bricks)" % (cluster.product_shortname.ljust(17),
                                                          display_bytes(cluster.raw_capacity, display_units).rjust(11)))

    print("      Status: %s           %s(raw used)" % (status_msg.ljust(17),
                                                        display_bytes(cluster.used_capacity, display_units).rjust(11)))

    print("   Glusterfs: %s%s%s(usable from volumes)" % (cluster.glfs_version.ljust(17),
                                                          " " * 11,
                                                          display_bytes(cluster.usable_capacity, display_units).rjust(
                                                              11)))

    if cluster.snapshot_capable:
        snap_msg = "Snapshots: %s" % (str(cluster.snapshot_count).rjust(3))
    else:
        snap_msg = ""

    print("  OverCommit: %s%s%s" % (cluster.over_commit.ljust(3), " " * 15, snap_msg))

    # Component Status
    if state_request:
        print("\n   Nodes       :%3d/%3d\t\t  Volumes:  %2d Up"
               % (cluster.nodes_active, cluster.node_count,
                  cluster.volume_summary['up']))

        print("   Self Heal   :%3d/%3d\t\t            %2d Up(Degraded)"
               % (cluster.sh_active, cluster.sh_enabled,
                  cluster.volume_summary['degraded']))

        print("   Bricks      :%3d/%3d\t\t            %2d Up(Partial)"
               % (cluster.bricks_active, cluster.brick_count,
                  cluster.volume_summary['partial']))

        print("   Connections :%3d/%4d%s%2d Down" %
               (cluster.num_clients,
                cluster.num_connections,
                " " * 20,
                cluster.volume_summary['down']))

    # Volume Breakdown
    if volume_request:
        print("\nVolume Information")

        for vol_name in sorted(cluster.volume):

            if len(volume_list) == 0 or vol_name in volume_list:
                vol = cluster.volume[vol_name]
                (up_bricks, all_bricks) = vol.brick_states()

                task_list_str = ", ".join(vol.task_list) if vol.task_list else 'None'

                print("\t%s %s - %d/%d bricks up - %s"
                       % (vol_name.ljust(16, ' '),
                          vol.volume_state.upper(),
                          up_bricks, all_bricks,
                          vol.typeStr))

                print("\t" + " " * 17 +
                       "Capacity: (%d%% used) %s/%s (used/total)"
                       % (vol.pct_used,
                          display_bytes(vol.used_capacity, display_units),
                          display_bytes(vol.usable_capacity, display_units)))

                if cluster.snapshot_capable:
                    print("\t" + " " * 17 + "Snapshots: %d" % vol.snapshot_count)

                print("\t" + " " * 17 + "Self Heal: %s" % vol.self_heal_string)
                print("\t" + " " * 17 + "Tasks Active: %s" % task_list_str)
                print("\t" + " " * 17 + "Protocols: glusterfs:%s  NFS:%s  SMB:%s"
                       % (vol.protocol['NATIVE'],
                          vol.protocol['NFS'],
                          vol.protocol['SMB']))
                print("\t" + " " * 17 +
                       "Gluster Connectivty: %d hosts, %d tcp connections"
                       % (vol.num_clients,
                          vol.num_connections))

                if volume_layout:
                    print("")
                    vol.print_layout()

                print("")

    if state_request:
        print("\nStatus Messages")
        if cluster.messages:

            # Add the current cluster state as the first message to display
            cluster.messages.insert(0, "Cluster is %s" % cluster.status.upper())
            for info in cluster.messages:
                print("  - " + info)

        else:
            print( "  - Cluster is HEALTHY, all_bricks checks successful")

    print("")


def log_mode():
    """ produce the output suitable for later processing by logstash, 
        or splunk et al """
    if volume_request:
        volume_list_output = []
        for vol_name in sorted(cluster.volume):
            tmp_vol= {}
            if len(volume_list) == 0 or vol_name in volume_list:
                vol = cluster.volume[vol_name]
                (up_bricks, all_bricks) = vol.brick_states()
                task_list_str = ", ".join(vol.task_list) if vol.task_list else 'None'
                tmp_vol['name'] = vol_name
                tmp_vol['status'] = vol.volume_state.upper()
                tmp_vol['brick_count'] = vol.brick_total
                tmp_vol['all_bricks'] = all_bricks
                tmp_vol['volume_type'] = vol.typeStr
                tmp_vol['capacity_used'] = vol.used_capacity
                tmp_vol['capacity_usable'] = vol.usable_capacity
                tmp_vol['quota_ctrl'] = vol.quota_ctrl
                tmp_vol['quota_limit'] = vol.quota_limit

                tmp_vol['snapshot'] = { 'available': cluster.snapshot_capable,
                                        'count': vol.snapshot_count,
                                        'item': vol.snapshot_list }
                tmp_vol['tasks'] = vol.task_list
                tmp_vol['self_heal'] = { 'enabled': vol.self_heal_enabled, 
                                         'active': vol.self_heal_active }    
                
                tmp_vol['protocols'] = {'glusterfs': vol.protocol['NATIVE'], 
                                        'nfs': vol.protocol['NFS'], 
                                        'smb': vol.protocol['SMB'] }
                
                tmp_vol['connectivity'] = { 'hosts': vol.num_clients, 
                                            'tcp_conn': vol.num_connections }
                #print("\t" + " " * 17 + "Tasks Active: %s" % task_list_str)
                volume_list_output.append(tmp_vol)
        print(json.dumps(volume_list_output,indent=DEBUG_INDENT))
    elif state_request:
        general = { 'nodes_active': cluster.nodes_active,
                   'nodes_total': cluster.node_count,
                   'self_heal_active': cluster.sh_active,
                   'self_heal_total': cluster.sh_enabled,
                   'brick_active': cluster.bricks_active,
                   'brick_total': cluster.brick_count,
                    }

        volumes = { 'up': cluster.volume_summary['up'],
                    'degraded': cluster.volume_summary['degraded'],
                    'partial': cluster.volume_summary['partial'] } 
        connection = { 'clients': cluster.num_clients,
                        'connections': cluster.num_connections }            
        print(json.dumps({'general':general,'volumes':volumes,'connection':connection},indent=DEBUG_INDENT))
    else:
        now = datetime.now()
        print("%s %s" % (now, str(cluster)))


def main():
    if cluster.output_mode == 'console':
        # add some spacing to make the output stand out more
        print(" ")

        # setup up the cluster object structure
    cluster.initialise()

    # run additional commands to get current state
    cluster.update_state(self_heal_backlog)

    # use the bricks to determine overall cluster disk capacity
    cluster.calc_capacity()

    # perform checks on the clusters state
    cluster.health_checks()

    # Now with the object model complete, we can provide the info
    # to the user
    if cluster.output_mode == 'console':
        console_mode()

    elif cluster.output_mode in ['json', 'keyvalue']:
        log_mode()


if __name__ == '__main__':

    # initialise any global variables
    cfg.init()

    usageInfo = "usage: %prog [options]"

    parser = OptionParser(usage=usageInfo, version="%prog 0.66")
    parser.add_option("-s", "--state", dest="state", action="store_true", help="show highlevel health of the cluster")
    parser.add_option("-v", "--volume", dest="volumes", action="store_true",
                      help="volume info (default is ALL, or supply a volume name)")
    parser.add_option("-b", "--backlog", dest="selfheal", action="store_true", default=False,
                      help="Look deeper at self heal state (Use with -a)")
    parser.add_option("-a", "--all", dest="everything", action="store_true", default=False,
                      help="show all cluster information (-s with -v)")
    parser.add_option("-u", "--units", dest="units", choices=['bin', 'dec'],
                      help="display capacity units in DECimal or BINary format (GB vs GiB)")
    parser.add_option("-l", "--layout", dest="layout", action="store_true", default=False,
                      help="show brick layout when used with -v, or -a")
    parser.add_option("-o", "--output-mode", dest="output_mode", default='console',
                      choices=['console', 'json', 'keyvalue'],
                      help="produce output in different formats - json, keyvalue or console(default)")
    parser.add_option("-D", "--debug", dest="debug_on", action="store_true", help="turn on debug mode")
    parser.add_option("-w", "--without-progress", dest="progress", action="store_true", default=False,
                      help="turn off progress updates to user during data gathering")
    parser.add_option("-t", "--timeout", dest="timeout", help="gluster command timeout value (secs)")
    (options, args) = parser.parse_args()

    if options.timeout:
        cfg.CMD_TIMEOUT = int(options.timeout)

    cfg.debug = True if options.debug_on else False

    cfg.no_progress_msgs = options.progress

    state_request = options.state

    volume_request = options.volumes

    volume_layout = options.layout

    self_heal_backlog = options.selfheal

    display_units = options.units if options.units else 'bin'

    volume_list = []  # empty list of vols = show them all

    # default behaviours
    if volume_request and args:
        volume_list = args

    if state_request:
        self_heal_backlog = False

    if options.everything:
        state_request = True
        volume_request = True

    if options.output_mode != 'console':
        self_heal_backlog = False

    # Create a cluster object. This simply creates the structure of 
    # the object and populates the glusterfs version 
    cluster = Cluster()

    cluster.output_mode = options.output_mode

    if version_ok(cluster.glfs_version, cfg.min_version):

        main()

    else:

        print("gstatus is not compatible with this version of glusterfs %s" % cluster.glfs_version)
        exit(16)
