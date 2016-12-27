#!/usr/bin/env /usr/local/bin/python

# A simple cross-platform implementation of the Pushover Open Client
# API that invokes a user-specified program to process Pushover
# notifications that it receives.

# This program logs-in to pushover as a user-specified desktop device,
# deletes any pending messages for the device, and then waits for new
# messages. When a new message is received, this program invokes a
# separate user-specified external command (e.g., any script or
# executable) to process the message. It continues to wait for
# messages and process them until terminated via Ctl-c or kill
# command.

# See https://pushover.net/api/client for Pushover Open Client API
# details.

# In constrast to this program, a full-featured, open source Pushover
# cross-platform desktop notification client created by Christoph
# Gross is available here: https://github.com/cgrossde/Pullover.

# Tested with Python version 2.7.13 on Mac OS X.

# Optionally, this program can be run as an auto-(re-)started
# background daemon process. For Mac OS X, please see the included
# launchd LaunchAgents config as an example.

# This program enables Pushover control for X10 home automation using
# the "heyu" command but it's easy to to customize for another
# command. Simply modify the two functions below: initialize_command()
# and process_messages(). The former is intended to ensure the command
# environment is initialized prior to processing messages e.g., start
# background processes etc. The latter is intended to perform a task
# based on a Pushover message received as a command line argument.

# usage: pushover-control.py --help

# To invoke this program with an unregistered desktop device use the
# following command line. Pushover will return a device ID for the
# registered device. Be sure to record the ID, because it is needed
# for subsequent invocations (see invoceation below this one). Note
# that a desktop license for the registered device must be purchased
# from Pushover before the device's five day trial expires.

# ~/bin/pushover-control.py  --login_email=<your pushover login email> --login_pass=<your pushover password> --device_name=<your unregistered device name> --command_bin=<path to message processing command>

# To invoke this program with a registered desktop device use the
# following command line.

# ~/bin/pushover-control.py  --login_email=<your pushover login email> --login_pass=<your pushover password> --device_id=<your registered device ID> --command_bin=/usr/local/bin/heyu

import argparse
import json
import subprocess
import sys
import thread
import time
import urllib
import urllib2
import websocket

login_url = "https://api.pushover.net/1/users/login.json"
device_reg_url = "https://api.pushover.net/1/devices.json"
download_url = "https://api.pushover.net/1/messages.json"
delete_url_template = "https://api.pushover.net/1/devices/%s/update_highest_message.json" 
websocket_url = "wss://client.pushover.net/push"

# Globals
secret = None
ws = None
exit = True
device_id = None

def log_date():
    return time.strftime("%m/%d/%Y %H:%M:%S")

def log(log_string):
    sys.stdout.write("%s: %s\n" % (log_date(), log_string)) 
    sys.stdout.flush()

def try_pushover_post_request(url, form_data, error_string):
    form_params = urllib.urlencode(form_data)
    try:
        response = urllib2.urlopen(url, form_params)
        return ( True, json.load(response) )
    except urllib2.HTTPError, error:
        response_data = json.load(error)
        log(error_string)
        log(error)
        return ( False, response_data )
    except urllib2.URLError, error:
        log(error_string)
        log(error)
        return ( False, None )

def try_pushover_get_request(url, param_data, error_string):
    form_params = urllib.urlencode(param_data)
    try:
        response = urllib2.urlopen(url + '?' + form_params)
        return ( True, json.load(response) )
    except urllib2.HTTPError, error:
        response_data = json.load(error)
        log(error_string)
        log(error)
        return ( False, response_data )
    except urllib2.URLError, error:
        log(error_string)
        log(error)
        return ( False, None )

def try_login():
    global secret
    login_form_data = { 'email': args.login_email, 'password': args.login_pass }
    login_error_string = "Login error for: %s" % args.login_email
    ( status, login_response_data ) = try_pushover_post_request(login_url,
                                                                login_form_data,
                                                                login_error_string)
    if not status:
        # Exit normally to prevent launchd re-start.
        log("Exiting.")
        sys.exit(0)
    else:
        secret = login_response_data['secret']

