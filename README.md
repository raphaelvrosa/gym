# Gym

This is a project to bring into reality the ideas designed in VBaaS (VNF Benchmarking-as-a-Service).
The main purpose of this source code is a modular ad-hoc platform for testing VNFs and their respective infrastructure.

Gym is a reference implementation of the ongoing draft in the Benchmarking Methodology Working Group (BMWG) in Internet Engineering Task Force (IETF), named [**Methodology for VNF Benchmarking Automation**](https://datatracker.ietf.org/doc/draft-rosa-bmwg-vnfbench/).

If you want to cite this work, please use:

ROSA, R. V.; BERTOLDO, C.; ROTHENBERG, C. E. [**Take your vnf to the gym: A testing framework for automated nfv performance benchmarking**](https://ieeexplore.ieee.org/document/8030496). IEEE Communications Magazine, v. 55, n. 9, p. 110–117, 2017. ISSN 0163-6804.


Bibtex:

```bibtex
@ARTICLE{Rosa:2017:Gym,
author={R. V. {Rosa} and C. {Bertoldo} and C. E. {Rothenberg}},
journal={IEEE Communications Magazine},
title={Take Your VNF to the Gym: A Testing Framework for Automated NFV Performance Benchmarking},
year={2017},
volume={55},
number={9},
pages={110-117},
keywords={program testing;virtualisation;VNF;automated NFV performance benchmarking;software entity;testing framework;vIMS scenario;network functions virtualization;Benchmark testing;Measurement;Monitoring;Software testing;Visualization;Network function virtualization},
doi={10.1109/MCOM.2017.1700127},
ISSN={0163-6804},
month={Sep.},
}
```


## Installing

All these packages can be installed using the command below.
This command requires root privileges. It installs gym components in the bare metal and creates the raphaelvrosa/gym:latest docker image to be used by the test cases.


### Dependencies

Gym is tested in Ubuntu, version 20.04 onwards. 

Gym depends on python 3.8, because it uses some gRPC libraries via asyncio. 

To run most of the examples, gym makes use of Containernet (an extension of Mininet to run containers), thus it needs to install Docker and Mininet to do so.
Besides, these dependencies also download and build other docker images needed for most of the gym examples, download some pcap files and place them under /mnt/pcaps folder.
To install such dependencies, follow:

```bash
$ sudo apt install git

$ git clone https://github.com/raphaelvrosa/gym

$ cd gym

$ sudo make examples-util
```


It's also recommended to add your user to the `docker` group (so no need to sudo the docker command in the terminal):

```bash
$ sudo usermod -a -G docker $USER
```

Then logout the OS and login again, so the group permissions are enabled.


### Gym

To install gym and build a docker image with all its components operational.

```bash
$ sudo make install
```

This command will install all the python packages needed by gym (see the setup.py file), and it will make available all the gym core components executables (i.e., gym-player, gym-manager, gym-monitor, gym-agent) to be run by terminal. 


To install Gym for **development** purposes, run:

```bash
$ sudo python3.8 setup.py develop
```

This will not actually install all the files in your system, but just link them to your development directory, simplifying the code/deploy/test cycle.

### Docker Image

You can build and run the gym docker image via:

```bash
$ sudo make docker-build

$ sudo make docker-run
```

### Virtual Machine (VM)

Gym uses Vagrant to build a virtual machine (VM). 
You can build a VM using qemu-kvm or virtualbox via:

```bash
$ sudo make vagrant-run-virtualbox

$ sudo make vagrant-run-libvirt
```

You can interact with the virtual machine using vagrant commands (e.g., vagrant ssh).

## Examples

In the folder gym/examples there exists a set of different example files.

Use gym-cli to experiment with the examples:

```bash
$ sudo gym-cli --uuid cli --address 127.0.0.1:9988 --source ./examples
```

Specifying --source means all the files in that folder will be available to be loaded by gym-cli and have experiments performed.

**Important:** sudo is needed because gym is going to start one of its components, gym-infra, that is responsible to start containernet, a platform used in the examples.


After initializing gym-cli, load the configuration file vnfbd.json example you want to experiment with. For instance:

```bash
$ sudo gym-cli --uuid cli --address 127.0.0.1:9988 --source ./examples


		<<< Welcome to Gym >>>		

(-: gym > load vnf-br-001.json

-> task: Loading configuration file at .../gym/examples/vnf-br-001.json
-> result: Configuration loaded

(-: gym > 

```

Having successfuly loaded the configuration, then you can begin the experiment.


```bash

		<<< Welcome to Gym >>>		

-> task: Loading configuration file at .../gym/examples/vnf-br-001.json
-> result: Configuration loaded

(-: gym > begin

: Beginning :

-> task: Experiment Begin

```

Gym is going to start gym-infra and gym-player components, then send the VNF-BR loaded config to gym-player, and wait for its result.

After waiting for a while, at the end of the experiment you should se something like:

```bash
: Beginning :

-> task: Experiment Begin
-> result: Gym Experiment Ok

-> result: Result VNF-BR 001 (json and csv) saved to /tmp/gym/results/

(-: gym > 

```

If errors were found, check the gym logs at /tmp/gym/logs. There exists a single log file for each component (e.g., GymCLIApp-cli.log,  GymInfra-gym-infra.log, GymPlayer-gym-player.log).


Finally, you can end the experiment and say goodbye to gym, type <ctrl+d> to exit gym-cli.


```bash

(-: gym > end

: Ending :

-> task: Experiment End
-> result: Ended Gym Experiment

(-: gym > <ctrl+d>

	<<< See you soon! Cheers, Gym >>>	

```



**Important:** To execute examples 1, 2 and 3 follow the instructions in the topic Installing/Dependencies previously explained in this readme.

Description of the examples:

* #1: Uses the containernet platform to deploy agents and a dummy VNF, which just bypass the traffic among its ports. The agents perform the execution of ping/iperf3 traffic through the target VNF using multiple instances of a prober.

* #2: Uses the containernet platform to deploy agents and a dummy VNF, which just bypass the traffic among its ports. The agents perform the execution of ping/iperf3 traffic through the target VNF, while its container is monitored during the test by a gym-monitor component.

* #3: Uses the containernet platform to deploy agents and a Suricata-IDS VNF. The agents perform the execution of tcpreplay traffic through the target VNF, while its container is monitored externally and the Suricata process is monitored internally in the VNF.
The test consists in executing different pcap files using tcpreplay  while the VNF suricata has loaded different rule sets.
In the end all the metrics are saved into csv files into the gym/tests/csv folder, included the timeseries monitoring of the container, and the overall VNF-PP metrics according to the VNF-BD input parameters. 

**Notice**: In the tests 1, 2 and 3, the flow of information consists in starting a player component and the containernet platform. When deployed a layout on player, it requires containernet to build the scenario to run the other gym components needed for the test. After the topology is deployed, player reaches manager to get the components status, and starts deploying the tasks. After all tasks are finished, player demands the scenario to be finished in the containernet platform and finally outputs the vnf-br to a json file.

# License

Gym is released under Apache 2.0 license.

# Contact

If you have any issues, please use GitHub's [issue system](https://github.com/intrig-unicamp/gym/issues) to get in touch.

## Mailing-list

If you have any questions, please use the mailing-list at https://groups.google.com/forum/#!forum/gym-discuss.

## Contribute

Your contributions are very welcome! Please fork the GitHub repository and create a pull request.

## Creator and Lead Developer

Raphael Vicente Rosa
* Mail: <raphaelvrosa (at) gmail (dot) com>
* GitHub: [@raphaelvrosa](https://github.com/raphaelvrosa)
* Website: [INTRIG Webpage](https://intrig.dca.fee.unicamp.br/raphaelvrosa/)

This project is part of [**INTRIG (Information & Networking Technologies Research & Innovation Group)**](http://intrig.dca.fee.unicamp.br) at University of Campinas - UNICAMP, Brazil.

INTRIG is led by [**Prof. Dr. Christian Esteve Rothenberg**](https://intrig.dca.fee.unicamp.br/christian/).

# Acknowledgements

This project was supported by Ericsson Innovation Center in Brazil.
