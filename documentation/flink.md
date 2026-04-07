Basic setup present at: https://nightlies.apache.org/flink/flink-docs-stable/docs/try-flink/local_installation/

- installed it locally via `brew install maven`

- skeleton created via: `mvn archetype:generate`

- Running instructions of App.java
```
cd flink-jobs/order-stream-job
mvn compile                          # compiles .java → .class files
mvn exec:java -Dexec.mainClass="com.dataeng.App"   # runs it
```

---

# Understanding Maven, Flink, and How They Fit This Repo

## 1. What is a Maven Project?

Think of Maven as the **pip + setuptools of Java**. In Python, you have `requirements.txt` or `pyproject.toml` to declare dependencies, and `pip install` to fetch them. In Go, you have `go.mod`. Maven is Java's equivalent.

A typical Maven project looks like this:

```
my-project/
├── pom.xml                          <-- the "requirements.txt" of Java
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/mycompany/       <-- your actual code goes here
│   │           └── App.java
│   └── test/
│       └── java/
│           └── com/mycompany/       <-- your test files go here
│               └── AppTest.java
└── target/                          <-- generated after you build (like dist/ or bin/)
    └── my-project-1.0.jar           <-- the final compiled output
```

**The flow:**

1. You write `.java` files under `src/main/java/`
2. You run `mvn compile` — Maven downloads dependencies, compiles your code
3. You run `mvn package` — Maven compiles + bundles everything into a `.jar` file under `target/`
4. The `.jar` file is like a `.whl` in Python or a Go binary — it's the thing you deploy/run

**Key difference from Python:** In Python you write `.py` files and run them directly (`python app.py`). In Java, you compile first (`.java` -> `.class` -> `.jar`), then run the JAR (`java -jar app.jar`).

---

## 2. What is pom.xml?

`pom.xml` (Project Object Model) is the single config file that controls everything about your Maven project. It's like combining `requirements.txt` + `Makefile` + `setup.py` into one file.

It has a few key sections:

**Identity** — who is this project?
```xml
<groupId>com.dataeng</groupId>        <!-- like a Python package namespace -->
<artifactId>order-stream-job</artifactId>  <!-- the project name -->
<version>1.0-SNAPSHOT</version>        <!-- version number -->
```

Think of `groupId:artifactId` like a Python import path. `com.dataeng:order-stream-job` uniquely identifies your project, just like `pip install my-package` uniquely identifies a PyPI package.

**Properties** — global settings
```xml
<properties>
    <maven.compiler.release>11</maven.compiler.release>   <!-- Java version -->
</properties>
```

**Dependencies** — what libraries do you need?
```xml
<dependencies>
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-streaming-java</artifactId>
        <version>1.18.1</version>
    </dependency>
</dependencies>
```

This is like adding `flink-streaming==1.18.1` to `requirements.txt`. Maven downloads the JAR from Maven Central (like PyPI for Java).

**Scope** — when is this dependency needed?
- `<scope>provided</scope>` — "the runtime environment already has this, don't bundle it." Flink's core libraries use this because the Flink cluster already has them installed. It's like how you don't bundle Python itself inside your `.whl` file.
- `<scope>test</scope>` — only needed for tests, not in the final JAR.
- No scope (default) — bundle it into the final JAR because it won't be available at runtime.

**Build plugins** — how to build the project?
- `maven-shade-plugin` — creates a "fat JAR" (also called an uber-jar) that bundles ALL your dependencies into a single JAR file. Without this, your JAR would only have your code, and you'd need to manually provide every dependency JAR at runtime.

---

## 3. What is Flink?

**One-line answer:** Flink is a framework for processing streams of data in real time, at scale.

**The analogy:** Imagine a conveyor belt in a factory. Items (events) arrive one by one on the belt. Workers (operators) stand along the belt — one worker inspects each item, another stamps it, another sorts it into different boxes. The belt never stops. That's Flink.

