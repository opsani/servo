from __future__ import print_function    # py2 compatibility

from threading import Timer
import argparse
import json
import subprocess
import sys

class AdjustError(Exception):
    """base class for error exceptions defined by drivers.
    """

    def __init__(self, *args, status="failed", reason="unknown"):
        self.status = status
        self.reason = reason
        super().__init__(*args)

class Adjust(object):
    '''
    Base class for Optune adjust driver command. This implements common functionality
    and is meant to be sub-classed, not run as is.

    Example usage:
    from adjust import Adjust
    class MyClass(Adjust):
       def info(self):
           ...
       def query(self):
           ...
       def handle_cancel(self, signal, frame):
           ...
       def adjust(self, data):
           ...
    if __name__ == '__main__':
        foo = MyClass(VERSION, DESC, HAS_CANCEL, PROGRESS_INTERVAL)
        foo.run()

    '''
    ##################################################
    #     METHODS THAT SHOULD NOT BE OVERWRITTEN
    #      (unless you know what you are doing)
    ##################################################

    def __init__(self, version, cli_desc, supports_cancel, progress_interval=None):

        # Parse Args
        self.parser = argparse.ArgumentParser(description=cli_desc)

        self.parser.add_argument(
            '--version', help='print version and exit', default=False, action='store_true')
        self.parser.add_argument(
            '--info', help='output driver info and exit', default=False, action='store_true')
        qry_help = 'output current state of settings for this application'
        self.parser.add_argument(
            '--query', help=qry_help, default=False, action='store_true')
        # alias for query
        self.parser.add_argument(
            '--describe', dest='query', help=qry_help, default=False, action='store_true')
        self.parser.add_argument(
            'app_id', help='Name/ID of the application to adjust', nargs='?')
        self.args = self.parser.parse_args()

        self.version = version
        self.app_id = self.args.app_id
        self.supports_cancel = supports_cancel
        self.progress_interval = progress_interval
        self.progress = 0
        self.progress_message = None
        self.timer = None


    def run(self):
        if self.args.version:
            print(self.version)
            sys.exit(0)

        if self.args.info:
            print(json.dumps(
                {"version": self.version, "has_cancel": self.supports_cancel}))
            sys.exit(0)

        # Valcheck
        if self.args.app_id is None:
            self.parser.error(
                'Missing required param app_id')

        # Handle --query
        if self.args.query:
            try:
                query = self.query()
                if "application" not in query:
                    query = { "application" : query } # legacy compat.
                print(json.dumps(query))
                sys.exit(0)
            except AdjustError as e:
                self._print_json_error(
                    e.status,
                    e.reason,
                    str(e)
                )
                raise
            except Exception as e:
                self._print_json_error(
                    "failed", "unknown", cls=e.__class__.__name__, message=str(e)
                )
                raise

        # Parse input
        try:
            # self.debug("Reading stdin")
            try:
                input_data = json.loads(sys.stdin.read())
            except json.decoder.JSONDecodeError as e:
                raise Exception('Failed to read input descriptor on stdin -> ({}) {}'.format(e.__class__.__name__,
                                                                                       str(e)))
            self.input_data = input_data # LEGACY mode, remove when drivers are updated to use arg
        except Exception as e:
            self._print_json_error(
                "failed", "unknown",
                cls=e.__class__.__name__,
                message="failed to parse input:" + str(e)
            )
            raise

        # Start progress timer
        self.start_progress_timer()

        # Adjust // TODO: print output??
        try:
            c = self.adjust.__code__.co_argcount
            if c == 2:
                query = self.adjust(input_data)
            else:
                query = self.adjust() # LEGACY mode
            if not query: # for old drivers that return None
                query = {}
            # if the above didn't raise an exception, all done (empty completion data, status 'ok')
            if "status" not in query:
                query["status"] = "ok"
                query["reason"] = "success"
            print(json.dumps(query))
        except AdjustError as e:
            self._print_json_error(
                e.status,
                e.reason,
                str(e)
            )
            raise
        except Exception as e:
            self._print_json_error(
                "failed", "unknown",
                cls=e.__class__.__name__,
                message=str(e)
            )
            raise
        finally:
            self.stop_progress_timer()

    def stop_progress_timer(self):
        if self.timer:
            self.timer.cancel()

    def start_progress_timer(self):
        self.stop_progress_timer()

        if not self.progress_interval:
            return

        self.timer = Timer(self.progress_interval, self.print_progress)
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

        if msg_index is not None:
            data['msg_index'] = msg_index
        if stage is not None:
            data['stage'] = stage
        if stageprogress is not None:
            data['stageprogress'] = stageprogress

        print(json.dumps(data), flush=True)
        # Schedule the next progress update
        self.start_progress_timer()

    def debug(self, *message):
        print(*message, flush=True, file=sys.stderr)

    @staticmethod
    def print_json_error(error, cl, message):
        '''
        Prints JSON formatted error
        (exported backward-compatible method, new drivers should raise an exception dervided from AdjustError)
        '''
        Adjust._print_json_error("failed", "unknown", message, err=error, cls=cl)

    @staticmethod
    def _print_json_error(status, reason, message, err="failure", cls="AdjustError"):
        """Print JSON-formatted status message. Internal method for use in this file only. Subclasses should raise an exception dervied from AdjustError."""
        print(json.dumps(
            {
                "status": status,
                "reason": reason,
                "error": err, # used for backward-compatibility only
                "class": cls, # used for backward-compatibility only
                "message": message
            }), flush=True)

    ##################################################
    #     METHODS THAT MUST BE OVERWRITTEN
    ##################################################
    def query(self):
        '''
        '''
        raise Exception("Not implemented")

    def adjust(self, data = None):
        '''
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

    def encode_value_if_needed(self, name, cfg_setting_data, adjust_data):
        """
        Takes:
            * a setting name
            * setting data (as defined in the config)
            * adjust data for the component that setting belongs to (as provided
            in the adjust event)

        Returns the value for the setting. If the config for that setting
        specifies an encoder to be used, the returned value will be encoded by
        the encoder specified in the config
        """
        # If there is no encoder, return as is
        if not "encoder" in cfg_setting_data:
            return adjust_data[name]["value"]

        # Else, call the encoder
        import encoders.base as enc
        value, _ = enc.encode(cfg_setting_data["encoder"], adjust_data)
        return value

    def encode_describe_if_needed(self, name, data, value):
        """
        Takes:
            * a setting name
            * setting data (as defined in the config)
            * value (as returned by the underlying infrastructure)

        Returns a dict in the format { <setting_name> : { <setting_data> }},
        suitable for returning as a description. At the very minimun,
        <setting_data> will return the current "value". If the config for that
        setting specifies an encoder to be used, the returned "value" ( in
        <setting_data>) will be decoded by the encoder specified in the config.
        """

        # If there is no encoder, return description with the current value and
        # any other params defined for the setting
        if not "encoder" in data:
            s_data = {"value": value}
            for i in ["type", "min", "max", "step", "values", "unit"]:
                if i in data:
                    s_data[i] = data[i]

            return {name: s_data}

        # Else, call the encoder
        import encoders.base as enc
        return enc.describe(data["encoder"], value.split())


    def get_oco_settings(self, cfg_settings):
        """
        Takes a config section with settings (key-value pair, where key is the
        setting name and the value is the setting params, i.e. min/max/step,
        etc.) and returns the list of setting names. If any of the settings
        require an ecoder, they will be run through the encoder and the list of
        the underlying settings (as OCO expects/provides them) will be returned
        instead of the setting name in the config.
        """
        settings = []

        for s_name, s_data in cfg_settings.items():

            if "encoder" in s_data:
                settings.extend(s_data["encoder"]["settings"].keys())
            else:
                settings.append(s_name)

        return settings

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
