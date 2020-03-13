Gym
===

A framework for automated VNF Testing (benchmarking, dimensioning, etc).


Scope
*****

Gym was built to receive high-level test descriptors and execute them to extract VNFs profiles, containing measurements of performance metrics - especially to associate resources allocation (e.g., vCPU) with packet processing metrics (e.g., throughput) of VNFs.  From the original research ideas, such output profiles might be used by orchestrator functions to perform VNF lifecycle tasks (e.g., deployment, maintenance, tear-down).

The proposed guiding principles to design and build Gym can be composed in multiple practical ways for different VNF testing purposes:

* Comparability: Output of tests shall be simple to understand and process, in a human-read able format, coherent, and easily reusable (e.g., inputs for analytic applications).

* Repeatability: Test setup shall be comprehensively defined through a flexible design model that can be interpreted and executed by the testing platform repeatedly but supporting customization.

* Configurability: Open interfaces and extensible messaging models shall be available between components for flexible composition of test descriptors and platform configurations.

* Interoperability: Tests shall be ported to different environments using lightweight and modular components.



Foundation
**********

Gym is a reference implementation of the ongoing draft in the Benchmarking Methodology Working Group (BMWG) in Internet Engineering Task Force (IETF), named https://datatracker.ietf.org/doc/draft-rosa-bmwg-vnfbench/ 

If you want to cite this work, please use:

ROSA, R. V.; BERTOLDO, C.; ROTHENBERG, C. E. [**Take your vnf to the gym: A testing framework for automated nfv performance benchmarking**](https://ieeexplore.ieee.org/document/8030496). IEEE Communications Magazine, v. 55, n. 9, p. 110–117, 2017. ISSN 0163-6804.

Bibtex:

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
month={Sep.}, }



How it Works
************

This is a short explanation of how Gym works.

Gym was created to receive a request of a VNF testing specification and deliver the performance metrics associated with it.
To realize that, Gym counts with 4 components: Agent, Monitor, Manager, and Player.
All of them are in essence python modules, which can be deployed anywhere behaving like microservices.
Agents and Monitors realize active and passive profiling of VNFs, respectively, while Manager interacts with them to coordinate such tasks. Player interacts with Manager realizing requests for multiple tasks decomposed from a VNF test specification. In an automated manner, all these components interact to deliver a full VNF test profile (output of Player), containing metrics from the Agents/Monitors measurements.
Agents and Monitors detains multiple interfaces to testing tools (e.g., ping, psutil, docker-py, iperf, etc), which can be loaded modularly according to the Manager requests. 



Roadmap
*******

Gym is the outcome of a PhD research project, so it is not dedicated for production. Mainly Gym can be used in research projects tackling reproducible experiments. So far:

* All Gym components are stable (i.e., as in a beta release) and work accordingly to their logical flow of messages in an asynchronous manner;
* The input and output VNF test specifications used by Gym are based on Yang data models currently being elaborated in a draft in IETF/BMWG;
* Proof of concept demos and publications showcased the utility of Gym for benchmarking tests.


The future work agenda is simple but demanding:

* Utilize protocol buffers as source of message specification among components;
* Use gRPC asynchronously with asyncio;
* Elaborate management interfaces for each component for the purposes of debugging and logging;
* Code interfaces to multiple tools for Agents/Monitors probers/listeners;
* Develop a specification format to automate the generation of comprehensive test reports (e.g., containing figures, statistics, logs).