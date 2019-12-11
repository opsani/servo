#!/usr/bin/python3
from __future__ import print_function
"""
tester for 'adjust' drivers.

use:
   - change the directory to where the tested driver is located;
   - configure the environment for the driver under test, so that it has an
     available application named 'test' to access and can respond to:
     ./adjust --query test
     ./adjust test <settings_data
     (for most 'adjust' drivers, the setup will include as a minimum creating
     a file named app.yaml in the current directory)
   - run python3 /path/to/servo/test/test_adjust.py
"""

import sys
import os
import subprocess
import select
import time

import json
import copy

def warn(txt):
    print("WARNING:", txt, file=sys.stderr)

def validate_setting(s):
    """check one setting item in one of these forms:
    {"type":"range","min":,"max":,"step":,["unit":], "value": }
    {"type":"enum", "values":["v1",...], "value"}
    s is the setting data (dict)
    on error, raises either KeyError (if an item is not found) or AssertionError (all other errors)
    """
    t = s.get("type","range")
    if t == "range":
        validate_range(s)
    elif t == "enum":
        validate_enum(s)
    else:
        assert False, "'type' should be in ('range','enum')"

def is_int(x):
    return float(x) == float(int(x))

def validate_range(s):
    mn = s["min"]
    mx = s["max"]
    step = s.get("step", 0)
    assert isinstance(step, (int,float)), "'step' should be numeric"
    v = s["value"]
    assert isinstance(v, (int,float)), "'value' should be numeric"
    assert mn<mx, "min < max"
    assert mn<=v, "v >= min"
    assert v<=mx, "v <= max"
    if is_int(mn) and is_int(step) and step != 0:
        assert is_int( float(v-mn) / step ), "(value-min) is not an integral multiple of 'step'"


def validate_enum(s):
    vals = s["values"]
    assert vals, "'values' list should be non-empty"
    assert s["value"] in vals, "current value not in the list of valid values"

def validate_settings(data):
    """ validate response to --query
    expected format:
    { "application" : { "settings" : {"name":{desc}, ...}, "components" : {"cname" : { "name":{desc}, ... }, ... }}}
    }
    """

    data = copy.deepcopy(data) # don't clobber input data

    # TODO: chk that value is always min + N*step, if step is integer or an exact power-of-two fraction
    # (for non-integer steps, float precision prevents this from being exact)

    # top-level content
    try:
        ctx = ""
        assert isinstance(data, dict), "input data should be 'dict'"
        ctx = "data"
        app = data.pop("application")
        if data:
            warn("unrecognized items in {}: {}".format(ctx,repr(sorted(data.keys()))))
        ctx = "data['application']"
        assert isinstance(app, dict), "should be of type 'dict'"
        if "settings" in app:
            a = app.pop("settings")
            assert isinstance(a, dict, "'settings' should be of type 'dict'")
            if not a:
                warn("data['application']['settings'] is present but empty")
            ctx = cc = ctx+"['settings']"
            for k,s in a.items():
                ctx = "{}['{}']".format(cc,k)
                validate_setting(s)

        ctx = "data['application']"
        if "components" in app:
            ctx = "data['application'] has optional 'components' object"
            comps = app.pop("components")
            assert isinstance(app, dict), "should be of type 'dict'"
            if not comps:
                warn("data['application']['components'] is present but empty")
            for k,c in comps.items():
                ctx = "data['application']['components']['{}']".format(k)
                a = c.pop("settings") # required, raise exception if absent
                if c:
                    warn("unrecognized items in {}: {}".format(ctx,repr(sorted(c.keys()))))
                cc = ctx+"['settings']"
                assert isinstance(a, dict), "should be of type 'dict'"
                for k2,s in a.items():
                    ctx ="{}['{}']".format(cc,k2) 
                    validate_setting(s)

        ctx = "data['application']"
        if app:
            warn("unrecognized items in {}: {}".format(ctx,repr(sorted(app.keys()))))

    except KeyError as e:
        print("FAILED: {} not in {}".format(str(e), ctx),file=sys.stderr)
        return 1
    except AssertionError as e:
        print("FAILED: {ctx}: {err}".format(ctx=ctx, err=str(e)), file=sys.stderr)
        return 1
    except Exception:
        # unexpected exc.
        raise
        # FIXME:


def progress_checker():
    """returns an object suitable for use as a 'progress callback',
    each time it is called, it updates its properties as follows:
    start_time: set on obj. creation
    max_wait: max interval between two calls
    last_time: last time it was called
    """
    def f(**args):
        t = time.time()
        i = t - f.last_time
        f.max_wait = max(f.max_wait, i)
        f.last_time = t
 
    f.start_time = f.last_time = time.time()
    f.max_wait = 0.0

    return f

