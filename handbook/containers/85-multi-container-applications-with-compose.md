# Chapter 85 — Multi-Container Applications with Compose

A folder containing three container commands is not yet a reproducible system. The commands need one shared model for service identity, networks, state, configuration, dependency conditions, diagnostics, and teardown.

The central idea is:

> Treat a Compose application as a resolved project model whose services remain independently replaceable, and make readiness, data ownership, optional tooling, and cleanup explicit.

## 1. Compose declares a project

The Compose Specification describes a platform-neutral application model. A project can contain:

- services that create one or more containers;
- networks that connect selected services;
- volumes that own persistent data;
- configs and secrets granted to selected services;
- profiles that activate optional parts of the model;
- project metadata and implementation-specific extensions.

The Compose file is input. The resolved model—after file merge, interpolation, path resolution, defaults, and normalization—is what the implementation applies.

This chapter uses Docker Compose commands because they provide a common local implementation. Other Compose implementations can support different subsets or platform behavior. Validate against the implementation and version that will run the project.

## 2. Project identity scopes resources

Compose groups resources under a project name. Docker Compose derives that name through precedence including the command-line `--project-name` or `-p` flag, `COMPOSE_PROJECT_NAME`, a top-level `name`, and project-directory naming.

A project name helps distinguish:

- two developers running the same repository;
- parallel continuous-integration jobs;
- two worktrees or branches;
- a test project from a development project;
- project-owned networks and volumes from external resources.

Do not rely on the current directory name accidentally. Automation should provide a stable, unique, valid project name and use the same value for startup, inspection, and teardown.

## 3. A service is a role, not one permanent container

A service declares how instances of one application role should run. Its name becomes a useful network identity inside the project.

Container instances can be recreated when configuration or image identity changes. Therefore:

- address peers by service name, not container IP;
- keep durable state outside the writable container layer;
- send logs to observable streams or external stores;
- make startup and shutdown repeatable;
- avoid host-specific container names;
- tolerate replacement and reconnection.

The service name is part of the application topology. An individual container ID is runtime evidence, not a durable dependency.

## 4. Prefer service identity over `container_name`

Setting `container_name` creates a fixed engine-wide name and prevents ordinary scaling of that service in Docker Compose. It can also collide across projects and encourages scripts to bypass project-aware commands.

Prefer:

```bash
docker compose exec api sh
docker compose logs api
docker compose ps api
```

Inside the project network, clients should call `api:<container-port>`. Let Compose name individual containers and networks according to project scope.

## 5. Separate image construction from runtime topology

A service can reference an existing `image`, define a `build`, or use both according to implementation rules. Keep their responsibilities distinct:

- the Dockerfile produces an immutable application artifact;
- the image reference or digest identifies that artifact;
- the Compose service supplies runtime command, environment, mounts, networks, policy, and dependencies;
- the project connects several service roles.

Do not solve missing image content with a development bind mount in production. Do not bake deployment credentials or environment endpoints into the image merely because Compose can build it.

For repeatability, pin external base and service images under the policy from Chapters 80 and 81. A mutable tag in a Compose file is still mutable.

## 6. Inspect the resolved model before mutation

Docker Compose can parse, merge, interpolate, normalize, and render the effective model:

```bash
docker compose config --quiet
docker compose config
docker compose config --environment
docker compose config --images
docker compose config --networks
docker compose config --volumes
```

Use `config --quiet` as an early validation gate. Review the full rendered model before applying overrides. Treat output from `--environment` or the rendered model as potentially sensitive because interpolation can reveal configuration values.

Validation proves that Compose understands the model; it does not prove that images exist, ports are free, secrets are correct, dependencies are ready, or the application works.

## 7. Interpolation and container environment are different phases

Compose interpolation substitutes values into the model before containers are created. A container environment exists later and only contains values explicitly supplied by the image or service configuration.

```yaml
services:
  api:
    image: "example/api:${IMAGE_TAG:?set IMAGE_TAG}"
    environment:
      LOG_LEVEL: "${LOG_LEVEL:-info}"
```

`IMAGE_TAG` selects a model value. `LOG_LEVEL` is also inserted into the container environment because the service declares it there. A variable present in the host shell or `.env` file does not automatically enter the container.

Use required-value syntax for values that must not silently become empty. Document precedence and inspect it rather than relying on memory.

## 8. Environment files are configuration, not secret stores

The term “environment file” can describe two different roles:

- a Compose CLI `.env` or `--env-file` source used for model interpolation;
- a service `env_file` whose entries populate the container environment.

