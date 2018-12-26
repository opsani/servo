# servo

Optune "servo" agent base protocol handler (servo core) for Opsani's continuous optimization service enabled by AI. See www.opsani.com for more information on Optune.

The servo core handles the protocol between the Opsani Optune service and a particular user application environment. To create a fully functioning Optune servo, three pieces need to be put together:

1. The servo code (this project)
1. One or more adjust drivers for adjusting the application's settings in the user environment
1. One or more measurement drivers for collecting performance metrics for the application

Typically, the servo pieces are packaged together, with any dependencies, in a Docker container. While this is customary, it is not required; the 3 together can be packaged in any way that is convenient for you to deploy and operate.

## Using ready servos

(WIP)


## Available servo drivers

Servo drivers are usually provided as open source projects in github. Here is a list of the currently known Optune servo drivers:

### Adjust drivers and links

| *Environment* | *Description* |
| --- | --- |
| [k8s](github.com/opsani/servo-k8s) | Kubernetes container orchestration: deployments in a namespace, with autodiscovery. Works with Kubernetes and OpenShift |
| [gitops](github.com/opsani/servo-gitops) | Gitops deployment (immutable infrastructre; works with Kubernetes, Mesos and OpenShift, as well as with any YAML-based deployment manifest) |
| [ec2asg](github.com/opsani/servo-ec2asg) | Amazon Web Services deployments based on auto-scaling groups of EC2 instances |
| [spinnaker](github.com/opsani/servo-spinnaker) | Spinnaker continuous deployment |
| [tomcat](github.com/opsani/servo-tomcat) | Tomcat Java service (bash startup script) |
| [javaservice](github.com/opsani/servo-javaservice) | Java service (Linux systemd service) |
| [skopos](github.com/opsani/servo-skopos) | Skopos continuous deployment |
| [rancher](github.com/opsani/servo-rancher) | Rancher 1.x container orchestration (for Rancher 2.x+, use the k8s driver) |

Multiple adjust drivers can be combined in a single servo using the [aggregation](github.com/opsani/servo-agg) driver.

### Measurement drivers

| *Tool* | *Description* |
| --- | --- |
| [prom](github.com/opsani/servo-prom) | Prometheus |
| [datadog](github.com/opsani/servo-datadog) | Datadog (supports multi-measurement protocol extension) |
| [sfx](github.com/opsani/servo-sfx) | SignalFX |
| [wavefront](github.com/opsani/servo-wavefront) | Wavefront |
| [ab](github.com/opsani/servo-ab) | Apache Benchmark (combined load generator and measurement driver) |

## Creating user-defined servos

`servo` is the binary to be packaged

`measure.py` is an optional Python base class that makes it easier to create measurement drivers in Python. It needs to be packaged only if the measurement driver uses it.

`adjust.py` is an optional Python base class that makes it easier to create adjust drivers in Python. It needs to be packaged only if the adjust driver uses it.


## Testing

When testing, place symlinks `measure` and `adjust` to the respective drivers
in the current working directory.

When testing with a local Optune test service, use `--url http://localhost:8080/servo --noauth` options

