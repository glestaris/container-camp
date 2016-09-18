import time
import multiprocessing
from os import path
import fabric.api as fab
import fabric.contrib.files as fab_files
import ice
from ice import ascii_table
from ice import experiment_timing


BUNDLES_BASE_PATH = '/var/lib/containers'
CVMFS_BASE_PATH = '/cvmfs/container-images.aws'

###############################################################################
# Runners
###############################################################################


@ice.ParallelRunner
def ping_cvmfs(instances):
    """Ping CernVM-FS setup.
    """
    with fab.hide('running', 'warnings'):
        res = fab.execute(ping_cvmfs_task, instances)
    _print_outcomes(res)


@ice.ParallelRunner
def mount_cvmfs(instances, server_fqdn, cert_path):
    """Mount CernVM-FS repository.

    Args:
        server_fqdn: The FQD of the CernVM-FS server.
        cert_path: Path to the public ceritifcate file.
    """
    with fab.hide('running'):
        fab.execute(write_cvmfs_config_task, instances, server_fqdn, cert_path)
        res = fab.execute(mount_cvmfs_task, instances)
    _print_outcomes(res)


@ice.ParallelRunner
def runc_run(instances, image, id, *args):
    """Start a container using a CernVM-FS backed container image.

    Args:
        image: The CernVM-FS container image to use.
        id: The runC container id.
        args: Command to run in container.
    """
    q = multiprocessing.Queue()
    with fab.hide('running'):
        res = fab.execute(runc_run_task, instances, q, image, id, args)
    _print_outcomes(res)
    if _check_outcomes(res):
        durations = _get_durations(instances, q)
        _print_durations(durations)


@ice.ParallelRunner
def runc_exec(instances, id, *args):
    """Execute a process inside an existing container.

    Args:
        id: The runC container id.
        args: Command to run in container.
    """
    q = multiprocessing.Queue()
    with fab.hide('running'):
        res = fab.execute(runc_exec_task, instances, q, id, args)
    _print_outcomes(res)
    if _check_outcomes(res):
        durations = _get_durations(instances, q)
        _print_durations(durations)


@ice.ParallelRunner
def runc_delete(instances, id):
    """Delete a running container.

    Args:
        id: The runC container id.
    """
    with fab.hide('running'):
        res = fab.execute(runc_kill_task, instances, id)
    if not _check_outcomes(res):
        print('ERROR: Failed to kill runC containers!')
        _print_outcomes(res)
        return False

    with fab.hide('running'):
        res = fab.execute(delete_runc_bundle_task, instances, id)
    _print_outcomes(res)

###############################################################################
# Tasks
###############################################################################


def ping_cvmfs_task(instances):
    return fab.run('[ -f /cvmfs/container-images.aws/ping ]', warn_only=True)


def write_cvmfs_config_task(instances, server_fqdn, cert_path):
    fab.put(
        cert_path, '/etc/cvmfs/keys/container-images.aws.pub',
        use_sudo=True
    )

    fab.sudo('rm -f /etc/cvmfs/config.d/container-images.aws.conf')
    fab_files.append(
        '/etc/cvmfs/config.d/container-images.aws.conf',
        """CVMFS_SERVER_URL=http://{:s}/cvmfs/container-images.aws
CVMFS_PUBLIC_KEY=/etc/cvmfs/keys/container-images.aws.pub
        """.format(server_fqdn),
        use_sudo=True
    )

    fab.sudo('rm -f /etc/cvmfs/default.local')
    fab_files.append(
        '/etc/cvmfs/default.local',
        """CVMFS_REPOSITORIES=container-images.aws
CVMFS_HTTP_PROXY=DIRECT

CVMFS_CHECK_PERMISSIONS=yes
CVMFS_CLAIM_OWNERSHIP=no
""",
        use_sudo=True
    )


def mount_cvmfs_task(instances):
    fab.sudo('mkdir -p /cvmfs/container-images.aws')
    return fab.sudo(
        'mount -t cvmfs container-images.aws /cvmfs/container-images.aws',
        warn_only=True
    )


def make_runc_bundle_task(instances, image, id):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)
    image_path = path.join(CVMFS_BASE_PATH, 'image', image)
    rw_branch_path = path.join(bundle_path, 'rw')
    rootfs_path = path.join(bundle_path, 'rootfs')

    if not fab_files.exists(image_path, use_sudo=True):
        return _error('image `{:s}` does not exist'.format(image))
    if fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` exists'.format(bundle_path))

    fab.sudo('mkdir -p {:s}'.format(bundle_path))
    fab.sudo('mkdir {:s}'.format(rw_branch_path))
    fab.sudo('mkdir {:s}'.format(rootfs_path))

    return fab.sudo(
        'mount -t aufs -o br={:s}=rw:{:s}=ro none {:s}'.format(
            rw_branch_path, image_path, rootfs_path
        ),
        warn_only=True,
    )


def make_runc_config_task(instances, id, args):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)
    config_path = path.join(bundle_path, "config.json")

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    cmd = 'ocitools generate'
    for arg in args:
        cmd += ' --args {:s}'.format(arg)

    return fab.sudo('{:s} > {:s}'.format(cmd, config_path), warn_only=True)


def runc_run_task(instances, q, image, id, args):
    tm = experiment_timing.ExperimentTiming()

    ret = make_runc_bundle_task(instances, image, id)
    if ret.failed:
        return ret

    ret = make_runc_config_task(instances, id, args)
    if ret.failed:
        return ret

    bundle_path = path.join(BUNDLES_BASE_PATH, id)
    with fab.cd(bundle_path):
        tm.start(time.time())
        ret = fab.sudo('runc run {:s}'.format(id), warn_only=True)
        tm.end(time.time())

    q.put([fab.env.host_string, tm.to_json()])

    return ret


def runc_exec_task(instances, q, id, args):
    tm = experiment_timing.ExperimentTiming()
    tm.start(time.time())

    bundle_path = path.join(BUNDLES_BASE_PATH, id)

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    with fab.cd(bundle_path):
        ret = fab.sudo('runc exec {:s} {:s}'.format(
            id, ' '.join(args)
        ), warn_only=True)

    tm.end(time.time())
    q.put([fab.env.host_string, tm.to_json()])

    return ret


def runc_kill_task(instances, id):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    with fab.cd(bundle_path):
        # ignore error
        fab.sudo('runc kill {:s}'.format(id), warn_only=True)
        return fab.sudo('runc delete {:s}'.format(id), warn_only=True)


def delete_runc_bundle_task(instances, id):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)
    rootfs_path = path.join(bundle_path, 'rootfs')

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    fab.sudo('umount {:s}'.format(rootfs_path))
    return fab.sudo('rm -Rf {:s}'.format(bundle_path))

###############################################################################
# Helpers
###############################################################################


class _error():
    def __init__(self, msg):
        self.failed = True
        self.msg = msg
        print('ERROR: {:s}'.format(msg))


def _check_outcomes(res):
    for key, value in res.items():
        if value.failed:
            return False
    return True


def _print_outcomes(res):
    for key, value in res.items():
        if hasattr(value, 'failed') and value.failed:
            if hasattr(value, 'msg'):
                outcome = '[FAIL] - {:s}'.format(value.msg)
            else:
                outcome = '[FAIL]'
        elif value != '':
            outcome = '[OK] - {}'.format(value)
        else:
            outcome = '[OK]'
        print("{:70s} {}".format(key, outcome))


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
