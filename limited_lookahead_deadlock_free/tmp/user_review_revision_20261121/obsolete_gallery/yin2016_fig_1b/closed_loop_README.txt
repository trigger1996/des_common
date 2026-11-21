Data flow: plant.json -> retained ll_bts.json -> supervisor.json -> closed_loop.json.
A single certified maximal pattern is fixed at each controller memory.
Closed-loop states pair a physical DFA state with controller memory.
Hidden events preserve memory; all enabled outcomes are included.
Safe Qe terminals use the enable-all continuation certified by the LL-BTS.
losing means no deadlock-free supervisor/closed-loop can be extracted.
