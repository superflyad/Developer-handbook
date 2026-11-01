# Chapter 44 — Virtual Memory and Process Address Spaces

A process does not normally address physical RAM directly. It operates in a virtual address space whose pages the operating system maps to physical memory, files, swap or pagefile backing, shared pages, or no storage until first use. This indirection provides isolation and flexible allocation, but makes memory numbers easy to misread.

The central idea is:

> Virtual address space describes possible mappings; resident memory describes pages currently in RAM; neither alone describes a process's unique physical cost.

## 1. Each process sees a private address space

Virtual addresses are translated through page tables into physical pages or other states. Two processes can use the same numeric virtual address while referring to different physical memory. Conversely, two address spaces can map the same physical page for shared libraries or explicit shared memory.

Mappings commonly include:

- executable code and libraries;
- stacks for threads;
- heap and other anonymous memory;
- memory-mapped files;
- shared-memory regions;
- reserved address ranges with no committed backing yet.

The address-space size is influenced by architecture and operating-system policy, not simply installed RAM. A large virtual range can be cheap if most pages are not resident or committed.

## 2. Pages are the unit of mapping and protection

Memory managers work in pages, commonly a few kibibytes, with optional larger-page facilities. Page-table entries encode whether a page is mapped, its protection, and where its content resides. Access to an unmapped or disallowed page triggers a fault that can become a process exception or signal.

A **page fault** is not automatically an error. Demand-zero allocation, copy-on-write, and loading a mapped file all use faults as normal control flow. A minor or soft fault can be satisfied without storage I/O; a major or hard fault requires a slower backing read. Terminology and counters vary by platform.

High fault count alone is not enough to diagnose memory pressure. Determine fault type, latency, reclaim activity, and workload impact.

## 3. Resident, virtual, committed, and private differ

Common measurements include:

- **virtual size:** address ranges mapped or reserved by a process;
- **resident set / working set:** process pages currently resident in physical memory;
- **committed memory:** memory for which the system has promised backing under its policy;
- **private memory:** pages not shareable with another process under the metric's definition;
- **proportional set size:** shared pages divided among processes, available in some Linux tooling.

These metrics do not form one portable schema. Windows working set, Linux RSS, macOS footprint, and container memory accounting have different definitions. Read the collector documentation before comparing dashboards.

Adding each process's resident value double-counts shared pages. Subtracting “free” RAM from total also misses file cache that the system can reclaim. Memory used for useful cache is not inherently wasted.

## 4. Anonymous and file-backed memory behave differently

File-backed clean pages can often be discarded and read again from the file. Dirty file-backed pages must be written before reuse. Anonymous pages such as heaps and stacks have no original file content; if evicted, they need swap or another backing strategy.

Systems can compress memory, page it to storage, reclaim caches, or terminate processes under severe pressure. Configuration and platform policy determine the balance. A host with no swap has different failure behavior, but adding swap is not a universal performance fix.

Memory-mapped files connect file I/O and virtual memory. Writes through a shared mapping affect file-backed pages according to API and synchronization semantics. Visibility and durability remain separate, just as in Chapter 41.

## 5. Copy-on-write delays copying

After Unix `fork`, parent and child can initially share physical pages marked copy-on-write. When one writes, the operating system gives it a private copy of the affected page. This makes process creation more efficient but means the memory cost can rise later.

File mappings, snapshots, virtual machines, and language runtimes use related techniques at other layers. Copy-on-write does not make mutable state magically synchronized; it specifically turns a shared mapping into private copies on write.

A large parent that forks and then changes many pages can consume far more memory than an initial snapshot suggests. This matters for prefork servers and background persistence strategies.

## 6. Pressure is a system condition, not one number

Memory pressure appears when active demand competes with reclaimable and backed capacity. Symptoms can include reclaim CPU, paging I/O, latency spikes, allocation failure, and process termination.

Observe at multiple scopes:

