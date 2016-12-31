# pushover-control.py

A simple cross-platform implementation of the Pushover Open Client
API that invokes a user-specified program to process Pushover
notifications that it receives.

This program logs-in to pushover as a user-specified desktop device,
deletes any pending messages for the device, and then waits for new
messages. When a new message is received, this program invokes a
separate user-specified external command (e.g., any script or
executable) to process the message. It continues to wait for
messages and process them until terminated via Ctl-c or kill
command.

See https://pushover.net/api/client for Pushover Open Client API
details.

In constrast to this program, a full-featured, open source Pushover
cross-platform desktop notification client created by Christoph
Gross is available here: https://github.com/cgrossde/Pullover.

Tested with Python version 2.7.13 on Mac OS X.

Optionally, this program can be run as an auto-(re-)started
background daemon process. For Mac OS X, please see the included
launchd LaunchAgents config as an example.

This program enables Pushover control for X10 home automation using
the "heyu" command but it's easy to to customize for another
command. Simply modify the two functions below: initialize_command()
and process_messages(). The former is intended to ensure the command
environment is initialized prior to processing messages e.g., start
background processes etc. The latter is intended to perform a task
based on a Pushover message received as a command line argument.

usage: pushover-control.py --help

To invoke this program with an unregistered desktop device use the
following command line. Pushover will return a device ID for the
registered device. Be sure to record the ID, because it is needed
for subsequent invocations (see invocation below this one). Note
that a desktop license for the registered device must be purchased
from Pushover before the device's five day trial expires.

~/bin/pushover-control.py  --login_email=[your pushover login email] --login_pass=[your pushover password] --device_name=[your unregistered device name] --command_bin=[path to message processing command]

To invoke this program with a registered desktop device use the
following command line.

~/bin/pushover-control.py  --login_email=[your pushover login email] --login_pass=[your pushover password] --device_id=[your registered device ID] --command_bin=[path to message processing command]