Compare this to **batch processing** (what Spark does well): batch processing is like receiving a truck full of items, dumping them all on a table, sorting them all at once, then shipping. You wait for the truck to arrive, process everything, then wait for the next truck.

**Flink = conveyor belt (continuous, real-time)**
**Spark = truck deliveries (periodic batches)**

### Why do industries use Flink?

| Use Case | What Happens | Why Not Batch? |
|----------|-------------|----------------|
| Fraud detection | Bank monitors every credit card transaction as it happens. Flag suspicious ones within milliseconds. | By the time a batch runs (every hour), the fraudster has already spent the money. |
| Ride-sharing surge pricing | Uber/Ola calculates demand per area in real time to adjust prices. | Stale pricing = lost revenue or angry customers. |
| IoT / sensor monitoring | Factory sensors stream temperature readings. Alert if a machine overheats. | A 15-minute delay on an overheating alert could mean equipment damage. |
| Real-time dashboards | E-commerce site shows live order count, revenue, trending products. | Users expect live numbers, not numbers from an hour ago. |
| Log processing | Aggregate application logs in real time, detect error spikes immediately. | Waiting for a batch to detect a production outage means longer downtime. |

- When you want real time data processing like fraud detection, we use Flink real time streaming data pipelines (stream processing)

### Example flow — Fraud Detection:

```
Credit card swipes (events)
    → Kafka topic "transactions"
        → Flink job:
            - Parse each transaction
            - Check: amount > $5000? foreign country? 3 swipes in 1 minute?
            - If suspicious → send to "alerts" topic
            - If normal → write to data lake for analytics
```

---

## 4. How Flink and Kafka Connect in This Repo

Your understanding is correct. Here's the before and after:

**Phase 2 (what you built):**
```
Python producer → Kafka "orders" → Python consumer (order_consumer.py) → Delta Lake
```

The Python consumer uses `KafkaBatchConsumer` to poll Kafka, accumulate messages, convert to a Spark DataFrame, and call `DeltaClient.write()`. It works, but:
- It's a simple poll loop — no parallelism, no fault tolerance
- If it crashes, you might lose or double-process messages
- It can't easily do transformations like splitting streams

**Phase 3 (what Flink replaces it with):**
```
Python producer → Kafka "orders" → Flink job (Java) → Delta table: "orders" (active)
                                                     ↘ Delta table: "orders_cancelled"
```

Flink replaces `order_consumer.py`. But it does more:
- **Reads from Kafka** using its built-in Kafka connector (like your `KafkaBatchConsumer`, but battle-tested and parallel)
- **Splits the stream** — active orders go to one Delta table, cancelled orders go to another. In Python you'd need to write this logic manually; in Flink it's a simple `.filter()`
- **Writes to Delta Lake** using the `delta-flink` connector (replaces your `DeltaClient`)
- **Handles failures** — if it crashes, it restarts from a checkpoint (a saved snapshot of progress), so no data is lost or duplicated

The Python consumer stays in the repo as a simpler alternative / learning reference, but Flink is the "production-grade" version.

---

## 5. How Does Flink Actually Work?

### The Core Idea: Dataflow Graphs

When you write a Flink job, you're describing a pipeline (a directed graph) of operations:

```
[Source] → [Transform] → [Transform] → [Sink]
```

For our job:
```
[Kafka Source] → [Deserialize JSON to OrderEvent] → [Filter: not cancelled] → [Delta Sink: /orders]
                                                   → [Filter: cancelled]     → [Delta Sink: /orders_cancelled]
```

Flink takes this graph and distributes it across multiple machines (or threads). Each step runs in parallel.

### Key Concepts

**Streams and Operators:**
A stream is an unbounded sequence of events (it never ends, unlike a file). An operator is a function applied to each event — map, filter, aggregate, join, etc. If you know Python generators or Go channels, a Flink stream is similar — events flow through, one at a time, forever.

**Parallelism:**
Say your Kafka topic has 3 partitions. Flink can run 3 parallel instances of the Kafka source, each reading from one partition. The downstream operators also run in parallel. This is like having 3 conveyor belts side by side instead of 1.

