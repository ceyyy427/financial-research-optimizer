# Task 5 runtime service decision

`ResearchRuntimeService` now creates one `ResearchSupervisor` for the durable
queue during service construction. `submit()` only persists a task contract;
`run_until_terminal()` observes queue state and returns the durable terminal
record. Request threads do not construct `ResearchWorker` instances or call a
process context. Request recovery uses the explicit request and task resolver
callbacks; no request map is inherited by a worker or supervisor.

The Supervisor remains a long lived owner in this task and starts its control
loop before requests are served. A dedicated OS process plus a command IPC
channel for starting and stopping that Supervisor is deferred. The existing
Task 4 boundary already guarantees that all worker process creation is owned by
the Supervisor loop and that the SQLite queue is the restart boundary. Task 7
may add the process command channel without changing queue fences or the spawn
worker contract.

