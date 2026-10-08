# S03-E003 Code Ready review — round 1

**Reviewer:** independent ChatGPT review, conversation
`6ac787b9-5b04-8333-a526-15f70563050a`  
**Bound commit:** `930b6ab38b72b3c3f5d9ae1f6842d884ed3fd862`  
**Bound protocol:** S03-E003 v1  
**Verdict:** `REVISE_CODE`

The review found one fail-closed counter bug and eight additional blockers that
could later permit false qualification:

1. required-header counters were not initialized for fields with zero misses;
2. floating cycle alone was treated as acquisition identity;
3. local mapping rows were not joined to local nodemap identities;
4. horizon counts did not require a valid direct DCPD target;
5. one eligible origin could pass and evaluation resolution was not enforced;
6. aliases, numeric formats, duplicate fields, malformed CSV and cycle validity
   were not parsed strictly;
7. unsafe/colliding/encrypted archive members and exact dictionary identities
   were not stopped before member reads;
8. the output firewall was asserted rather than tested and raw CSV column names
   could be emitted;
9. the output path could alias and overwrite an immutable input.

The reviewer required synthetic decision-level regression tests, not only helper
tests. No real archive audit was executed under the rejected commit.

Local action: accepted all blockers. Protocol v2 and the corrected runner add
manifest-first stopping, timestep/connection identity, strict parsing,
file-level synchronization, value-redacted target validity, a frozen minimum-
information rule, output collision guards, atomic writing, and end-to-end
fixtures. A second independent review is required before S03-E003-R001.