**Checkpointing (how it survives crashes):**
Every N seconds, Flink takes a "snapshot" of where each operator is — which Kafka offset it has read up to, what's in any internal buffers, etc. This snapshot is saved to durable storage (in our case, MinIO at `s3a://lakehouse/_checkpoints/`).

If the job crashes and restarts:
1. Flink loads the last checkpoint
2. Kafka source resumes from the saved offset (not from the beginning)
3. No events are lost, no events are double-processed

This is called **exactly-once processing** — and it's the main reason people use Flink over a simple Python consumer loop.

**Watermarks (handling late/out-of-order events):**
Events might arrive out of order (event A happened at 10:01 but arrives at 10:05, while event B happened at 10:02 but arrived at 10:03). Watermarks are Flink's way of saying "I believe all events up to time T have arrived, so I can safely process them." For our simple use case, this isn't critical, but it matters a lot for windowed aggregations (e.g., "count orders per minute").

### Flink Architecture

```
┌─────────────────────────────────────────┐
│              JobManager                  │
│  (the "brain" — schedules tasks,         │
│   manages checkpoints, handles failures) │
└──────────────┬──────────────────────────┘
               │ assigns work to
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│TaskMgr │ │TaskMgr │ │TaskMgr │
│ slot 1 │ │ slot 1 │ │ slot 1 │
│ slot 2 │ │ slot 2 │ │ slot 2 │
└────────┘ └────────┘ └────────┘
  (workers that actually run your code)
```

- **JobManager** = the coordinator. Like a Spark driver or a Kubernetes control plane. There's one per cluster.
- **TaskManager** = the workers. Each has "slots" (threads). Each slot runs one parallel instance of an operator. In our Docker setup, we'll have 1 JobManager + 1 TaskManager with enough slots for both sinks.

For our local setup, everything runs on one machine, but the architecture is the same as a 100-node production cluster.

---

## 6. Mapping to Python/Go Concepts You Already Know

| Java / Maven / Flink | Python Equivalent | Go Equivalent |
|-----------------------|-------------------|---------------|
| `pom.xml` | `requirements.txt` + `setup.py` | `go.mod` |
| `mvn compile` | (not needed, Python is interpreted) | `go build` |
| `mvn package` → `.jar` | `python setup.py bdist_wheel` → `.whl` | `go build` → binary |
| `maven-shade-plugin` (fat JAR) | `PyInstaller` (bundled executable) | (Go statically links by default) |
| `<scope>provided</scope>` | Library pre-installed in the runtime | Build tags / conditional compilation |
| Maven Central | PyPI | Go module proxy |
| `groupId:artifactId` | package name on PyPI | module path in `go.mod` |
| `.java` → `.class` → `.jar` | `.py` → runs directly | `.go` → binary |
| Flink streaming | `KafkaBatchConsumer` (your Python version) | goroutines reading from channels |
| Flink checkpoint | manually saving Kafka offsets | no direct equivalent |
| Flink parallelism (slots) | multiprocessing pool | goroutines |

---

## 7. What Dependencies Do We Need and Why?

For our Flink job in `pom.xml`, we need 4 groups of dependencies:

| Dependency | What It Does | Scope |
|-----------|-------------|-------|
| `flink-streaming-java` | Core Flink streaming API — lets you build the pipeline (source → transform → sink) | `provided` — the Flink cluster already has this |
| `flink-connector-kafka` | Kafka source connector — lets Flink read from Kafka topics | default — bundle it, Flink doesn't ship with Kafka support out of the box |
| `delta-flink` (from `delta-io`) | Delta Lake sink for Flink — lets Flink write Parquet files in Delta format to S3/MinIO | default — bundle it |
| `hadoop-aws` + `aws-java-sdk-bundle` | S3A filesystem — lets Flink (and Delta) talk to MinIO using the `s3a://` protocol | default — bundle it |
| `flink-parquet` | Parquet format support — Delta stores data as Parquet files, Flink needs this to write them | default — bundle it |

