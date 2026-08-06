# Captain Thermo — deployment architecture

All figures are measured against the live deployment, not estimated.

## Request flow

The thing worth reading here is which paths cost money. Two of the four tools
never reach the API at all, and the two that do sit behind separate prompt
caches that are the dominant cost driver.

```mermaid
flowchart TB
    S(["Student · browser"])
    GATE{"passcode<br/>+ rate limit<br/>per student"}
    R{"route"}
    BANK[("pre-generated bank<br/>199 problems · 154 cards<br/>committed to the repo")]
    A[("analytics.db<br/>Render disk /var/data")]

    subgraph CACHE ["Anthropic prompt cache - one entry per model+schema"]
        C1["corpus 94.1K tok<br/>notes + tutorials"]
        C2["corpus 129.6K tok<br/>notes + tutorials<br/>+ CA marking digest"]
        M1["Claude Sonnet 4.6<br/>Socratic tutor · streaming"]
        M2["Claude Opus 5<br/>grader · adaptive thinking<br/>effort medium"]
        C1 --> M1
        C2 --> M2
    end

    S -->|"X-Passcode + X-Client-Id"| GATE
    GATE -->|"401 / 429"| S
    GATE --> R
    R -->|"POST /api/generate"| BANK
    R -->|"POST /api/flashcards"| BANK
    R -->|"POST /api/chat"| C1
    R -->|"POST /api/grade"| C2

    BANK ==>|"free · instant"| S
    M1 -->|"0.034 USD · 4.1s"| S
    M2 -->|"0.093 USD · 13.8s<br/>+0.007 per photo"| S

    M1 -.-> A
    M2 -.-> A
    BANK -.-> A

    classDef free fill:#14532d,stroke:#22c55e,color:#dcfce7
    classDef paid fill:#1e3a5f,stroke:#3987e5,color:#dbeafe
    classDef store fill:#3f3f46,stroke:#a1a1aa,color:#f4f4f5
    class BANK free
    class M1,M2,C1,C2 paid
    class A store
```

**Why the bank exists.** Fifty students asking for an L2 deck used to be fifty
near-identical API calls, each re-reading the ~94K-token corpus. Pre-generating
removes ~35% of live traffic *and* two of the four cache prefixes the app must
keep warm. A cold round now costs $1.86, down from $2.39.

**Why the grader has a bigger corpus.** Tutorials show the teaching style; the
past CAs show the examining style — mark allocation, how much working earns
full credit. The grader has no other source for what "good enough" means in
this course — but it does not need the papers themselves, only what they encode.
`scripts/build_ca_digest.py` distils them into an 8K-token marking standard
(0.5-mark itemisation, the 60:40 setup-to-evaluation split, error-carried-forward,
house conventions), down from 51K. The tutor is not charged for it at all.

> The digest records that the CA papers write $dU = \delta Q - P\,dV$ while the
> consolidated notes use $\Delta U = Q + W$. The grader is told the convention is
> the student's to choose provided they state it and stay consistent, which is
> what the published CA solutions do. Only inconsistency is a conceptual error.

## Cost structure

Marginal and average cost differ by 3x, and the gap is the cache.

```mermaid
flowchart LR
    subgraph FIXED ["Near-fixed — per cold round, regardless of who is using it"]
        W1["Sonnet prefix<br/>94.1K x 2 x $3/M<br/>= $0.56"]
        W2["Opus 5 prefix<br/>129.6K x 2 x $5/M<br/>= $1.30"]
    end
    subgraph VAR ["Marginal — per action, cache warm"]
        V1["chat $0.034"]
        V2["grade $0.093"]
        V3["practice $0"]
        V4["flashcards $0"]
    end
    FIXED --> AVG["average $0.117 / action<br/>at moderate usage"]
    VAR --> AVG
    AVG --> T["~$9.33 per student<br/>over 16 weeks"]

    classDef fx fill:#7c2d12,stroke:#ea7317,color:#ffedd5
    classDef vr fill:#1e3a5f,stroke:#3987e5,color:#dbeafe
    class W1,W2 fx
    class V1,V2,V3,V4 vr
```

Because the write cost is near-fixed, **more usage makes each action cheaper**:
$0.150/action at light usage, $0.100 at heavy. An under-used deployment is the
expensive one per unit of value.

`CACHE_TTL=adaptive` narrows that gap from the other side: a 1h write costs 2x
input price and a 5m write 1.25x, so 1h only repays itself above ~3 requests per
hour. The app counts the last hour's requests and picks. The TTL is not part of
the cache key — verified — so switching between them re-reads the same entry
rather than forking it.

## Build and deploy

```mermaid
flowchart LR
    PDF["course_content/<br/>notes · tutorials<br/>19 CA papers"]
    PDF -->|"scripts/extract_ca.py"| TXT["ca_papers.txt<br/>51K tok"]
    TXT -->|"scripts/build_ca_digest.py"| DIG["ca_digest.txt<br/>8K tok · marking standard"]
    DIG --> CORP["corpus.py"]

    CORP -->|"offline, once per revision"| MK["scripts/make_bank.sh"]
    MK --> G["build_bank.py --direct"]
    G --> AU["audit_bank.py --remove"]
    AU --> DD["dedupe_bank.py --apply"]
    DD -->|"still thin?"| G
    DD -->|"clean AND full"| BJ[("practice_bank.json<br/>flashcard_decks.json")]

    BJ --> GH["git push"]
    CORP --> GH
    GH -->|"auto-deploy ~90s"| RN["Render · Docker<br/>1 instance + 1GB disk"]

    classDef gate fill:#7c2d12,stroke:#ea7317,color:#ffedd5
    class AU gate
```

**The audit is a gate, not a report.** Adding the course conventions to the
authoring prompt halved the defect rate (measured 9.5% to 5.3% on freshly
generated problems) but did not eliminate it — roughly 1 in 19 still shipped a
wrong sign convention or an irreversible process described as reversible. A
prompt is not a guarantee, so `make_bank.sh` loops until the audit comes back
clean and cannot exit with a dirty bank.

The loop's exit condition checks **clean AND full**: an empty bank is trivially
clean, and a full one can still be dirty.

> The audit proves only the absence of the three defects it can detect. It says
> nothing about whether a problem is well-posed — the first problem reviewed by
> hand had correct arithmetic throughout and a self-contradictory premise. A
> human read is still owed before students see the bank.
