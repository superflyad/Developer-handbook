# Agent Answer Evaluation

Use this set to check whether an assistant can retrieve, summarize, and apply the handbook without losing important qualifications. It is a review aid, not a claim that any model has passed. Keep the questions independent of a particular provider.

These public questions are smoke checks. For a measured benchmark, add fresh scenarios whose expected answers were not available to the assistant during the run.

## Run a review

1. Start a fresh assistant session. Provide only the [chapter index](https://superflyad.github.io/Developer-handbook/llms.txt) and one question below. Do not paste the expected answer.
2. Ask the assistant to cite the chapter section and any primary source it uses. Let it state uncertainty rather than requiring an answer to every detail.
3. Compare the response with the linked chapter and its primary references. Record the model, date, repository revision, answer, citations, and reviewer notes.
4. Fix an incorrect or ambiguous source chapter through a reviewed pull request. Rerun the same question and keep both results.

Score each answer from 0 to 2 for **retrieval**, **technical accuracy**, **preserved limits**, **source traceability**, and **useful next step**. A score of 2 means the answer is correct and specific, 1 means incomplete but usable, and 0 means missing or misleading. Record an unsafe recommendation or invented citation as a critical failure regardless of the total score. Do not average away critical failures.

## Pilot questions

### Unix foundations

- **UNIX-1: A script runs `find . -name '*.log' | grep ERROR | wc -l`. What does it actually count, and how should it search the contents?** Expected: plain `find` emits paths; `grep` receives those path strings through the pipe. The [Chapter 1 example](handbook/foundations/01-thinking-like-a-unix-developer.md#3-small-tools-and-composition) uses `find -exec` to pass files as arguments.
- **UNIX-2: Will turning a manual process into a pipeline necessarily reduce errors?** Expected: no. Explain that the process must be understood and validated before automation. Use [Chapter 1's automation section](handbook/foundations/01-thinking-like-a-unix-developer.md#6-automation-over-repetition).
- **UNIX-3: When is shell composition a poor fit?** Expected: name rich interaction, tightly coupled transactions, or visual work without claiming pipelines are generally unsafe. See [Chapter 1's engineering review](handbook/foundations/01-thinking-like-a-unix-developer.md#engineering-review).

### DNS

- **DNS-1: An authoritative `A` record was corrected, but one office still receives NXDOMAIN. What should be checked before editing DNS again?** Expected: the office's configured resolver, cached negative answer, remaining TTL, query name and type, and authoritative response. See [Chapter 55's negative caching section](handbook/networking/55-dns-and-name-resolution.md#7-negative-answers-and-failures-are-not-one-result) and [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308).
- **DNS-2: `dig` returns the expected address, but the application cannot resolve the service. Does `dig` clear DNS as a cause?** Expected: no. The application may use a different resolver, search suffix, cache, address family, or split view. See [Chapter 55's stub resolver section](handbook/networking/55-dns-and-name-resolution.md#3-the-application-usually-asks-a-stub-resolver).
- **DNS-3: If DNSSEC validates a record, can the application skip TLS certificate or SSH host-key validation?** Expected: no. DNSSEC authenticates signed DNS data, not the application endpoint or operation. See [Chapter 55's trust section](handbook/networking/55-dns-and-name-resolution.md#9-dns-transport-is-not-dns-data-authenticity).

### S3 object lifecycle

- **S3-1: An object was overwritten yesterday. Can S3 Versioning recover the earlier bytes if versioning was enabled only today?** Expected: no. Versioning cannot recover an overwrite made before it was enabled. See [Chapter 97's versioning section](handbook/aws/97-s3-object-storage-and-data-lifecycle.md#10-versioning-makes-current-state-recoverable) and [AWS Versioning documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html).
- **S3-2: Three successful S3 `PUT` calls publish a release. Does strong consistency make the group transactional?** Expected: no. A reader can observe intermediate state; publish through an explicit manifest or another commit mechanism. See [Chapter 97's consistency section](handbook/aws/97-s3-object-storage-and-data-lifecycle.md#4-s3-is-strongly-consistent-but-not-multi-object-transactional).
- **S3-3: Can an S3 event notification be used as proof that a billing side effect ran exactly once?** Expected: no. Delivery is at least once and can be out of order; the consumer needs idempotency and recovery. See [Chapter 97's events section](handbook/aws/97-s3-object-storage-and-data-lifecycle.md#18-events-require-idempotent-order-aware-consumers) and [AWS event notification documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html).

## Review record

For each run, record the question ID, model and version, date, repository commit, five scores, critical failures, and the exact unsupported or missing claim. Do not publish a pass rate until the review has been run against a recorded revision. Expand this set when readers report a misleading recap or a new chapter introduces a consequential distinction.