The `provided` vs default scope distinction is important:
- Flink's own JARs (`flink-streaming-java`, `flink-clients`) are already inside the Flink Docker container. If you bundle them again in your fat JAR, you get version conflicts.
- Everything else (Kafka connector, Delta, Hadoop AWS) is NOT in the Flink container, so you must bundle them.

---

## 8. Delta Lake Sink vs Delta Table with Version History

These are two sides of the same coin — one is the **writer**, the other is the **result**.

**Delta Sink (the writer):**
This is a Flink component — a piece of code that knows how to take a stream of events and write them as Parquet files in the Delta format to a storage path (like `s3a://lakehouse/orders`). Think of it as the "pen" — it writes data, manages file layout, and appends entries to the Delta transaction log (`_delta_log/`). In our Flink job, `DeltaSink` is what we attach at the end of the pipeline. It's the equivalent of calling `DeltaClient.write()` in your Python code.

**Delta Table (the result):**
This is what exists on disk (MinIO) after the sink writes. It's a folder containing:
```
s3a://lakehouse/orders/
├── _delta_log/                    <-- transaction log (the "version history")
│   ├── 00000000000000000000.json  <-- version 0: initial write
│   ├── 00000000000000000001.json  <-- version 1: next batch
│   └── ...
├── part-00000-xxxx.parquet        <-- actual data files
├── part-00001-xxxx.parquet
└── ...
```

The `_delta_log/` folder is what gives you version history. Each JSON file in it records what happened in that version — which Parquet files were added, which were removed, what the schema was. This is what enables:
- **Time travel**: read the table as it was at version 5
- **`get_history()`**: see all changes ever made
- **ACID transactions**: concurrent readers and writers don't corrupt each other

**The relationship:**
- The **Delta Sink** (Flink) and **DeltaClient.write()** (Python/Spark) both write to the same Delta table format. They both produce Parquet files and append to `_delta_log/`.
- The **Delta Table** is the shared result — regardless of whether Flink or Spark wrote it, anyone can read it using Spark, Flink, or any Delta-compatible tool.
- In your pipeline: Flink's Delta Sink writes → Spark's `DeltaClient.read()` reads. They're interoperable because they both speak the Delta protocol.

**Analogy:** A Delta Sink is like a bank teller (processes deposits). A Delta Table is like your bank account (has balance + transaction history). Different tellers (Flink, Spark, Python) can all deposit to the same account, and the ledger keeps a record of every transaction.

---

## 9. How Does Flink Handle Millions of Records in Streaming?

Short answer: **it divides the work across many workers and processes everything in memory, without waiting.**

### a) Parallelism — divide and conquer

Imagine you have a Kafka topic with 12 partitions, each receiving thousands of events per second. Flink doesn't read all 12 partitions with one thread. It spins up 12 parallel "sub-tasks", each reading from one partition independently.

```
Kafka partition 0  →  Flink subtask 0  →  filter  →  sink
Kafka partition 1  →  Flink subtask 1  →  filter  →  sink
Kafka partition 2  →  Flink subtask 2  →  filter  →  sink
...
Kafka partition 11 →  Flink subtask 11 →  filter  →  sink
```

Each subtask runs on a separate thread (slot) on a TaskManager. If one machine isn't enough, you add more TaskManagers — Flink spreads the subtasks across them. This is horizontal scaling — the same way a web app handles more traffic by adding more servers behind a load balancer.

### b) In-memory processing — no disk round-trips

Unlike Spark (which writes intermediate results to disk between stages), Flink keeps data in memory and passes events directly from one operator to the next through in-memory buffers. An event flows from Kafka source → deserializer → filter → sink without ever touching disk in between.

Think of it like a factory assembly line: items pass hand-to-hand between workers standing next to each other. Nobody walks to a warehouse to drop off and pick up items between steps.

### c) Pipelining — no waiting between stages

In Spark batch processing, stage 1 has to finish completely before stage 2 starts. In Flink, all stages run simultaneously. While subtask 0 is reading event #1000, the filter operator is already processing event #999, and the sink is already writing event #998. Everything overlaps.

