import re
import json
from fabric import api as fab
import ice
from ice import ascii_table

###############################################################################
# Runners
###############################################################################


@ice.ParallelRunner
def start(hosts):
    """Start Docker daemon
    """
    with fab.hide('running'):
        res = fab.execute(daemon_start, hosts)
    _print_outcomes(res)


@ice.ParallelRunner
def stop(hosts):
    """Stop Docker daemon
    """
    with fab.hide('running'):
        res = fab.execute(daemon_stop, hosts)
    _print_outcomes(res)


@ice.ParallelRunner
def check(hosts):
    """Check the Docker daemon status
    """
    with fab.hide('running'):
        res = fab.execute(daemon_check, hosts)
    _print_outcomes(res)


@ice.ParallelRunner
def run(hosts, *args):
    """Run a container
    """
    with fab.hide('running'):
        res = fab.execute(container_run, hosts, *args)
    _print_outcomes(res)


@ice.ParallelRunner
def execute(hosts, *args):
    """Execute a process inside a container
    """
    with fab.hide('running'):
        res = fab.execute(container_exec, hosts, *args)
    _print_outcomes(res)


@ice.ParallelRunner
def rm(hosts, *args):
    """Remove a container
    """
    with fab.hide('running'):
        res = fab.execute(container_rm, hosts, *args)
    _print_outcomes(res)


@ice.ParallelRunner
def ps(hosts, *args):
    """List running containers
    """
    with fab.hide('running', 'stdout'):
        res = fab.execute(daemon_ps, hosts)

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

def daemon_start(hosts):
    return fab.sudo('service docker start', warn_only=True)


def daemon_stop(hosts):
    return fab.sudo('service docker stop', warn_only=True)


def daemon_check(hosts):
    return fab.sudo('service docker status > /dev/null', warn_only=True)


def container_run(hosts, *args):
    return fab.sudo('docker run ' + ' '.join(args), warn_only=True)


def container_exec(hosts, *args):
    return fab.sudo('docker exec ' + ' '.join(args), warn_only=True)


def container_rm(hosts, *args):
    return fab.sudo('docker rm ' + ' '.join(args), warn_only=True)


def daemon_ps(hosts):
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