They have different resolution and precedence rules. The service `environment` mapping can override values from its `env_file`; command-line run overrides can take still higher precedence.

Environment values can appear in process inspection, diagnostic output, crash reports, rendered configuration, or child processes. Do not treat `.env`, `env_file`, or `environment` as a secure secret-delivery mechanism.

## 9. Grant configs and secrets explicitly

Top-level `configs` and `secrets` declare resources. A service receives one only when its own configuration grants access.

```yaml
services:
  api:
    secrets:
      - database_password

secrets:
  database_password:
    file: ./local-secrets/database-password.txt
```

This separates resource definition from service access, but the protection depends on the platform. A local Compose implementation can source a secret from a host file and mount it into a container; that does not imply an encrypted secret store, automatic rotation, audit trail, or safe source control.

Keep secret material outside the repository, restrict host access, use the platform's secret manager where available, and verify the effective mount, ownership, and rotation behavior.

## 10. Use networks to express intended paths

Compose creates a default project network when none is declared. Services on it can normally discover one another by service name.

For a stronger topology, declare purpose-specific networks:

```yaml
services:
  web:
    networks: [edge, application]
  api:
    networks: [application, data]
  database:
    networks: [data]

networks:
  edge: {}
  application: {}
  data: {}
```

This makes unnecessary paths visible during review. It does not replace application authentication or authorization.

Use network aliases deliberately and avoid relying on fixed container addresses. Chapter 84's namespace, DNS, and publication model still applies to each service.

## 11. Publish only host entry points

Services on the same Compose network reach one another at service name plus container port. They do not need host publication for that path.

Publish only entry points needed by a host or external client:

```yaml
services:
  web:
    ports:
      - "127.0.0.1:8080:8080"
  database:
    expose:
      - "5432"
```

`expose` documents container ports for network peers; it does not publish them to the host. Network peers can reach eligible listeners even without `expose` metadata.

For parallel development or tests, omit the host port and let the implementation choose one, then discover it with `docker compose port`.

## 12. Volumes have a project lifecycle

A top-level named volume is usually scoped under the project and can survive container replacement and ordinary `docker compose down`.

Declare ownership and mount mode:

```yaml
services:
  database:
    volumes:
      - database-data:/var/lib/database

volumes:
  database-data: {}
```

`docker compose down --volumes` intentionally removes declared named volumes and anonymous volumes for the project. That can permanently delete data. Do not add the flag mechanically to a production teardown.

External volumes and networks are not owned or removed by the project. Validate their existence, access policy, lifecycle owner, and compatibility separately.

## 13. Bind mounts usually mark a development boundary

Source-code bind mounts support rapid local editing, but they couple the service to a host path and can hide files supplied by the image.

Review every bind mount for:

- path resolution and portability;
- read-only versus read-write access;
- host ownership and security labels;
- ignored image content under the mount point;
- file-watching semantics across desktop virtualization;
- whether the mount appears in production unexpectedly.

Keep canonical runtime artifacts in the image. Put development-only mounts in an explicit override or development model and inspect the merged result.

## 14. Dependency order is not readiness

Short `depends_on` syntax establishes creation and removal order. It does not wait for a dependency's application to become ready.

Long syntax can express conditions:

- `service_started`: the dependency has started;
- `service_healthy`: its declared health check is healthy;
- `service_completed_successfully`: a one-shot dependency exited successfully.

```yaml
services:
  api:
    depends_on:
      migrate:
        condition: service_completed_successfully
      database:
        condition: service_healthy
```

The condition is only as good as the signal. A database accepting TCP may still be migrating; an HTTP 200 from a shallow endpoint may ignore unavailable dependencies.

## 15. Services must survive dependency turnover

Dependency gating improves initial convergence. It does not make a dependency permanently available after startup.

Application clients still need:

- bounded connection and request timeouts;
- reconnect and re-resolution behavior;
- backoff with jitter;
- retry-safe operations;
- circuit breaking or load shedding where appropriate;
- clear permanent-configuration errors;
- shutdown behavior when critical dependencies remain unavailable.

The `restart: true` field within long `depends_on` concerns explicit Compose operations on the dependency under documented behavior. It is not a substitute for runtime reconnect logic and is distinct from a service restart policy.

## 16. Health checks should test a meaningful local contract

A service health check runs inside the service container. Design it to be:

- bounded by a short timeout;
- inexpensive and safe to repeat;
- independent of optional external systems;
- specific enough to prove the process can perform its local role;
- supported by tools actually present in the image;
- tolerant of realistic startup time through `start_period` and retries.

Do not add a large shell or HTTP client solely for a health check without weighing image size and attack surface. An application-native probe can be better.