This is like a restaurant kitchen: the cook doesn't wait for all orders to be taken before starting to cook. The waiter takes order #5 while the cook prepares order #3 while the runner delivers order #1.

### d) Backpressure — automatic speed control

What if the sink is slower than the source? (e.g., MinIO is slow to write, but Kafka has millions of events queued up.) Flink doesn't crash or drop events. Instead, it slows down the upstream operators automatically — the Kafka source pauses polling until the sink catches up. This is called backpressure.

It's like a highway on-ramp meter light — when the highway (downstream) is congested, the light turns red to slow down cars entering (upstream), preventing a pile-up.

### Putting it together for our repo:

Our setup is small (1 TaskManager, 3 Kafka partitions), but the architecture is identical to a production cluster processing millions of events/second. The only difference is scale — more partitions, more TaskManagers, more slots.

---

## 10. Stateless vs Stateful Processing

### Stateless processing — "process and forget"

A stateless operator looks at each event in isolation, does something with it, and moves on. It has no memory of previous events.

**Example in our repo:** The `filter` operator that splits orders into active/cancelled. For each event, it just checks: `is status == "cancelled"?` and routes it. It doesn't need to know anything about previous events.

```
Event: {order_id: "ORD-0042", status: "cancelled"}  →  Filter checks status  →  route to cancelled sink
Event: {order_id: "ORD-0043", status: "shipped"}     →  Filter checks status  →  route to active sink
```

Each event is processed independently. If you shuffled the order, the result would be the same.

**Python analogy:** This is like a simple `for` loop with an `if` statement:
```python
for event in stream:
    if event["status"] == "cancelled":
        write_to_cancelled(event)
    else:
        write_to_active(event)
```

No variables carried between iterations — pure stateless.

### Stateful processing — "remember and reason"

A stateful operator keeps some memory (state) across events. It needs to "remember" things to produce correct results.

**Example 1 — Counting orders per customer:**
To compute "Customer X has placed 5 orders so far," Flink needs to remember the running count for each customer. Each new event updates that count. The count is the state.

```
Event: {customer: "Alice", ...}  →  state[Alice] = 1  →  emit: Alice has 1 order
Event: {customer: "Bob", ...}    →  state[Bob] = 1    →  emit: Bob has 1 order
Event: {customer: "Alice", ...}  →  state[Alice] = 2  →  emit: Alice has 2 orders
```

**Example 2 — Fraud detection (3 swipes in 1 minute):**
To detect "3 credit card swipes in 1 minute," Flink must remember the last few swipes for each card. It stores recent swipe timestamps per card_id — that's state.

**Example 3 — Deduplication:**
To ensure each `order_id` is processed only once, Flink keeps a set of seen IDs. For each new event, it checks: "have I seen this ID before?" That set is state.

**Python analogy:** This is like a `for` loop with variables that persist between iterations:
```python
counts = {}   # <-- this is "state"
for event in stream:
    customer = event["customer"]
    counts[customer] = counts.get(customer, 0) + 1
    print(f"{customer} has {counts[customer]} orders")
```

### Why does the distinction matter?

Stateless operators are simple and cheap — they need no memory, no checkpointing of state. Stateful operators are powerful but come with a cost: Flink must save their state to checkpoints, so if the job crashes, it can restore the state and continue correctly.

**In our repo:** Our Phase 3 Flink job is mostly stateless (filter + write). But the Delta Sink itself is internally stateful — it tracks which files it's writing and what's been committed. Flink's checkpointing system handles this transparently.

---

## 11. Fault Tolerance — What Happens When Things Fail?

Flink's fault tolerance is built on **checkpoints** + **replayable sources**. Here's how different failure scenarios play out:

### Scenario 1: Flink job crashes (e.g., out of memory, bug, TaskManager dies)

