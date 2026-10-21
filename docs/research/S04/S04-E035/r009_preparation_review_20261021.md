# R009 outcome and unexecuted preparation review

R009 accepted seven states through U=.21; U=.24 stopped in the added PF residual Armijo rule. Full U=.4 reference is absent; PIDL did not start. See [result](runs/S04-E035-R009.md).

Independent reviewer `/root/shear_review` checked the saved-array verifier and conditional PIDL preparation. The PIDL launcher now masks by the fixed GPU UUID and verifies Torch logical-device UUID in the training process. The final native-PF candidate review confirmed residual timing metadata is cleared before driver/history changes, while a failed returned-point assertion retains its matching value. Review covers preparation only; it is not numerical validation of that candidate.

Mechanical checks: four new Python files compile; git diff whitespace check passed. R009 raw retrieval has 50/50 matching size/SHA256 files. Figure source sidecars passed and rendered figures were visually inspected.

No additional FEM solve, FEM RunID allocation, PIDL training or scientific retry was performed. R010 exists as local conditional PIDL preparation only. One repair attempt is consumed; original deadline and previous costs remain.

| Prepared file | SHA256 |
| --- | --- |
| `execute_manav_static_pidl.py` | `afc54387deb00ad0f1b5cdde7a98a2a06d1e16ea721b1439473b91e6a33596a3` |
| `launch_manav_static_pidl.py` | `749763da136ea5eeb0d0f3b59c1e46053cd5bf040ce2184454c4b2ce1681f280` |
| `plot_manav_static_stop.py` | `7ea49a57848979815239a03092aa307b741fe6e9fc5f5365375e674f0b2e3a1c` |
| `run_manav_static_fem_native_pf.m` | `e585ae62d7ca7cee321fe6d096f14909b86e01199e579b946168a1134b72f58a` |
| `supervise_manav_pidl.ps1` | `b8a44209c03f807ef6c88c266bbb1f30b071e9dd49f16cb3b8b86fef3484c3e8` |
| `verify_manav_static_reference.py` | `1f03560d70f8b3e531d151b67e83dba8c6af809de24726fe42a3c45aca122626` |
