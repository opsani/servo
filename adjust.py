from __future__ import print_function    # py2 compatibility

import json
import argparse
import sys


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
       def adjust(self):
           ...
    if __name__ == '__main__':
        foo = MyClass(VERSION, DESC, HAS_CANCEL)
        foo.run()

    '''
    ##################################################
    #     METHODS THAT SHOULD NOT BE OVERWRITTEN
    #      (unless you know what you are doing)
    ##################################################

    def __init__(self, version, cli_desc, supports_cancel):

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
            except Exception as e:
                self.print_json_error(
                    e.__class__.__name__,
                    "failure",
                    str(e)
                )
                raise

        # Parse input
        try:
            # self.debug("Reading stdin")
            input_data = json.loads(sys.stdin.read())
            self.input_data = input_data # LEGACY mode, remove when drivers are updated to use arg
        except Exception as e:
            self.print_json_error(
                e.__class__.__name__,
                "failed to parse input",
                str(e)
            )
            raise

        # Adjust // TODO: print output??
        try:
            c = self.adjust.__code__.co_argcount
            if c == 2:
                self.adjust(input_data)
            else:
                self.adjust() # LEGACY mode
            # if the above didn't raise an exception, all done (empty completion data, status 'ok')
            print(json.dumps(dict(status='ok')))
        except Exception as e:
            self.print_json_error(
                e.__class__.__name__,
                "failure",
                str(e)
            )
            raise

    def debug(self, *message):
        print(*message, flush=True, file=sys.stderr)

    def print_json_error(self, error, cl, message):
        '''
        Prints JSON formatted error
        '''
        print(json.dumps(
            {
                "error": error,
                "class": cl,
                "message": message
            }), flush=True)

    ##################################################
    #     METHODS THAT MUST BE OVERWRITTEN
    ##################################################
    def query(self):
        '''
        '''
        raise Exception("Not implemented")

    def adjust(self):
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
