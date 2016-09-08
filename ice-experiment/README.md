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

The latest AMI in eu-west-1 is: **ami-14166a67**.

## Experiment

TODO.
