# V24: unbounded co-op message reassembly / server RAM exhaustion

Pinned upstream `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, `server/coop/coop_stream.h`.

**Concrete defect:** CoopStream::Receive appends reliable fragments to one vector without a size limit. A malicious peer may send an unlimited chain of fragments with LastChunk unset, exhausting server RAM before any protobuf validation can run.

Fix: switch to `sh_message_bounds.hpp` Assembler with an 8 MiB maximum per peer, drop an oversized message until its next last fragment, and reset on peer restart. Never interpret its tail as a valid new message. The guard is shared by server and client code. Complexity O(payload bytes) as before, constant extra state, no background CPU polling, no automatic bans.

8 MiB is a safe starting bound but the largest legit game snapshots should be measured before production deployment. A process with many connections still needs per-IP connection caps, authenticated session quotas, and packet parsing limits. Memory already consumed in lower framing stages also requires investigation.

Tests: standalone C++20 test includes oversized payload, indefinite fragments, reset during truncation, clean recovery. Python pinned source anchors must all match. GitHub safety CI includes both. Full Windows client and Linux/Qt server builds remain pending. Not deployed to production CLS/Fornex.