# FIXME: large part of this code is the same as in 'servo' itself, consider using a library
def run_cmd(cmd, req=None):

    progress_cb = progress_checker()

    # prepare stdin in-memory file if a request is provided
    if req is not None:
        stdin = json.dumps(req).encode("UTF-8")   # input descriptor -> json -> bytes
    else:
        stdin = b''         # no stdin

    # execute driver, providing request and capturing stdout/stderr
    proc = subprocess.Popen(cmd, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    stderr = [] # collect all stderr here
    rsp = {"status": "nodata"} # in case driver outputs nothing at all
    wi = [proc.stdin]
    ei = [proc.stdin, proc.stdout,proc.stderr]
    eof_stdout = False
    eof_stderr = False #
    while True:
        r,w,e = select.select([proc.stdout,proc.stderr], wi, ei )
        if eof_stdout and eof_stderr and proc.poll() is not None: # process exited and no more data
            break
        for h in r:
            if h is proc.stderr:
                l = h.read(4096)
                if not l:
                    eof_stderr = True
                    continue
                stderr.append(l)
            else: # h is proc.stdout
                l = h.readline()
                if not l:
                    eof_stdout = True
                    continue
                stdout_line = l.strip().decode("UTF-8") # there will always be a complete line, driver writes one line at a time
                #if args.verbose:
                #    print('DRIVER STDOUT:', stdout_line)
                if not stdout_line:
                    continue # ignore blank lines (shouldn't be output, though)
                try:
                    stdout = json.loads(stdout_line)
                except Exception as x:
                    proc.terminate()
                    # TODO: handle exception in json.loads?
                    raise
                if "progress" in stdout:
                    progress_cb(progress=stdout["progress"], message = stdout.get("message", None)) # FIXME stage/stageprogress ignored
                else: # should be the last line only (TODO: check only one non-progress line is output)
                    rsp = stdout
        if w:
            l = min(getattr(select,'PIPE_BUF',512), len(stdin)) # write with select.PIPE_BUF bytes or less should not block
            if not l: # done sending stdin
                proc.stdin.close()
                wi = []
                ei = [proc.stdout,proc.stderr]
            else:
                proc.stdin.write(stdin[:l])
                stdin = stdin[l:]
        # if e:

    progress_cb(progress=100,message="") # call last time, to update timing
    if progress_cb.max_wait > 60:
        raise Exception("max wait between progress reports exceeded limit of 60s")
    print("max_wait={}, runtime={}".format(progress_cb.max_wait, progress_cb.last_time-progress_cb.start_time), file=sys.stderr)

    rc = proc.returncode
#    if args.verbose or rc != 0:
#        print('DRIVER RETURNED:\n---stderr------------------\n{}\n----------------------\n'.format( (b"\n".join(stderr)).decode("UTF-8") ), file=sys.stderr)
    if rc != 0:
        print('DRIVER RETURNED:\n---stderr------------------\n{}\n----------------------\n'.format( (b"\n".join(stderr)).decode("UTF-8") ), file=sys.stderr)
        print("---stdin\n",stdin, file=sys.stderr)
        raise Exception('Command {} returned non-zero exit code {}'.format(repr(cmd), rc))

    return rsp

CMD="./adjust" # FIXME, make configurable
APP="test" # FIXME, real app name might be needed (should be configurable, for now we rely that app is either ignored or the driver-specific test setup makes an app named 'test' available.)

def test_version():
    r = subprocess.check_output([CMD,"--version"])
    r = r.strip().split(b"\n")
    assert len(r) and r[0],"check --version output is non-empty"
    # TODO: first word on the 1st line (r[0].split()[0]) should look like a version string

def test_info():
    r = run_cmd([CMD,"--info"])
    assert isinstance(r,dict)
    assert "version" in r
    del r["version"]
    if "has_cancel" in r:
        assert isinstance(r["has_cancel"], bool)
        del r["has_cancel"]
    # if r: warn: unknown data in info

def test_query():
    r = run_cmd([CMD,"--query", APP]) # FIXME: there's plans to change the option to be --describe
    t = validate_settings(r)
    assert not t, "query output validation"

def test_adj():
    """basic adjust tests"""

    r = run_cmd([CMD,"--query", APP]) # FIXME: there's plans to change the option to be --describe
    t = validate_settings(r)
    assert not t, "query output validation"

    # change a single numeric value
    found = False
    app = copy.deepcopy(r["application"])
    # if there are app-level settings, pick one from there first
    if "settings" in app:
        raise NotImplementedError # AFAIK, not supported by the backend, anyway.
    # TODO in validate_settings: either app or comp settings must be present
    for k,comp in app["components"].items():
        #
        for k2,s in comp["settings"].items():
            if s.get("type","range") != "range": continue
            step = s.get("step",0)
            found = True
            if s["value"]<s["max"]:
                if not step: step = min(s["max"]-s["value"],1.0) # pick a valid increment that keeps the value in range, if step == 0
                s["value"] += step
            else:
                if not step: step = min(s["value"]-s["min"],1.0)
                s["value"] -= step
            break
        if found: break
    if found:
        r = run_cmd([CMD, APP], {"application":app})
    else:
        # warn, but we raise error for now (no support for types other than 'range', so there should be at least one 'range' setting)
        raise Exception("no values of type 'range'")

    r2 = run_cmd([CMD,"--query", APP]) # FIXME: there's plans to change the option to be --describe
    t = validate_settings(r2)
    assert not t, "query output validation (after adj)"

    # TODO: check r2 != r (one setting is different)


# TODO: maybe convert this to 'pytest'
def run_tests():
    """
tested operations:
--version - expected (min) 1-line response and exitcode=0
--info - expected json output: {"version": "1.0", "has_cancel": false}
--query app - query current state
(empty options) app - change settings
"""

    err = False
    for f in test_version, test_info, test_query, test_adj:
        print ("running {}".format(f.__name__))
        try:
            f()
        except Exception as e:
            print ("FAILED {}".format(f.__name__), str(e))
            err = True

if __name__ == "__main__":
    run_tests()
