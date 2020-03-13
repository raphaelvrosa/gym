Workflows
=========

Use Case View
*************

Gym may have two types of users, VNF Developer (Analyst) and VNF User (Tester). 

The Tester can design and run multiple test cases and get the output format of a test result from the Player component (i.e. a VNF-BR). 

The Analyst concerns about the test results, performing analysis on them and tunning the VNF performance and/or fixing bugs accordingly.

Flow/Process View
*****************

Gym core components communicate through a flexible REpresentational State Transfer  (REST) Application Programming Interface (API) using generic RPC calls with custom/extensible JavaScript Object Notation (JSON) message formats. In the following, we describe a generic workflow based on request-reply message exchanges and pairwise component interactions represented as numbered (1 to 7).

0. Considers that all the Gym components are already deployed and established connections with each other.

1. The first step consists of a user defining the composition of the testing VNF-BD containing the structural and functional requirements to express target performance metrics that will be processed to eventually generate a VNF-PP.

2. The Player processes the parametrized VNF-BD considering the features offered by the associated/available Manager(s). The output is a workflow of tasks, in sequence or parallel, submitted to a selected Manager that satisfies (i.e. controls a matching set of Agents/Monitors) the VNF-BD requirements. Based on input variables, a VNF-BD can be decomposed into different sets of tasks with the corresponding high-level probers/listeners parameters.

3. The Manager decomposes tasks into a coherent sequence of instructions to be sent to Agents and/or Monitors. Inside each instruction, sets of actions define parametrized execution procedures of probers/listeners. Sequential or parallel tasks may include properties to be decomposed into different sets of instructions, for instance, when sampling cycles might define their repeated execution.

4. By interpreting action into a prober/listener execution, an Agent or Monitor performs an active or passive measurement to output metrics via a pluggable tool. A VNF developer can freely create a customized prober or listener to interface her tests and extract particular metrics. An interface of such a tool is automatically discovered by an Agent/Monitor and exposed as available to Managers and Players along with its corresponding execution parameters and output metrics.

5. After computing the required metrics, a set of evaluations (i.e., parsed action outputs) integrate a so-called snapshot sent from an Agent/Monitor to the Manager. A snapshot associated to a specific task is received from the Agent/Monitor that received the previous corresponding instruction. An evaluation contains timestamps and identifiers of the originating prober/listener, whereas a snapshot receives an Agent/Monitor unique identifier along the host name information from where it was extracted.

6. After processing all the instructions related tree of snapshots, the Manager composes a report, as a reply to each task requested by the Player. The Manager can sample snapshots in a diverse set of programmable methods. For instance, a task may require cycles of repetition, so the correspondent snapshots can be parsed and aggregated in a report through statistical operations (e.g., mean, variance, confidence intervals). Repetitions here concerns the amount of trials a specific tasks is configured to perform.

7. Finally, the Player processes the report following the VNF-PP metrics definition, as established initially during the VNF-BD decomposition. While the VNF-PP contains filtered evaluation metrics and parameters, snapshots can be aggregated/sampled into a report. Results can be exported in different file formats (e.g., formats CSV, JSON, YAML) or saved into a database for further analysis and visualization. For instance, in our current Gym prototype we integrate two popular open source components, the Elasticsearch database and the Kibana visualization platform 2 —tools providing high flexibility in querying, filtering and creation of different visual representations of the extracted VNF-PPs.


Logical View
************

For each main Gym module the following logic describes the most important classes, their organization and the most important use case realizations.

* common/asyncs: all the components utilize the App class in gym/common/asyncs/app.py file. It defines their how they load a web application using the aiohttp module. 

* Agent: interacts with Manager through the input of Instructions and output of Snapshots. As such, its main class loads probers via the common Actuator class instance, and instantiate them to execute Actions as needed. For that, Agent also makes use of Actuator, interfacing a Multiprocess instance. I.e., each prober, when called, defines a new process.
    
* Monitor: interacts with Manager through the input of Instructions and output of Snapshots. As such, its main class loads listeners via the common Actuator class instance, and instantiate them to execute Actions as needed. For that, Monitor also makes use of Actuator, interfacing a Multiprocess instance. I.e., each listener, when called, defines a new process.

* Manager: inputs Tasks and Outputs Reports to Player. While receiving a Task, decomposes it in multiple Instructions to its associated peers Agents and Monitors, as needed. A Task might require multiple trials, so Manager makes use of the Tasks class to schedule and execute multiple trials. At the end of all trials, it packs all snapshots from all trials into a report, and sends it to Player.

* Player: ...


Deployment View
***************

Gym is designed to be started from a jump server, only Player is instantiated and the other components will be instantiated according to an orchestration plugin, or with all components already deployed manually and Player will discover them at startup. Gym components must be reachable on the same logical network for the purposes of management and operations. Besides that, Agents should be on the same user/data plane network as the VNF under test. In the manual or automated case, such configurations must be performed.

Directory Structure
*******************

* build.sh: contains the installation scripts for all the gym modules, in addition to the scripts needed to install the gym dependencies and build a docker image.
* docs: all the documentation is stored in docs, included all the source files (.rst) needed to compile the html pages for readthedocs.
* examples: contains a README file on how to run gym examples, and for each test example (enabled by the run.sh script) it contains a folder referencing the layouts utilized.
* examples/utils: contains the script(s) that install the dependencies needed for the example tests (e.g., target VNF docker images, pcap source files, mininet/containernet).
* examples/cnet: contains the python script(s) that enable the containernet instantiation service to deploy the needed test scenarios of the example tests.
* gym: contains all the modules that contain the source code of all the components of Gym. I.e., agent, monitor, manager and player. 
* gym/common: contains all the common libraries shared and utilized by all the Gym components.
* gym/agent/probers: defines all the probers to be loaded by the Agent component, and enabled as capabilities for tests.
* gym/monitor/listeners:  defines all the listeners to be loaded by the Monitor component, and enabled as capabilities for tests. 
* gym/etc: defines all the VNF-BD source files to be loaded and used as recipes of tests by the Player component.