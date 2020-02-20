# Base class for OCO measure command. This implements common functionality
# and is meant to be sub-classed, not run as is.
#
# Example usage:
#
# from measure import Measure
#
# class AB(Measure):
#    def describe(self):
#        ...
#
#    def handle_cancel(self, signal, frame):
#        ...
#
#    def measure(self):
#        ...
# if __name__ == '__main__':
#     ab = AB(VERSION, DESC, HAS_CANCEL, PROGRESS_INTERVAL)
#     ab.run()



from threading import Timer
import argparse
import json
import os
import signal
import subprocess
import sys
import time

ST_FAILED=500
ST_BAD_REQUEST=400

class Measure(object):
    ##################################################
    #     METHODS THAT SHOULD NOT BE OVERWRITTEN
    #      (unless you know what you are doing)
    ##################################################

    def __init__(self, version, cli_desc, supports_cancel, progress_interval=30):

        # Parse Args
        self.parser = argparse.ArgumentParser(description=cli_desc)

        self.parser.add_argument('--info', help='Don\'t measure, instead print driver info and exit', default=False, action='store_true')
        self.parser.add_argument('app_id', help='Name/ID of the application to measure', nargs='?')
        self.parser.add_argument('--describe', help='Don\'t measure, instead print a description of what can be measured for this application and exit', default=False, action='store_true')
        self.args = self.parser.parse_args()

        self.version = version
        self.app_id = self.args.app_id
        self.supports_cancel = supports_cancel
        self.progress_interval = progress_interval
        self.progress = 0
        self.progress_message = None
        self.timer = None


        # Valcheck
        if self.args.info and self.args.describe:
            self.parser.error('argument --info: not allowed with argument --describe')

    def print_measure_error(self, err, code=ST_FAILED):
        '''
        Prints JSON formatted error and exit
        Takes an error message as string
        '''
        out = {
            "status": code,
            "reason": err,
        }
        print(json.dumps(out), flush=True)


    def run(self):
        # Handle --info
        if self.args.info:
            out = {
                "has_cancel": self.supports_cancel,
                "version": self.version,
            }
            print(json.dumps(out), flush=True)
            sys.exit(0)

        # Valcheck
        if self.args.app_id is None:
            self.parser.error('the following arguments are required: app_id')

        # Handle --describe
        if self.args.describe:
            try:
                metrics = self.describe()
                out = {
                    "status": "ok",
                    "metrics": metrics,
                }
                print(json.dumps(out), flush=True)
                sys.exit(0)
            except Exception as e:
                self.print_measure_error(str(e))
                raise

        # Parse input
        try:
            self.debug("Reading stdin")
            self.input_data = json.loads(sys.stdin.read())
            # TODO: valcheck input
        except Exception as e:
            err = "failed to parse input: " + str(e)
            self.print_measure_error(err, ST_BAD_REQUEST)
            raise

        #print('MEASURE DRIVER: READ INPUT:', self.input_data) ##@#

        # Setup signal handlers
        if self.supports_cancel:
            signal.signal(signal.SIGUSR1, self.handle_cancel)

        # Start progress timer
        self.start_progress_timer()

        # Measure
        try:
            self.t_measure_start = time.time()
            metrics, annotations = self.measure()
            out = {
               "status": "ok",
               "metrics": metrics,
            }

            if annotations is not None:
                out["annotations"] = annotations

            print(json.dumps(out), flush=True)
        except Exception as e:
            self.print_measure_error(str(e), ST_FAILED)
            raise
        finally:
            self.stop_progress_timer()

    def stop_progress_timer(self):
        if self.timer:
            self.timer.cancel()

    def start_progress_timer(self):
        self.stop_progress_timer()
        self.timer = Timer(self.progress_interval, self.print_progress)
        self.timer.daemon = True # allow program to exit when main thread finishes
        self.timer.start()

    def print_progress(
            self,
            message=None,
            msg_index=None,
            stage=None,
            stageprogress=None):

        data = dict(
            progress=self.progress,
            message=message if (message is not None) else self.progress_message,
        )

        if msg_index is not None     : data['msg_index']     = msg_index
        if stage is not None         : data['stage']         = stage
        if stageprogress is not None : data['stageprogress'] = stageprogress

        print(json.dumps(data), flush=True)
        # Schedule the next progress update
        self.start_progress_timer()

    def debug(self, *message):
        print(*message, flush=True, file=sys.stderr)

    ##################################################
    #     METHODS THAT MUST BE OVERWRITTEN
    ##################################################

    def measure(self):
        '''
        Should return a tuple of two dicts: (metrics, annotations)

        "metrics": {
           "metric1_name": {    # all sub-elements except value are optional
              "value": 404859304, # value; may be number or string
              "unit": "rps", # optional, human/display targeted
              "annotation": "comment", # optional notes (e.g., how collected)
           },
        },
        "annotations": {
          # optional (string)key-value pairs with info, e.g., log/warnings, etc.
          # values may be strings (e.g., log message) or list of strings (log messages)
        }
        '''
        raise Exception("Not implemented")

    def describe(self):
        '''
        Should return metrics dict:
        "metrics": {
          "metric1_name": {    # all sub-elements are optional
             "index": 3,    # optional, display order index
             "cookie": "metric-cookie", # optional, to be provided on measure
             "min": 0,      # optional, min value, if known
             "max": 100,    # optional, max value, if known
             "weight": 1,   # optional, importance weight factor, if known

             "unit": "rps", # optional, human/display targeted
             "annotation": "comment", # optional notes (e.g., how collected)
          },
          ...
        }
        '''
        raise Exception("Not implemented")

    ##################################################
    #     METHODS THAT CAN BE OVERWRITTEN
    ##################################################
    def handle_cancel(self, signal, frame):
        '''
        Handles SIGUSR1 signal
        '''
        self.debug("Received cancel signal", signal)

    ##################################################
    #     HELPERS
    ##################################################

    # helper:  run a Bash shell command and raise an Exception on failure
    # note:  if cmd is a string, this supports shell pipes, environment variable
    # expansion, etc.  The burden of safety is entirely on the user.
    def _run_command(self, cmd, pre=True):
        cmd_type = 'Pre-command' if pre else 'Post-command'
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=True, executable='/bin/bash')
        msg = "cmd '{}', exit code {}, stdout {}, stderr {}".format(cmd,
                                                                    res.returncode, res.stdout, res.stderr)
        assert res.returncode == 0, '{} failed:  {}'.format(cmd_type, msg)
        self.debug('{}:  {}'.format(cmd_type, msg))

    # helper:  run a Bash shell command with stdout/stderr directed to /dev/null
    # and return the popen object
    def _run_command_async(self, cmd):
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, shell=True, executable='/bin/bash',
                                preexec_fn=os.setpgrp)
        self.debug('Pre-command async:  {}'.format(cmd))
        return proc

    # Kills a async process started by _run_command_async(). 'proc' is the
    # return value of _run_command_async()
    def _kill_async_cmd(self, proc):
        if proc is None: return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            self.debug("Failed to kill async cmd", e)
