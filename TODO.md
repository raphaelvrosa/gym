# List of TODOs:

* Info upgrade: define flag to update peers info. When called a peer must contacts
its peers and update its peers database (add/update/delete peers info profiles). 
A peer also must provide a session key hash for each of its peers, it must allow 
anonymous/ad-hoc calls to its service interfaces (i.e., messages from contacts not in peers database).
And a peer must retrieve info message acknoledging if peer was added or not (info message filled or not).

* Each component must have its jobs, one at a time. For instance an Agent must only accept an Intruction
per time, and deny any other calls until the current Instruction job is finished. Jobs must detail each peer
work being executed. Jobs will allow management interfaces (gRPC services) to retrieve info about jobs and cancel them.

* Upgrade messages with errors: every message must contain an Error (sub-message) with proper fields explaining the details of 
the errors. For instance, when an Agent cannot handle an Instruction because of having already a running job, it must
return an empty Snapshot with an Error message containing a proper message (e.g., Busy! Try again later.)

* Make tools be checked and installed: Before each trial/test manager must check the agents/monitors if their
tools are working correctly, so each tool must have its ways of checking their operational status (minimum unit test).
For instance, a ping must ping localhost and check the result metrics, or it must check that the ping tool is installed, 
and contains the proper permissions to be used/called. If the tool is not installed the tool might contain the scripts
that perform the installation of the tool. 