Health is a runtime signal, not a historical uptime guarantee. Chapter 86 separates liveness, readiness, and observability more fully.

## 17. Model migrations as explicit one-shot work

A migration is not merely “something the API does while starting.” It changes durable state and can have concurrency, compatibility, rollback, and privilege requirements.

A one-shot service with `service_completed_successfully` can make the dependency visible, but it does not automatically guarantee:

- exactly-once execution;
- exclusive ownership across two hosts or projects;
- transactional schema change;
- compatibility with old and new application versions;
- safe rollback;
- resumability after partial failure.

Make migrations idempotent or externally locked as required, record their version, and grant them narrower time-bounded credentials than the long-running application where possible.

## 18. Restart policy is not recovery design

A restart policy can recreate a process after failure. It cannot repair corrupt data, satisfy a missing secret, free a conflicting host port, make an incompatible dependency compatible, or decide whether repeating an operation is safe.

Avoid tight crash loops that consume resources and bury the first useful error. Preserve startup diagnostics, set a bounded dependency strategy, and escalate persistent failures.

Compose on one engine also cannot recover that application onto another machine when the host fails. That requirement belongs to a scheduler or another availability design.

## 19. Profiles keep optional services optional

Profiles can hide tools or workflows from the default application:

```yaml
services:
  api:
    image: example/api
  inspector:
    image: example/inspector
    profiles: [tools]
```

Services without profiles are enabled normally. A profiled service starts when its profile is enabled or when it is targeted directly under the implementation's rules; declared dependencies can also be started.

Good profile candidates include debuggers, administrative UIs, load generators, and one-off development helpers. Do not use profiles to conceal an undeclared mandatory dependency or create many untested topology combinations.

## 20. Multiple files create one merged model

Docker Compose can merge files supplied with repeated `-f` flags. Merge behavior varies by field: some values replace, some sequences concatenate, and mappings merge by key or mount target.

Important rules include:

- paths in override files are normally resolved relative to the base file;
- added `ports` entries can expose both old and new ports;
- environment entries merge by variable name;
- volume entries merge using container mount paths;
- an override fragment need not be a valid standalone project;
- file order changes the result.

Never approve an override by reading only the fragment. Render and review the final model with the exact file order used by automation.

## 21. Keep overrides few and testable

Useful layering might include:

- one canonical base application;
- one explicit development override;
- one continuous-integration override;
- a documented production-like single-host override when that deployment is supported.

Too many combinable fragments create a configuration state space that no one tests. Prefer a small number of named, validated compositions and generate evidence for each.

When component files need independent relative-path roots, evaluate the implementation's `include` support rather than forcing them into one ambiguous override chain.

## 22. Use the correct command for the lifecycle

Common Docker Compose operations have different intent:

| Command | Intended use |
| --- | --- |
| `config` | Resolve and validate the project model |
| `pull` / `build` | Obtain or construct service images |
| `up` | Create or reconcile and start project services |
| `ps` | Show project container state |
| `logs` | Read aggregated service output |
| `exec` | Run a command in an existing service container |
| `run --rm` | Create a one-off container from a service definition |
| `stop` / `start` | Stop or start existing containers without reconciling a new model |
| `down` | Remove project containers and project-owned networks |

Use `up --wait --wait-timeout <duration>` when the implementation supports it and health-based convergence is required. A successful command still needs an application-level verification for the workflow you care about.

## 23. Understand `exec` versus `run`

`docker compose exec api ...` enters an existing API container. It shares that instance's writable layer, mounts, environment, and current state.

`docker compose run --rm api ...` creates a new one-off container from the service definition. It can have different port behavior and lifecycle, and it may start declared dependencies. It does not inspect the exact existing instance.

Use `exec` for bounded diagnosis of a running instance. Use `run --rm` for tests, administrative commands, or one-shot work that should have a fresh container lifecycle. Do not mutate production state interactively without an auditable, recoverable procedure.

## 24. Logs need service and instance context

Compose can prefix aggregated logs with service and instance identity. Preserve that context when exporting output.

Useful observations include:

```bash
docker compose ps
docker compose logs --timestamps api
docker compose top api
docker compose port web 8080
docker compose events
```

Logs can contain secrets, tokens, personal data, and internal topology. Apply access, retention, and redaction policy.

Compose aggregation is convenient for a local project; it is not a durable observability platform. Host loss, container removal, or log rotation can remove evidence.

## 25. Teardown must match data ownership

Choose deliberately:

