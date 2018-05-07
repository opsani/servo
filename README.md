# servo
Optune "servo" agent base protocol handler (servo core)

## Using

<< document WIP >>

`servo` is the binary to be packaged

`measure.py` is an optional Python base class used by measurement drivers. It needs to be packaged only if the measurement driver uses it.

## Testing

When testing, place symlinks `measure` and `adjust` to the respective drivers
in the current working directory.

When testing to local Optune service, use `--url http://localhost:8080/servo` option

