# servo

Optune "servo" agent base protocol handler (servo core) for Opsani's continuous optimization service enabled by AI. See www.opsani.com for more information on Optune.

The servo core handles the protocol between the Opsani Optune service and a particular user application environment. To create a fully functioning Optune servo, three pieces need to be put together:

1. The servo code (this project)
1. One or more adjust drivers for adjusting the application's settings in the user environment
1. One or more measurement drivers for collecting performance metrics for the application

Typically, the servo pieces are packaged together, with any dependencies, in a Docker container. While this is customary, it is not required; the 3 together can be packaged in any way that is convenient for you to deploy and operate.

The following sections describe what servos are available and how to use them:

  * [Configuration](#configuration)
  * [Using ready servos](#using-ready-servos)
  * [Available servo drivers](#available-servo-drivers)
    * [Adjust drivers for supported environments and CI/CD systems (e.g., Kubernetes, Mesos, Spinnaker, gitops)](#adjust-drivers)
    * [Measurement drivers for supported monitoring systems and benchmarks (e.g., Prometheus, Datadog, SignalFX)](#measurement-drivers)

## Configuration

### Command line

The servo core has the following command line options:

```
usage: servo [-h] [--interactive] [--delay DELAY] [--verbose] [--agent AGENT]
             [--account ACCOUNT] [--url URL] [--auth-token AUTH_TOKEN]
             [--no-auth]
             app_id
```

The minimal command line includes just the `app_id` parameter, which determines the application ID under which the results will be sent (e.g., as it shows in the Optune dashboard).

The `--account` parameter allows specifying the account name on the command line (instead of using the OPTUNE_ACCOUNT environment variable, see below)

The `--auth-token` parameter allows specifying a path to the auth token file (the default is `/run/secrets/optune_auth_token`, as required for Docker secrets). For Kubernetes, set to the path where the file will be mapped, e.g., `/etc/optune_auth_token`, or, omit this parameter if mapped in the default location)

### Environment variables

The servo configuration is performed through environment variables and config file(s). The servo core itself uses the following variables:

| *Variable* | *Description* |
| --- | --- |
| OPTUNE_ACCOUNT | Account name within the Optune service (provided during signup) |
| OPTUNE_PERF | Formula for computing performance from metrics. May be just a metric name (e.g., `throughput`) or a formula combining multiple metrics |
| OPTUNE_VERBOSE_STDERR | Control how much of driver's stderr to send to the Optune service in case of error (`none`, `minimal`, **`all`**) |
| OPTUNE_IO_TIMEOUT | Maximum time (seconds) to wait for a driver to send a progress or completion message. Default is empty (unlimited time). |

Specific adjust and measure drivers may define additional environment variables, see the respective driver's repo and/or instructions.

### Configuration file(s)

In addition, the servo core defines a recommended configuration file, `./config.yaml` that drivers may use for additional configuration. Each driver can find its own section, under a top-level key matching the driver's name (i.e., `k8s:` for the `k8s` driver).

## Using ready servos

The following complete servos have been packaged and made available as containers for easy deployment:

| *Repository* | *Image on Docker Hub* |
| --- | --- |
| [servo-k8s-datadog](https://github.com/opsani/servo-k8s-datadog) | `opsani/servo-k8s-datadog` |
| [servo-k8s-newrelic](https://github.com/opsani/servo-k8s-newrelic) | `opsani/servo-k8s-newrelic` |
| [servo-k8s-sfx](https://github.com/opsani/servo-k8s-sfx) | `opsani/servo-k8s-sfx` |
| [servo-k8s-ab](https://github.com/opsani/servo-k8s-ab) | `opsani/servo-k8s-ab` |
| [servo-gitops-sfx](https://github.com/opsani/servo-gitops-sfx) | `opsani/servo-gitops-sfx` |
| [servo-javaservice-datadog](https://github.com/opsani/servo-javaservice-datadog) | `opsani/servo-javaservice-datadog` |
| [servo-spinnaker-wavefront](https://github.com/opsani/servo-spinnaker-wavefront) | `opsani/servo-spinnaker-wavefront` |
| [servo-tomcat-wavefront](https://github.com/opsani/servo-tomcat-wavefront) | `opsani/servo-tomcat-wavefront` |
| [servo-skopos-ab](https://github.com/opsani/servo-skopos-ab) | `opsani/servo-skopos-ab` |
| [servo-rancher-ab](https://github.com/opsani/servo-rancher-ab) | `opsani/servo-rancher-ab` |
| [redis-benchmark](https://github.com/opsani/servo-redis-benchmark) | `opsani/servo-redis-benchmark` |

### Deploying servos to Kubernetes

See the following example Deployment object for a Kubernetes servo:
https://github.com/opsani/co-http/blob/master/k8s/servo.yaml

For more details on configuring the Kubernetes adjust driver, see that driver's repo.

### Deploying servos to Docker

```
docker rm -f servo || true
docker run -d --restart=always \
    --name servo \
    -v /opt/optune/auth_token:/opt/optune/auth_token \
    -v /opt/optune/config.yaml:/servo/config.yaml \
    $DOCKER_IMAGE --auth-token /opt/optune/auth_token \
    --account $OPTUNE_ACCOUNT $OPTUNE_APP_ID
```

## Available servo drivers

Servo drivers are usually provided as open source projects in github. Here is a list of the currently known Optune servo drivers:

### Adjust drivers

| *Environment* | *Description* |
| --- | --- |
| [k8s](https://github.com/opsani/servo-k8s) | Kubernetes container orchestration: deployments in a namespace, with autodiscovery. Works with Kubernetes and OpenShift |
| [gitops](https://github.com/opsani/servo-gitops) | Gitops deployment (immutable infrastructre; works with Kubernetes, Mesos, OpenShift and PaaSTA, as well as with any YAML-based deployment manifest) |
| [ec2asg](https://github.com/opsani/servo-ec2asg) | Amazon Web Services deployments based on auto-scaling groups of EC2 instances |
| [spinnaker](https://github.com/opsani/servo-spinnaker) | Spinnaker continuous deployment |
| [tomcat](https://github.com/opsani/servo-tomcat) | Tomcat Java service (bash startup script) |
| [javaservice](https://github.com/opsani/servo-javaservice) | Java service (Linux systemd service) |
| [skopos](https://github.com/opsani/servo-skopos) | Skopos continuous deployment |
| [rancher](https://github.com/opsani/servo-rancher) | Rancher 1.x container orchestration (for Rancher 2.x+, use the k8s driver) |
| [redis](https://github.com/opsani/servo-redis) | Redis structured data store |

Multiple adjust drivers can be combined in a single servo using the [aggregation](https://github.com/opsani/servo-agg) driver.

### Measurement drivers

| *Tool* | *Description* |
| --- | --- |
| [prom](https://github.com/opsani/servo-prom) | Prometheus |
| [datadog](https://github.com/opsani/servo-datadog) | Datadog (supports multi-measurement protocol extension) |
| [newrelic](https://github.com/opsani/servo-newrelic) | NewRelic APM (supports multi-measurement protocol extension) |
| [sfx](https://github.com/opsani/servo-sfx) | SignalFX |
| [wavefront](https://github.com/opsani/servo-wavefront) | Wavefront |
| [ab](https://github.com/opsani/servo-ab) | Apache Benchmark (combined load generator and measurement driver) |
| [exec](https://github.com/opsani/servo-exec) | Aggregation driver that supports running arbitrary commands and perform HTTP requests to provide support for other measurement drivers |
| [redis-benchmark](https://github.com/opsani/servo-redis-benchmark) | Custom benchmark for using Redis as a cache |
| hammerdb | HammerDB benchmark (contact support for access to preliminary version of this driver) |

## Creating user-defined servos

`servo` is the binary to be packaged

`measure.py` is an optional Python base class that makes it easier to create measurement drivers in Python. It needs to be packaged only if the measurement driver uses it.

`adjust.py` is an optional Python base class that makes it easier to create adjust drivers in Python. It needs to be packaged only if the adjust driver uses it.

Servos are typically packaged as Docker containers. See the ready-made servos for examples of Dockerfiles, e.g, https://github.com/opsani/servo-k8s-datadog

## Testing

When testing, place symlinks `measure` and `adjust` to the respective drivers
in the current working directory.

When testing with a local Optune test service, use `--url http://localhost:8080/servo --noauth` options