```bash
# Remove project containers and owned networks; keep named volumes
docker compose down --remove-orphans

# Also delete project-owned named and anonymous volumes
docker compose down --volumes --remove-orphans
```

Before destructive teardown, confirm:

- the project name and Compose files;
- which volumes are project-owned or external;
- whether data needs backup or retention;
- whether another job shares external resources;
- whether orphaned services should be removed;
- whether the selected engine context is correct.

Compose labels help identify project resources, but a unique project name and exact context remain essential safeguards.

## 26. Safe Compose lab: initialize, become healthy, call, and clean up

On an approved disposable Docker-compatible engine with Docker Compose, this Bash lab creates a unique project. A one-shot service initializes a named volume, an API waits on its successful completion and becomes healthy, and a client resolves the API by service name. The host publication uses a runtime-selected loopback port.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

suffix="$RANDOM-$$"
project="handbook-compose-$suffix"
temporary_root="${TMPDIR:-/tmp}"
work="$(mktemp -d "$temporary_root/handbook-compose.XXXXXX")"
file="$work/compose.yaml"

cleanup() {
  docker compose \
    --project-name "$project" \
    --file "$file" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true

  case "$work" in
    "$temporary_root"/handbook-compose.*)
      rm -rf -- "$work"
      ;;
    *)
      printf 'refusing to remove unexpected path: %s\n' "$work" >&2
      ;;
  esac
}
trap cleanup EXIT

cat > "$file" <<'YAML'
services:
  initialize:
    image: alpine:3.21
    command:
      - sh
      - -c
      - 'printf "compose-ready\n" > /site/index.html'
    network_mode: none
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    volumes:
      - site-data:/site

  api:
    image: alpine:3.21
    command: [httpd, -f, -p, "8080", -h, /site]
    depends_on:
      initialize:
        condition: service_completed_successfully
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    volumes:
      - site-data:/site:ro
    networks: [application]
    ports:
      - "127.0.0.1::8080"
    healthcheck:
      test: [CMD, wget, -qO-, http://127.0.0.1:8080/]
      interval: 1s
      timeout: 1s
      retries: 20
      start_period: 1s

  client:
    image: alpine:3.21
    command:
      - sh
      - -c
      - 'test "$$(wget -qO- http://api:8080/)" = "compose-ready"'
    depends_on:
      api:
        condition: service_healthy
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    networks: [application]

  inspector:
    image: alpine:3.21
    command: [sleep, "300"]
    profiles: [tools]
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    networks: [application]

networks:
  application: {}

volumes:
  site-data: {}
YAML

compose() {
  docker compose --project-name "$project" --file "$file" "$@"
}

compose config --quiet
compose config --services
compose up --detach --wait --wait-timeout 60 api
compose run --rm client

published="$(compose port api 8080)"
case "$published" in
  127.0.0.1:*) ;;
  *)
    printf 'unexpected publication: %s\n' "$published" >&2
    exit 1
    ;;
esac

