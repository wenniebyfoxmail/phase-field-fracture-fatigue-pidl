# S09-E017 authorised dispatch: pre-admission network stop

## Outcome

`PRE_ADMISSION_STAGING_STOPPED__NETWORK_TRANSFER_LOST_CONNECTION__NO_EXECUTION`

The user authorised the exact reviewed package through HQ thread
`01a14bb9-6cd1-7ee2-9647-5190d786f7ba`. The local authority was valid for
commit `2002538d9a30c8d4006ccaff5959cd214958fc82`, candidate SHA256
`4c1e928274f6fbee134ff540345844260cf16675727d0e996abb0054062ddcf1`
and code-archive SHA256
`4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22`.

## Live facts

The SSH connection did succeed. It verified `GPUServer8`, user `drtao`, Linux,
GPU5 UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`, 4 MiB used, 0% GPU
utilisation and no GPU5 compute process. `/mnt/data2` had 652,974,047,232 free
bytes. The RunID task and archive roots were absent. Packet-manifest and B25
checkpoint hashes matched the frozen card.

During staging, the full shallow-checkout stream was stopped before completion
because the SSH send window progressed too slowly; its task-owned partial tree
was preserved under the control root. A remote S09-E010 checkout at exact
ancestor `010281be8045301f7e56b938de82969982c89bc9` was then copied locally on the
producer, and a 3.3 MiB thin bundle was selected to avoid retransmitting the
repository. That bundle transfer ended with the exact terminal error
`lost connection`.

## Boundary

The command chain stopped at that transfer. It did not write the remote
execution authority, fetch the target commit, create the bound code archive,
invoke the resolver or runner, or create `admission_attempt.json`. Therefore
there was no live admission, model forward, autograd collection, optimiser,
update, output, archive or scientific result. No reconnect, continuation,
retry, remote cleanup or alternate route was attempted after the terminal
network error. The local authority is closed for retry.

The remote post-failure staging state is deliberately recorded as unverified.
A future action would need a new explicit authority and must first inspect the
existing RunID paths and processes read-only; it must not overwrite, clean or
resume them by assumption.
