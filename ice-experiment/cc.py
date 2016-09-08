from os import path
import fabric.api as fab
import fabric.contrib.files as fab_files
import ice


BUNDLES_BASE_PATH = '/var/lib/containers'
CVMFS_BASE_PATH = '/cvmfs/container-images.aws'

###############################################################################
# Runners
###############################################################################


@ice.ParallelRunner
def ping_cvmfs(hosts):
    """Ping CernVM-FS setup.
    """
    with fab.hide('running', 'warnings'):
        res = fab.execute(ping_cvmfs_task, hosts)
    _print_outcomes(res)


@ice.ParallelRunner
def mount_cvmfs(hosts, server_fqdn, cert_path):
    """Mount CernVM-FS repository.

    Args:
        server_fqdn: The FQD of the CernVM-FS server.
        cert_path: Path to the public ceritifcate file.
    """
    with fab.hide('running'):
        fab.execute(write_cvmfs_config_task, hosts, server_fqdn, cert_path)
        res = fab.execute(mount_cvmfs_task, hosts)
    _print_outcomes(res)


@ice.ParallelRunner
def runc_start(hosts, image, id, *args):
    """Start a container using a CernVM-FS backed container image.

    Args:
        image: The CernVM-FS container image to use.
        id: The runC container id.
        args: Command to run in container.
    """
    with fab.hide('running'):
        res = fab.execute(make_runc_bundle_task, hosts, image, id)
    if not _check_outcomes(res):
        print('ERROR: Failed to make runC bundles!')
        _print_outcomes(res)
        return False

    with fab.hide('running'):
        res = fab.execute(make_runc_config_task, hosts, id, args)
    if not _check_outcomes(res):
        print('ERROR: Failed to make runC config in bundles!')
        _print_outcomes(res)
        return False

    with fab.hide('running'):
        res = fab.execute(runc_start_task, hosts, id)
    _print_outcomes(res)


@ice.ParallelRunner
def runc_exec(hosts, id, *args):
    """Execute a process inside an existing container.

    Args:
        id: The runC container id.
        args: Command to run in container.
    """
    with fab.hide('running'):
        res = fab.execute(runc_exec_task, hosts, id, args)
    _print_outcomes(res)


@ice.ParallelRunner
def runc_delete(hosts, id):
    """Delete a running container.

    Args:
        id: The runC container id.
    """
    with fab.hide('running'):
        res = fab.execute(runc_kill_task, hosts, id)
    if not _check_outcomes(res):
        print('ERROR: Failed to kill runC containers!')
        _print_outcomes(res)
        return False

    with fab.hide('running'):
        res = fab.execute(delete_runc_bundle_task, hosts, id)
    _print_outcomes(res)

###############################################################################
# Tasks
###############################################################################


def ping_cvmfs_task(hosts):
    return fab.run('[ -f /cvmfs/container-images.aws/ping ]', warn_only=True)


def write_cvmfs_config_task(hosts, server_fqdn, cert_path):
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


def mount_cvmfs_task(hosts):
    fab.sudo('mkdir -p /cvmfs/container-images.aws')
    return fab.sudo(
        'mount -t cvmfs container-images.aws /cvmfs/container-images.aws',
        warn_only=True
    )


def make_runc_bundle_task(hosts, image, id):
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


def make_runc_config_task(hosts, id, args):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)
    config_path = path.join(bundle_path, "config.json")

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    cmd = 'ocitools generate'
    for arg in args:
        cmd += ' --args {:s}'.format(arg)

    return fab.sudo('{:s} > {:s}'.format(cmd, config_path), warn_only=True)


def runc_start_task(hosts, id):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    with fab.cd(bundle_path):
        fab.sudo('runc create {:s}'.format(id))
        return fab.sudo('runc start {:s}'.format(id), warn_only=True)


def runc_exec_task(hosts, id, args):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    with fab.cd(bundle_path):
        return fab.sudo('runc exec {:s} {:s}'.format(
            id, ' '.join(args)
        ), warn_only=True)


def runc_kill_task(hosts, id):
    bundle_path = path.join(BUNDLES_BASE_PATH, id)

    if not fab_files.exists(bundle_path, use_sudo=True):
        return _error('`{:s}` does not exist'.format(bundle_path))

    with fab.cd(bundle_path):
        fab.sudo('runc kill {:s}'.format(id))
        return fab.sudo('runc delete {:s}'.format(id), warn_only=True)


def delete_runc_bundle_task(hosts, id):
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
