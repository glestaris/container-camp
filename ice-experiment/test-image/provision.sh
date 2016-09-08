#!/bin/sh
set -e
set -x

update() {
  apt-get -y update
  apt-get -y upgrade
  apt-get -y clean
}

install_apt_packages() {
  apt-get install -y vim \
	git \
	silversearcher-ag \
	jq \
	cgroup-lite \
	htop \
	gcc \
	python
}

install_docker() {
  curl https://get.docker.com | sh
}

install_runc() {
  # Download and install Go
  wget -qO- https://storage.googleapis.com/golang/go1.7.linux-amd64.tar.gz | tar -C /usr/local -xzf -

  # Setupt the environment
  export GOPATH=/root/go
  export PATH=$GOPATH/bin:/usr/local/go/bin:$PATH

  # Clone runC
  mkdir -p $GOPATH/src/github.com/opencontainers/
  cd $GOPATH/src/github.com/opencontainers
  git clone https://github.com/opencontainers/runc

  # Build
  cd runc
  GOPATH=$PWD/Godeps/_workspace:$GOPATH go build -o runc .

  # Install
  cp runc /usr/local/bin/runc
}

install_cvmfs() {
  # Add custom apt source
  wget https://ecsft.cern.ch/dist/cvmfs/cvmfs-release/cvmfs-release-latest_all.deb
  sudo dpkg -i cvmfs-release-latest_all.deb
  rm -f cvmfs-release-latest_all.deb

  # Install
  apt-get update
  apt-get install -y cvmfs \
	linux-image-extra-$(uname -r)
}

###############################################################################

update
install_apt_packages
install_docker
install_runc
install_cvmfs