```
Timeline:
  checkpoint @ offset 500  →  processed up to offset 750  →  CRASH

What happens:
  1. JobManager detects the failure
  2. Restarts the failed task (or the whole job if needed)
  3. Loads the last checkpoint (offset 500)
  4. Kafka source replays from offset 500
  5. Events 500-750 are reprocessed
  6. Processing continues from 750+
```

Events 500-750 are processed twice — but the Delta Sink uses **exactly-once semantics**: it only commits files that weren't committed before the crash. So the Delta table sees no duplicates.

**Analogy:** You're reading a book and your bookmark falls out. You go back to the last page you remember for sure (the checkpoint), re-read a few pages you'd already read, and continue. You didn't miss anything, and you didn't read the book twice.

### Scenario 2: Downstream fails (e.g., MinIO is down, Delta write fails)

```
Timeline:
  Kafka source reads event  →  filter routes it  →  Delta Sink tries to write  →  FAILS

What happens:
  1. The sink throws an exception
  2. Flink does NOT commit the Kafka offset for this event
  3. Flink retries the task (configurable retry count and delay)
  4. If MinIO comes back, the retry succeeds — event is written, offset committed
  5. If retries are exhausted, the job fails → restarts from last checkpoint
```

The key guarantee: **an event's Kafka offset is only committed after it's been successfully written to the sink.** If the write fails, the offset stays uncommitted, so the event will be reprocessed on restart. No data is lost.

**Analogy:** A bank transfer between two accounts. The money is only deducted from account A after it's confirmed in account B. If the transfer to B fails, account A keeps the money — nothing is lost, you just retry.

### Scenario 3: Kafka goes down

```
What happens:
  1. Flink's Kafka source can't poll — it keeps retrying
  2. Backpressure kicks in — downstream operators idle, no data flowing
  3. Checkpoints continue (they just save "I'm at offset X, waiting")
  4. When Kafka recovers, source resumes polling from where it left off
  5. No data loss — Kafka persists messages on disk, they're still there
```

Flink doesn't crash because Kafka is down. It just waits. Like a conveyor belt that pauses when the loading dock is closed — the belt doesn't break, it just stops until the dock opens again.

### How checkpoints tie it all together

```
┌─────────────┐     ┌──────────┐     ┌────────────┐
│ Kafka Source │ ──→ │  Filter  │ ──→ │ Delta Sink │
│ offset: 500 │     │ (no state)│    │ pending: [] │
└─────────────┘     └──────────┘     └────────────┘
        │                                    │
        └──── CHECKPOINT saved to MinIO ─────┘
              (offset=500, sink=committed)

... 250 more events processed ...

┌─────────────┐     ┌──────────┐     ┌────────────┐
│ Kafka Source │ ──→ │  Filter  │ ──→ │ Delta Sink │
│ offset: 750 │     │ (no state)│    │ pending: [3 files] │
└─────────────┘     └──────────┘     └────────────┘

                    💥 CRASH 💥

Recovery:
  → Load checkpoint: offset=500, sink=committed
  → Kafka replays from 500
  → Delta sink discards any uncommitted files from the crash
  → Reprocess 500-750, this time successfully
  → Continue from 750+
```

### Summary table

| What Fails | What Happens | Data Lost? | Data Duplicated? |
|-----------|-------------|-----------|-----------------|
| Flink task crashes | Restart from last checkpoint, replay from Kafka | No | No (exactly-once sink) |
| MinIO / Delta write fails | Retry, then restart from checkpoint if retries exhausted | No | No |
| Kafka goes down | Flink pauses and waits, resumes when Kafka recovers | No | No |
| JobManager crashes | Standby JobManager takes over (HA mode), or manual restart | No (checkpoints persist on MinIO) | No |
| Everything crashes at once | Restart everything, Flink loads checkpoint from MinIO, Kafka replays | No (as long as checkpoints + Kafka data survive) | No |

This is why Flink is used in production for financial systems, fraud detection, and other scenarios where losing or duplicating even one event is unacceptable.


- Go into the folder using: 
```
docker exec -it dataeng_devops-jobmanager-1 bash
```

- Run the flink job using: 
