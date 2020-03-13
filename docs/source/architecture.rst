Architecture
============

Gym architecture is composed of 4 main elements: Agent, Monitor, Manager, Player.
They form an hierarchical structure which allows modular test topologies.
Some observations are important here:

* All the components communicate through REST APIs, realizing the specific interfaces to the messages they can handle only;
* Components exchange Hello/Info messages with each other to discover their peer features/capabilities and interact with each other using the "keys" obtained from this initial handshake;
* Agent and Monitor only communicate with Manager, and Manager only communicates with Player.


Definitions: 

* **VNF Benchmarking Descriptor (VNF-BD)**: contains all required definitions and requirements to deploy, configure, execute, and reproduce VNF benchmarking tests.  VNF-BDs are defined by the developer of a benchmarking methodology and serve as input to the benchmarking process, before being included in the generated VNF-BR.

* **VNF Performance Profile (VNF-PP)**:  contains all measured metrics resulting from the execution of a benchmarking.  Additionally, it  might also contain additional recordings of configuration parameters used during the execution of the benchmarking scenario to facilitate comparability of VNF-BRs.

* **VNF Benchmarking Report (VNF-BR)**: correlates structural and functional parameters of VNF-BD with extracted VNF benchmarking metrics of the obtained VNF-PP.



Agent
*****

An Agent executes active stimulus using extensible and modular interfaces to probers to benchmark and collect network and system performance metrics. While a single Agent is capable of performing localized benchmarks in execution environments (e.g., stress tests on CPU, memory, disk I/O), the interaction among distributed Agents enable the generation and collection of VNF end-to-end metrics (e.g., frame loss rate, latency). In a benchmarking setup, one Agent can create the stimuli and the other end be the VNF itself where, for example, one-way latency is evaluated. An Agent can be defined by a physical or virtual network function. Agents expose modular APIs for flexible extensibility (e.g., new probers). Agents receive Instructions from a Manager defining sets of actions to consistently configure and run prober instances, parse the results, and send back Snapshots containing output evaluations of the probers’ actions.

**Prober -** Defines a software/hardware-based tool able to generate stimulus traffic specific to a VNF (e.g., sipp) or generic to multiple VNFs (e.g., pktgen). A prober must provide programmable interfaces for its life cycle management workflows, e.g., configuration of operational parameters, execution of stimuli, parsing of extracted metrics, and debugging options. Specific probers might be developed to abstract and to realize the description of particular VNF benchmarking methodologies.

Implementation: 

* Inputs: a Instruction type of message, containing Actions that refer to triggering specific probers and their custom parameters. 
* Outputs: a Snapshot type of message, containing Evaluations (in reference to each Action inside the input Instruction) that contain metrics and the source of them (i.e., the prober specifications).


Monitor
*******

When possible, it is instantiated inside the target VNF or NFVI PoP (e.g., as a plug-in process in a virtualized environment) to perform passive monitoring/instrumentation, using listeners, for metrics collection based on benchmark tests evaluated according to Agents’ stimuli. Different from the active approach of Agents that can be seen as generic benchmarking VNFs, Monitors observe particular properties according to NFVI PoPs and VNFs capabilities. A Monitor can be defined as a virtual network function. Similarly to the Agent, Monitors interact with the Manager by receiving Instructions and replying with Snapshots. Different from the generic VNF prober approach of the Agent, Monitors may listen to particular metrics according to capabilities offered by VNFs and their respective execution environment (e.g. CPU cycles of DPDK-enabled processors).

**Listener -** Defines one or more software interfaces for the extraction of particular metrics monitored in a target VNF and/or execution environment. A Listener must provide programmable interfaces for its life cycle management workflows, e.g., configuration of operational parameters, execution of monitoring captures, parsing of extracted metrics, and debugging options. White-box benchmarking approaches must be carefully analyzed, as varied methods of performance monitoring might be coded as a Listener, possibly impacting the VNF and/or execution environment performance results.

Implementation: 

* Inputs: a Instruction type of message, containing Actions that refer to triggering specific listeners and their custom parameters. 
* Outputs: a Snapshot type of message, containing Evaluations (in reference to each Action inside the input Instruction) that contain metrics and the source of them (i.e., the listener specifications).


Manager
*******

Responsible for (i) keeping a coherent state and consistent coordination and synchronization of Agents and Monitors, their features and activities; (ii) interacting with the Player to receive tasks and decompose them into a concrete set of instructions; and (iii) processing snapshots along proper aggregation tasks into reports back to the Player.


Implementation: 

* Inputs: a Task type of message, containing parameters for Agents and Monitors realize Instructions. 
* Outputs: a Report type of message, containing sets of Spanshots (possibly from different Agents and/or Monitors) that refer to a single Task.


Player
******

Defines a set of user-oriented, north-bound interfaces abstracting the calls needed to manage, operate, and build a VNF-BR. Player can store different VNF Benchmarking Descriptors, and trigger their execution when receiving a testing Layout request that might reference one or more parametrized VNF-BDs, which are decomposed into a set of tasks orchestrated by Managers to obtain their respective reports. Interfaces are provided for storage options (e.g., database, spreadsheets) and visualization of the extracted reports into VNF-PPs.

Implementation: 

* Inputs: a Layout type of message, containing a reference of a VNF Benchmarking Descriptor and its input parameters. 
* Outputs: a Result type of message, containing a VNF Benchmarking Report.  
