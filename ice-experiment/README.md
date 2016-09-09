# runC - CernVM-FS iCE experiment

## Experiment image

The subdirectory `test-image/` defines a Packer recipe to build an Ubuntu 16.04
based AMI to be used in the iCE experiment. The AMI contains:

* runC
* Docker
* CernVM-FS client

To build the image, please create a `secrets.json` file inside `test-image/`
with the following format:

```json
{
  "aws_access_key": "...",
  "aws_secret_key": "..."
}
```

Running `make` inside `test-image/` should then be able to build and push an
AMI. Currently AMIs end up in the eu-west-1 AWS availability zone but you can
easily change that by modifying `test-image/runc-cvmfs.json`.

The latest AMI in eu-west-1 is: **ami-0af58979**.

## Experiment

### Installing and configuring iCE

Running the experiment requires installing and running iCE:

```bash
git clone https://github.com/glestaris/ice
cd ice
pip install -r requirements.txt
```

iCE configuration is done by providing an `ice.ini` file in `~/.ice`:

```bash
# from the iCE repository
cp -r config/default ~/.ice
```

Edit `~/.ice/ice.ini` accordingly.

You can use the following public iCE registry:

```ini
[registry_client]
host=ice-registry.cfapps.io
port=80
```

### Running iCE

To start iCE, run `./bin/ice-shell` from within the iCE repository.

#### Creating experiment VMs

iCE supports AWS EC2. If the `~/.ice/ice.ini` contains the AWS credentials
and the other required configuration parameters, you should be able to create
iCE instances by using `ec2_create` inside the iCE shell:

```bash
$> ec2_create -n 2 # creates 2 VMs
$> inst_wait -n 2 # blocks until the VMs come up
```

#### Loading the experiment

There are two experiment files in this directory:

* `docker.py` for the Docker cluster
* `cc.py` for the CernVM-FS / runC experiment

To load an experiment run `exp_load` in the iCE shell:

```bash
$> exp_load /path/to/container-camp/ice-experiment/docker.py
$> exp_ls docker # will list the experiment's runners
```

#### Creating containers and measuring creation time

The `docker.py` experiment defines the `run` runner. The `run` runner measures
the duration it takes `docker run` to return. You can run the `run` runner
with the usual Docker arguments as follows:

```bash
$> exp_run docker run --name test-redis -d redis:latest
```

#### Running the CernVM-FS / runC experiment

The `cc.py` experiment requires a bit more setup. Firstly, it requires a
running CernVM-FS server with uploaded container images. Then it requires
mounting the CernVM-FS repository in the iCE instances.

Please, create a Github issue if you are interested in trying it out and I will
make sure this section get populated with detailed instructions to do so.
