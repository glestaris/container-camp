import re
import json
import time
import multiprocessing
from fabric import api as fab
import ice
from ice import ascii_table
from ice import experiment_timing

###############################################################################
# Runners
###############################################################################


@ice.ParallelRunner
def start(instances):
    """Start Docker daemon
    """
    with fab.hide('running'):
        res = fab.execute(daemon_start, instances)
    _print_outcomes(res)


@ice.ParallelRunner
def stop(instances):
    """Stop Docker daemon
    """
    with fab.hide('running'):
        res = fab.execute(daemon_stop, instances)
    _print_outcomes(res)


@ice.ParallelRunner
def check(instances):
    """Check the Docker daemon status
    """
    with fab.hide('running'):
        res = fab.execute(daemon_check, instances)
    _print_outcomes(res)


@ice.ParallelRunner
def run(instances, *args):
    """Run a container
    """
    q = multiprocessing.Queue()
    with fab.hide('running'):
        res = fab.execute(container_run, instances, q, *args)
    _print_outcomes(res)
    durations = _get_durations(instances, q)
    _print_durations(durations)


@ice.ParallelRunner
def execute(instances, *args):
    """Execute a process inside a container
    """
    q = multiprocessing.Queue()
    with fab.hide('running'):
        res = fab.execute(container_exec, instances, q, *args)
    _print_outcomes(res)
    durations = _get_durations(instances, q)
    _print_durations(durations)


@ice.ParallelRunner
def rm(instances, *args):
    """Remove a container
    """
    with fab.hide('running'):
        res = fab.execute(container_rm, instances, *args)
    _print_outcomes(res)


@ice.ParallelRunner
def ps(instances, *args):
    """List running containers
    """
    with fab.hide('running', 'stdout'):
        res = fab.execute(daemon_ps, instances)

    res_parsed = {}
    for key, value in res.items():
        if value.failed:
            print('{:70s} [FAIL]'.format(key))
            continue
        json_str = '[{}]'.format(value)
        json_str = re.sub(r'},\]', '}]', json_str)
        res_parsed[key] = json.loads(json_str)

    table = ascii_table.ASCIITable()
    table.add_column('name', ascii_table.ASCIITableColumn('Name', 20))
    table.add_column('image', ascii_table.ASCIITableColumn('Image', 30))
    table.add_column('ports', ascii_table.ASCIITableColumn('Ports', 30))

    for key in res_parsed.keys():
        table.add_comment_row('Host: {}'.format(key))
        for container in res_parsed[key]:
            table.add_row({
                'name': container['name'],
                'image': container['image'],
                'ports': container['ports']
            })

    print(ascii_table.ASCIITableRenderer().render(table))


###############################################################################
# Tasks
###############################################################################

def daemon_start(instances):
    return fab.sudo('service docker start', warn_only=True)


def daemon_stop(instances):
    return fab.sudo('service docker stop', warn_only=True)


def daemon_check(instances):
    return fab.sudo('service docker status > /dev/null', warn_only=True)


def container_run(instances, q, *args):
    tm = experiment_timing.ExperimentTiming()
    tm.start(time.time())

    ret = fab.sudo('docker run ' + ' '.join(args), warn_only=True)

    tm.end(time.time())
    q.put([fab.env.host_string, tm.to_json()])

    return ret


def container_exec(instances, q, *args):
    tm = experiment_timing.ExperimentTiming()
    tm.start(time.time())

    ret = fab.sudo('docker exec ' + ' '.join(args), warn_only=True)

    tm.end(time.time())
    q.put([fab.env.host_string, tm.to_json()])

    return ret


def container_rm(instances, *args):
    return fab.sudo('docker rm ' + ' '.join(args), warn_only=True)


def daemon_ps(instances):
    cmd = """docker ps --format '{
    "name": "{{.Names}}",
    "image": "{{.Image}}",
    "ports": "{{.Ports}}"
},'"""
    return fab.sudo(cmd, warn_only=True)


###############################################################################
# Helpers
###############################################################################

def _print_outcomes(res):
    for key, value in res.items():
        if value.failed:
            outcome = '[FAIL]'
        elif value != '':
            outcome = '[OK] - {}'.format(value)
        else:
            outcome = '[OK]'
        print('{:70s} {}'.format(key, outcome))


def _get_durations(instances, queue):
    durations = {}
    for i in range(0, len(instances)):
        host_string, json_str = queue.get()
        tm = experiment_timing.ExperimentTiming.from_json(json_str)
        durations[host_string] = tm.duration()
    return durations


def _print_durations(durations):
    table = ascii_table.ASCIITable()
    table.add_column('host_string', ascii_table.ASCIITableColumn('Host', 60))
    table.add_column('duration', ascii_table.ASCIITableColumn('Duration', 20))
    for host_string, duration in durations.items():
        table.add_row({
            'host_string': host_string,
            'duration': str(duration)
        })
    print(ascii_table.ASCIITableRenderer().render(table))