| Scope | Linux examples | macOS examples | Windows examples |
| --- | --- | --- | --- |
| System | `free -h`, `/proc/meminfo`, PSI | Activity Monitor, `vm_stat` | Task Manager, performance counters |
| Process | `ps`, `/proc/PID/status`, `smaps` | Activity Monitor, `vmmap` | `Get-Process`, VMMap, performance counters |
| Containment | cgroup memory files | platform policy | job, container, or VM limits |

Tools may require elevated access for another process's detailed maps. Do not collect sensitive memory dumps casually; process memory can contain credentials and personal data.

## 7. Out-of-memory behavior is policy-driven

Allocation can fail immediately, succeed virtually and fault later, trigger reclaim, or lead the operating system or container manager to terminate a process. Linux overcommit and OOM selection, Windows commit limits, macOS memory pressure, and orchestrator eviction policies differ.

An “OOM” incident report should include the scope that enforced the limit, victim selection evidence, requested allocation if known, workload growth, and reclaim or paging behavior. Restarting may restore service temporarily but loses the evidence needed to distinguish leak, load, fragmentation, limit, and working-set growth.

Memory leaks are retained unreachable or unnecessary allocations from the application's perspective; high stable cache use may be intentional. Use language-appropriate heap profiling and ownership analysis rather than inferring leaks from one resident-memory slope.

## Common Misconceptions

- “Virtual size is RAM consumed.” It includes nonresident, shared, and reserved ranges.
- “Free RAM should be maximized.” Reclaimable cache can improve performance.
- “Every page fault means disk I/O.” Many faults are satisfied from memory or demand-zero pages.
- “Adding process RSS gives system use.” Shared pages can be counted repeatedly.

## Core Computer Science Concept

Virtual memory is **address translation plus demand allocation**. It decouples a process's logical addresses from physical placement, enabling isolation, sharing, sparse allocation, and protection at page granularity.

## Engineering Connections

- Container memory limits can terminate a workload even when the host has available RAM.
- Memory-mapped databases rely on page-cache and durability behavior.
- Fork-based workers can share code efficiently but diverge through copy-on-write.
- Heap profiles explain application ownership; system metrics explain residency and pressure.

## From the Field

A dashboard sums RSS across 30 workers and reports more memory than the machine contains. Much of each worker's code and read-only data is shared, so the sum double-counts physical pages. The team adds proportional and private metrics, system pressure, and container-limit evidence before deciding whether worker count is actually unsafe.

## Engineering Review

### What problem does this solve?

It explains how processes receive isolated address spaces and how those mappings relate to physical memory and backing storage.

### Why was it designed this way?

Indirection enables protection, sharing, efficient sparse allocation, and flexible placement without exposing physical addresses to applications.

### When should I use it?

Use the model for memory dashboards, OOM incidents, process sizing, mapped files, worker models, and capacity decisions.

### When should I avoid it?

Avoid comparing platform metrics by label alone or declaring a leak from virtual or resident size without ownership evidence.

### How does this make me a better engineer?

It makes you distinguish address-space promises, current residency, shared cost, and pressure.

### How does this reduce waste?

It prevents false capacity alarms, inappropriate process restarts, and optimization of memory that is merely useful cache.

## Handbook Principle #44

> Interpret memory by mapping type, residency, sharing, and enforcement scope—not by one process number.

## Practical Observation

Choose one non-sensitive process you own and record its virtual and resident or working-set measurements with native tools. Compare that with system memory and explain why the values cannot simply be equated. Do not dump process memory or modify memory limits.

## Looking Ahead

Processes are isolated by default but still need to exchange data and coordinate. Chapter 45 compares local communication mechanisms by lifetime, framing, backpressure, and trust boundary.

## References

- [Linux `/proc` process memory fields](https://docs.kernel.org/filesystems/proc.html)
- [Linux `mmap(2)`](https://man7.org/linux/man-pages/man2/mmap.2.html)
- [Microsoft: Virtual Address Space](https://learn.microsoft.com/en-us/windows/win32/memory/virtual-address-space)
- [Microsoft: Working Set](https://learn.microsoft.com/en-us/windows/win32/memory/working-set)