def try_device_reg():
    global device_id
    device_reg_form_data = { 'secret': secret, 'name': args.device_name, 'os': 'O' }
    device_reg_error_string = "Device registration error for: %s" % args.device_name
    ( status, device_reg_response_data ) = try_pushover_post_request(device_reg_url, 
                                                                     device_reg_form_data,
                                                                     device_reg_error_string)
    if status:
        device_id = device_reg_response_data['id']
        log("Device ID for %s: %s" % ( args.device_name, device_id ))

def try_download():
    max_message_id = -1
    download_param_data = { 'secret': secret,
                            'device_id': device_id }
    download_error_string = "Outstanding messages download error"
    ( status, download_response_data ) = try_pushover_get_request(download_url,
                                                                  download_param_data,
                                                                  download_error_string)
    if status:
        messages = download_response_data['messages']
        for message in messages:
            if message['id'] > max_message_id:
                max_message_id = message['id']

    return ( max_message_id, messages )

def try_delete(max_message_id):
    if max_message_id > -1:
        delete_url = delete_url_template % device_id
        delete_form_data = { 'secret': secret, 'message': max_message_id }
        delete_error_string = "Error deleting messages"
        ( status, delete_response_data ) = try_pushover_post_request(delete_url,
                                                                     delete_form_data,
                                                                     delete_error_string)
        if status:
            log("Deleted device messages up to id: %s" % max_message_id)

def process_messages():
    ( max_message_id, messages ) = try_download()
    if max_message_id == -1:
        log("No messages downloaded.")
        return
    for message in messages:
        title = message['title']
        message = message['message']
        log("message title: %s" % title)
        log("message body: %s" % message)
        if title == 'heyu':
            # Parse message components and create command arguments.
            parsed_message = message.split()
            on_off = parsed_message[0]
            device = '_'.join(parsed_message[1:])
            log("command: %s %s" % (on_off, device))
            subprocess.call([ args.command_bin ] + [ on_off, device ], stderr=subprocess.STDOUT)
    try_delete(max_message_id)

def on_ws_message(ws, message):
    def run(*thread_args):
        global exit
        log("WS message: %s" % message)
        if message == '!':
            process_messages()
        elif message == 'R':
            exit = False
            ws.close()
        elif message == 'E':
            exit = True
            ws.close()
        elif message == '#':
            pass
        else:
            log("Unrecognized WS message: %s" % message)
    thread.start_new_thread(run, ())

def on_ws_error(ws, error):
    log("WS error: %s" % error)

def on_ws_close(ws):
    log("WS closed.")

def on_ws_open(ws):
    ws.send("login:%s:%s\n" % ( device_id, secret ))
    log("Sent WS credentials.")

def initialize_command():
    # Initialize command environment.
    subprocess.call([args.command_bin, 'start'], stderr=subprocess.STDOUT)

def initialize_pushover():
    global ws
    try_login()
    # If device not registered yet (no device ID provided on command
    # line), then register it using device_name provided on command
    # line.
    if args.device_name:
        try_device_reg()
    # Download and delete any pending messages.
    ( max_message_id, messages ) = try_download()
    try_delete(max_message_id)
    # Wait for new message and process them.
    ws = websocket.WebSocketApp(websocket_url,
                                on_message = on_ws_message,
                                on_error = on_ws_error,
                                on_close = on_ws_close)
    ws.on_open = on_ws_open

def initialize():
    log("Initializing.")
    initialize_command()
    initialize_pushover()

# mainline

parser = argparse.ArgumentParser()
parser.add_argument("--login_email", 
                    help="Pushover account login email address.",
                    required=True)
parser.add_argument("--login_pass",
                    help="Pushover account login password.",
                    required=True)
parser.add_argument("--command_bin",
                    help="Absolute path to executable command invoked in response to pushover notifications.",
                    required=True)
group = parser.add_mutually_exclusive_group()
group.add_argument("--device_name",
                    help="Pushover desktop client device name. Only required to register the device.")
group.add_argument("--device_id",
                    help="Pushover device ID assigned to desktop client device after device is registered.")
args = parser.parse_args()
if args.device_id:
    device_id = args.device_id

while True:
    initialize()
    ws.run_forever()
    if exit:
        break
    else:
        # Pause 10 seconds before trying to re-register.
        time.sleep(10)

log("Exiting.")
# Exit normally to prevent launchd auto-restart.
sys.exit(0)
