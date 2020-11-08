.PHONY: clean-pyc clean-build
.DEFAULT_GOAL := help

TEST_PATH=./gym/tests

UTIL_FOLDER=./util
UTIL_TOOLS=tools.py
UTIL_VISUAL=visual.sh
UTIL_EXAMPLES=examples.sh


install-tools:
	sh -c "cd $(UTIL_FOLDER) && sudo /usr/bin/python3.8 $(UTIL_TOOLS) --install ${ARGS} && cd - "

uninstall-tools:
	sh -c "cd $(UTIL_FOLDER) && sudo /usr/bin/python3.8 $(UTIL_TOOLS) --uninstall ${ARGS} && cd - "

vagrant-requirements-virtualbox:
	sudo apt install -y vagrant

	sudo apt install -y virtualbox
	sudo apt-get install -y linux-headers-generic
	sudo dpkg-reconfigure virtualbox-dkms
	sudo dpkg-reconfigure virtualbox
	sudo modprobe vboxdrv
	sudo modprobe vboxnetflt

vagrant-requirements-libvirt:
	sudo apt install -y vagrant
	sudo apt-get install -y qemu-kvm qemu-utils libvirt-daemon bridge-utils virt-manager libguestfs-tools virtinst rsync
	sudo apt-get install -y ruby-libvirt libvirt-dev
	vagrant plugin install vagrant-libvirt

examples-aux:
	sh -c "cd $(UTIL_FOLDER) && sudo ./$(UTIL_EXAMPLES) && cd - "

requirements:
	sudo apt update && sudo apt install -y python3.8 python3-setuptools python3-pip
	mkdir -p /tmp/gym
	mkdir -p /tmp/gym/logs
	mkdir -p /tmp/gym/source

develop: requirements
	sudo /usr/bin/python3.8 setup.py develop

install: requirements
	/usr/bin/python3.8 -m pip install .

uninstall:
	sudo /usr/bin/python3.8 -m pip uninstall -y gym
    
clean-pyc:
	sudo sh -c "find . -name '*.pyc' -exec rm --force {} + "
	sudo sh -c "find . -name '*.pyo' -exec rm --force {} + "
	sudo sh -c "find . -name '*~' -exec rm --force  {} + "

clean-build:
	sudo sh -c "rm --force --recursive build/"
	sudo sh -c "rm --force --recursive dist/"
	sudo sh -c "rm --force --recursive *.egg-info"

clean: clean-build clean-pyc
	sudo rm -R /tmp/gym
	
isort:
	sh -c "isort --skip-glob=.tox --recursive . "

lint:
	flake8 --exclude=.tox

test: clean-pyc
	py.test --verbose --color=yes $(TEST_PATH)

run: install
	gym-cli

docker-build:
	docker build \
	--tag=gym:latest .

docker-run: docker-build
	docker run \
	--detach=false \
	--name=gym \
	gym:latest gym-cli

vagrant-run-virtualbox: requirements-vagrant-virtualbox
	vagrant up --provider virtualbox

vagrant-run-libvirt: vagrant-requirements-libvirt
	vagrant up --provider libvirt

start-visual:
	sh -c "cd $(UTIL_FOLDER) && ./$(UTIL_VISUAL) start && cd - "

stop-visual:
	sh -c "cd $(UTIL_FOLDER) && ./$(UTIL_VISUAL) stop && cd - "

all: requirements install run



help:
	@echo ""
	@echo "     				gym makefile help"
	@echo "           ---------------------------------------------------------"
	@echo ""
	@echo "     requirements"
	@echo "         Install gym requirements (i.e., python3.8 python3-setuptools python3-pip)."
	@echo "     examples"
	@echo "         Install gym examples requirements (i.e., see examples.sh in gym/util)."
	@echo "     vagrant-requirements-virtualbox"
	@echo "         Install the requirements to build a virtual machine with gym installed using virtualbox."
	@echo "     vagrant-requirements-libvirt"
	@echo "         Install the requirements to build a virtual machine with gym installed using qemu-kvm."
	@echo "     install-tools"
	@echo "         Install provided list (e.g., ARGS="ping iperf3 ...") of gym tools (i.e., probers/listeners in ./util/tools)."
	@echo "     uninstall-tools"
	@echo "         Uninstall provided list (e.g., ARGS="ping iperf3 ...") of gym tools (i.e., probers/listeners in ./util/tools)."
	@echo "     install"
	@echo "         Setup with pip install . ."
	@echo "     develop"
	@echo "         Setup with python3 setup.py develop."
	@echo "     uninstall"
	@echo "         Remove gym with pip uninstall gym."
	@echo "     clean-pyc"
	@echo "         Remove python artifacts."
	@echo "     clean-build"
	@echo "         Remove build artifacts."
	@echo "     clean"
	@echo "         Remove build and python artifacts (clean-build clean-pyc)."
	@echo "     isort"
	@echo "         Sort import statements."
	@echo "     lint"
	@echo "         Check style with flake8."
	@echo "     test"
	@echo "         Run py.test in gym/tests folder"
	@echo "     run"
	@echo "         Run the gym-cli on your local machine."
	@echo "     docker-run"
	@echo "         Build and run the gym-cli in a Docker container."
	@echo "     vagrant-run-virtualbox"
	@echo "         Build and run a virtual machine with gym installed using virtualbox."
	@echo "     vagrant-run-libvirt"
	@echo "         Build and run a virtual machine with gym installed using qemu-kvm."
	@echo "     start-visual"
	@echo "         Create and start the aux containers for monitoring (influxdb and graphana)."
	@echo "     stop-visual"
	@echo "         Stop and remove the aux containers for monitoring (influxdb and graphana)."
	@echo ""
	@echo "           ---------------------------------------------------------"
	@echo ""