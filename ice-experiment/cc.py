import fabric.api as fab
import fabric.contrib.files as fab_files
import ice

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
        print("{:70s} {}".format(key, outcome))