compose ps
printf 'host endpoint: http://%s\n' "$published"
```

The default run does not create `inspector`; enable it only with `--profile tools` or target it explicitly. The client needs no host publication because it uses `api:8080` on the project network.

Cleanup permanently deletes the lab's uniquely scoped named volume. Run it only with the generated project name and disposable data. Image pulls can remain in the engine cache. Pin approved digests when the lab is used as reproducibility evidence.

## 27. Define a local-system acceptance contract

A project is not ready merely because `docker compose up` returned. Test at least:

1. the exact file set resolves without warnings or missing required values;
2. expected images or builds are identified and available;
3. one-shot initialization or migrations finish successfully;
4. health-gated services converge within a time budget;
5. service-name calls work on intended networks;
6. only approved host ports are published;
7. persistent data survives container recreation;
8. ordinary shutdown honors signal and timeout behavior;
9. logs identify service and instance;
10. teardown removes disposable resources while retaining owned durable data;
11. destructive reset removes only the intended project volumes;
12. the full workflow succeeds from a clean machine or clean engine context.

Store the commands and expected results in repository documentation or automation. Local tribal knowledge is not reproducibility.

## 28. Know where Compose stops

Compose is valuable for local development, integration testing, demonstrations, continuous-integration jobs, and deliberately operated single-engine systems.

It does not by itself provide a multi-host control plane for:

- rescheduling after host loss;
- distributed desired-state reconciliation;
- rolling deployment safety across a fleet;
- cluster-wide service discovery and ingress;
- node placement and capacity management;
- multi-host persistent-volume orchestration;
- policy admission and tenant isolation;
- automated certificate or secret lifecycle.

Do not label a Compose file “production-ready” without defining the host, availability, backup, upgrade, monitoring, and operator contracts around it. Chapter 88 develops orchestration foundations without assuming every application needs a cluster.

## Common Misconceptions

- “`depends_on` means the dependency is ready.” Short syntax guarantees order, not application readiness.
- “Every environment variable in `.env` enters the container.” Interpolation sources affect the model only where referenced.
- “Compose secrets are automatically encrypted.” Protection and storage depend on the implementation and source.
- “A published database port is needed for the API.” Services on the same network use the database service name and container port.
- “`down` deletes all project data.” Named volumes remain unless volume removal is requested; external resources remain externally owned.
- “An override replaces the base file.” Compose merges them field by field into one resolved model.
- “Compose is a lightweight multi-host orchestrator.” It can describe an application without providing a distributed control plane.

## Core Computer Science Concept

A Compose project is **declarative graph composition with scoped resource ownership**. Services are vertices; dependencies and network paths are distinct edges; volumes, configs, and secrets carry explicit ownership and access; reconciliation maps the resolved graph onto runtime objects.

## Engineering Connections

- Service-name connectivity applies Chapter 84's scoped discovery model.
- Image and build separation preserves the artifact chain from Chapters 79–81.
- Named-volume ownership extends Chapter 83's storage lifetime model.
- Health-gated dependencies still require Chapter 74's retry-safe client behavior.
- One-shot migrations are durable state transitions, not startup decoration.
- Project-scoped cleanup applies the bounded destructive-operation discipline from Part II.

## From the Field

A team starts its API, database, and cache with three shell commands. The API sometimes starts first, fails once, and remains down; every developer publishes all three services on common host ports; cleanup commands delete whichever volume name happens to match. A Compose project with health-gated dependencies, internal service-name endpoints, one host entry point, named data ownership, and a unique project name turns intermittent workstation behavior into a reviewable local system.

## Engineering Review

### What problem does this solve?

It gives a multi-container application one reproducible model for service identity, configuration, networks, data, dependency signals, observation, and teardown.

### Why was it designed this way?

Independent service roles need shared topology and lifecycle declarations while remaining replaceable and addressable by stable project-scoped identities.

### When should I use it?

Use Compose for local multi-service development, integration tests, disposable demonstrations, CI jobs, and intentionally managed single-engine deployments whose availability contract permits it.

### When should I avoid it?

Avoid treating Compose alone as a solution for multi-host scheduling, automatic host-failure recovery, fleet rollouts, tenant isolation, or platform-wide secret and policy management.

### How does this make me a better engineer?

It teaches you to distinguish graph order from readiness, interpolation from runtime environment, project ownership from external resources, and local reproducibility from distributed operations.

### How does this reduce waste?

It prevents port collisions, hand-run startup races, duplicated scripts, leaked development mounts, accidental shared-resource deletion, and local environments that cannot be reconstructed.

## Handbook Principle #85

> Compose the application as an owned, inspectable graph—and make every dependency condition, network path, state lifetime, and teardown decision explicit.

## Practical Observation

Run `docker compose config` for the exact file and environment set used by your team, then compare the resolved model with the running project. Execute the disposable lab where Compose is available, record its selected host port, confirm the optional profile remains absent, and observe which resources remain after ordinary `down` versus the lab's intentional `down --volumes` cleanup.

## Looking Ahead

Compose can declare health checks and restart policies, but operators still need to understand resource enforcement, OOM termination, health semantics, runtime events, logs, metrics, and the boundary between host and container evidence. Chapter 86 builds that operational diagnosis model.

## References

- [Compose Specification overview](https://compose-spec.github.io/compose-spec/00-overview.html)
- [Docker Compose file reference](https://docs.docker.com/reference/compose-file/)
- [Docker Compose services reference](https://docs.docker.com/reference/compose-file/services/)
- [Docker Compose networks reference](https://docs.docker.com/reference/compose-file/networks/)
- [Docker Compose volumes reference](https://docs.docker.com/reference/compose-file/volumes/)
- [Docker Compose secrets reference](https://docs.docker.com/reference/compose-file/secrets/)
- [Docker Compose startup and shutdown order](https://docs.docker.com/compose/how-tos/startup-order/)
- [Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/)
- [Docker Compose interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [Docker Compose merge behavior](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
- [Docker CLI `docker compose config`](https://docs.docker.com/reference/cli/docker/compose/config/)
- [Docker CLI `docker compose up`](https://docs.docker.com/reference/cli/docker/compose/up/)
- [Docker CLI `docker compose down`](https://docs.docker.com/reference/cli/docker/compose/down/)
