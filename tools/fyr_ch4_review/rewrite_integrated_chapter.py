"""Integrate the two reviewed local evidence sets into a new Chapter 4 draft."""
from pathlib import Path
import csv,json,shutil
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OLD=R/'local_archive/report_ch4_revision_20261015'
FAT=R/'local_archive/report_ch4_fatigue_fields_20261015'
O=R/'local_archive/report_ch4_rewrite_integrated_20261015'
for d in ['draft','figures','review']:(O/d).mkdir(parents=True,exist_ok=True)
for folder in [OLD,FAT]:
 for p in (folder/'figures').glob('*.png'):shutil.copy2(p,O/'figures'/p.name)
def read(p):return list(csv.DictReader(p.open()))
S=read(FAT/'analysis/native_GP_statistics.csv');D=read(FAT/'analysis/same_state_GP_differences.csv');U=read(FAT/'analysis/history_update_s3_to_s4.csv')
I=json.loads((OLD/'analysis/summary.json').read_text())
A=R/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis'
Q=json.loads((A/'c83_q4_mechanism/summary.json').read_text());T=json.loads((A/'c83_q4_mechanism/t3_summary.json').read_text())
E=json.loads((A/'multicycle_fixed_damage_equilibrium/decision_summary.json').read_text())
def stat(sol,a,c):return next(r for r in S if r['solver']==sol and r['topology']==a and int(r['cycle'])==c)
def gap(a,c,f,dom='full'):return next(r for r in D if r['topology']==a and int(r['cycle'])==c and r['field']==f and r['domain']==dom)
def tab(n,cap,headers,rows):
 return f'*Table 4.{n}. {cap}*\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in rows)+'\n'
def fig(n,name,caption):return f'![Figure 4.{n}.]({O}/figures/{name}.png)\n\n*Figure 4.{n}. {caption}*\n'
P=[r'''# Chapter 4. Results and discussion: FEM and PIDL under cyclic loading

This chapter asks how closely the physics-informed deep learning (PIDL) implementation reproduces the response of the phase-field fatigue model solved by the finite element method (FEM). The comparison examines when high damage reaches the observation region, how the damage and fatigue fields evolve, and what the remaining differences reveal about the two implementations. The work addresses the first stage of the PhD: establishing and testing a numerical implementation before extending it to a pavement cracking problem.

The main study contains four calculations: FEM and PIDL on a four-node quadrilateral mesh (Q4) and on a paired three-node triangular mesh (T3). All four use the same physical model and realised five-substep loading sequence. The chapter first compares their recovered initial states and event times. It then follows the local fields at early, middle and late cycles, before examining energy fields, fatigue updates and earlier attempts to reduce the differences. The results show why event timing and domain averages need to be read alongside spatial fields.

## 4.1 Basis for the comparison

### 4.1.1 Model, discretisation and solution methods

The calculations use the single-edge-notched tensile specimen introduced in Chapter 3. The bulk material is linear elastic. Fracture is represented by the phase-field damage variable $d$, and cyclic degradation is represented by an accumulated fatigue history $\bar\alpha$ and a fatigue factor $f$. The four calculations use plane strain, the AT1 phase-field model and the Amor energy split. Their nondimensional parameters are $E=1$, $\nu=0.3$, $G_c=0.01$, $\ell=0.01$ and $\alpha_T=0.5$, with zero residual stiffness.

The meshes share an ordered set of 86,756 nodes. The Q4 mesh has 86,408 elements. Splitting each quadrilateral along a fixed diagonal gives 172,816 T3 elements. Q4 uses four Gauss points (GP) per element, and T3 uses a three-point rule. The paired meshes retain the node locations while changing connectivity, interpolation and integration.

Both PIDL calculations start from the same network file before zero-load recovery. The network has eight hidden layers, 400 neurons per layer and trainable ReLU activation functions. Both calculations use seed 1 and the same RPROP settings, with a maximum of 10,000 optimisation iterations per loading step. FEM solves displacement and damage in alternating steps. PIDL updates the network parameters for both fields through a joint energy objective. The comparison therefore covers the complete numerical implementations, including their solution procedures.

The fields used below have different roles. Damage reduces tensile stiffness through $g(d)$, while the active fatigue driver combines the raw tensile elastic-energy density with that reduction:

$$
g(d)=(1-d)^2,\qquad
\psi_{\mathrm{active}}=g(d)\psi_{\mathrm{raw}}.
$$

The active driver contributes to the accumulation of $\bar\alpha$. The accumulated history then reduces fracture resistance through the fatigue law

$$
f(\bar\alpha)=
\begin{cases}
1, & \bar\alpha\leq\alpha_T,\\
\left(\dfrac{2\alpha_T}{\bar\alpha+\alpha_T}\right)^2,
& \bar\alpha>\alpha_T,
\end{cases}
\qquad \alpha_T=0.5.
$$

A smaller $f$ means a greater fatigue-induced reduction in fracture resistance. The stiffness degradation $g(d)$ and the fatigue factor $f(\bar\alpha)$ act on different parts of the model. The accumulated history $\bar\alpha$ is carried between loading steps and is separate from damage $d$.

### 4.1.2 Loading and saved states

Each calculation first recovers the initial crack profile at zero load. This is global step $j=0$ and lies outside the physical cycles. Each subsequent cycle uses the realised displacement sequence

$$
[0.02999988,\;0.05999988,\;0.08999988,\;0.11999988,\;0],
$$

with nominal maximum displacement $U_{\max}=0.12$. The same sequence is used by FEM and PIDL. For physical cycle $c$ and substep $s=1,\ldots,5$,

$$
j=5(c-1)+s.
$$

Substep 4 is the peak, at $j=5c-1$, and substep 5 is the unloaded state. All four calculations continue through cycle 120. The early, middle and late field comparisons use the peaks of c20, c60 and c83, corresponding to global steps 99, 299 and 414.

The fatigue-history and fatigue-factor plots use the saved state after the loading step has been accepted and its history updated. Both implementations save this state, although they use fatigue differently during the current solve. PIDL keeps the factor derived from the previous accepted history fixed during optimisation. FEM keeps the previous accepted history unchanged but calculates trial fatigue values within the current phase-field solve. Section 4.5 discusses the consequence of that distinction.

The five-substep Hard-5 loading remains the baseline. The main results in this chapter use the October paired Q4/T3 study. The original July Hard-5 reference and the earlier eight-substep FEM diagnostic are separate calculations. The earlier diagnostic motivated the matching of loading sequences in the paired study.

### 4.1.3 Domain quantities and spatial comparisons

A domain integral describes the total amount of a field. A domain mean divides that integral by the specimen area. Neither records where the field is concentrated. Spatial comparisons therefore accompany the domain quantities. For a field $q$, the weighted relative difference is

$$
e_q=\left[
\frac{\sum_k w_k(q_k^{\mathrm{PIDL}}-q_k^{\mathrm{FEM}})^2}
{\sum_k w_k(q_k^{\mathrm{FEM}})^2}
\right]^{1/2},
$$

and the weighted mean absolute difference (MAE) is

$$
\operatorname{MAE}_q=
\frac{\sum_k w_k\left|q_k^{\mathrm{PIDL}}-q_k^{\mathrm{FEM}}\right|}
{\sum_k w_k}.
$$

FEM is the reference in these numerical comparisons. The initial damage statistics use common nodal weights from the row sums of the Q4 mass matrix. Energy and fatigue comparisons use the native Gauss points and common physical integration weights within each topology. Q4 and T3 have different Gauss-point locations, so their histories are not subtracted point by point across meshes.

The fatigue analysis also reports a fixed central strip, $|y_{\mathrm{GP}}|\leq0.03$, to show differences close to the crack line. The strip is a spatial reporting region; its metrics are normalised by the weights inside that region. Field images show weighted cell means, while the reported norms and extrema use the native Gauss-point values. The fatigue factor is averaged independently of the history, because averaging $f(\bar\alpha)$ differs from evaluating $f$ at the average history.

## 4.2 Recovered initial states

The four cyclic trajectories begin from recovered zero-load damage fields. FEM prescribes unit damage on the starter-crack nodes and solves for the surrounding diffuse profile. PIDL first sets the current damage output close to one while preserving the stored initial history, then performs zero-load recovery. The common initial network used by the two PIDL calculations does not make the resulting recovered fields identical.

Figure 4.1 shows the four recovered damage fields. All contain the horizontal starter crack, but their crack-tip profiles differ. Table 4.1 reports statistics over the full specimen, using the common nodal weights to account for the mesh refinement near the crack.
''']
P.append(fig(1,'initial_damage_four_arms',r'Recovered damage before the first physical cycle. The four panels use the same coordinates and a damage display range of zero to one. The view is cropped to $-0.12\leq y\leq0.12$; the statistics cover the full specimen and retain the actual extrema.'))
P.append(tab(1,'Recovered initial damage on the common nodes.',['Calculation','Weighted mean','Weighted 99th percentile','Minimum','Maximum'],[[r['arm'],f"{r['weighted_nodal_mean']:.8f}",f"{r['weighted_nodal_p99']:.6f}",f"{r['minimum']:.8f}",f"{r['maximum']:.8f}"] for r in I['initial_statistics']]))
P.append(r'''The PIDL mean damage is slightly higher on both meshes. Figure 4.2 shows that the largest FEM-PIDL differences occur near the starter-crack tip. The relative differences are 8.04% for Q4 and 7.47% for T3, with maximum local differences of 0.355 and 0.324. The initial mean alone would therefore understate the difference in the recovered profiles.''')
P.append(fig(2,'initial_damage_differences',r'PIDL minus FEM damage after zero-load recovery. The two panels share a zero-centred colour scale and the same cropped view as Figure 4.1. The statistics retain the unmodified nodal values.'))
P.append(tab(2,'Differences between recovered initial damage fields. The reference appears second in each pair.',['Comparison','Weighted MAE','Relative L2','Maximum absolute difference'],[[r['candidate']+' versus '+r['reference'],f"{r['weighted_MAE']:.8f}",f"{r['weighted_relative_L2']:.5f}",f"{r['max_abs_difference']:.5f}"] for r in I['initial_differences']]))
P.append(r'''The PIDL penalty permits small violations of the damage bounds. At recovery, the minimum damage is about $-3.3\times10^{-4}$ in both PIDL calculations; the T3 maximum is slightly above one. These values are retained in the numerical statistics.

The fatigue variables have a common starting condition. FEM initialisation metadata records zero accumulated fatigue, zero previous active driver and a fatigue factor of one after recovery. The PIDL recovery checkpoints contain zero fatigue history and zero previous active driver, which give $f=1$. Thus the four calculations start with equal fatigue variables but measurably different damage fields. The following comparisons track the trajectories from these actual recovered states.

## 4.3 Event timing under a common rule

The event records when high damage reaches a narrow observation region near the right boundary. At each cycle peak, the qualifying-node count is

$$
n_c=\#\{i:x_i>0.48\ \text{and}\ d_i(c,s=4)>0.95\}.
$$

First detection is the earliest cycle with $n_c\geq3$. The same coordinates, strict inequalities and minimum count are used in every calculation. Because the specimen already contains a starter crack, this event describes damage reaching the observation region rather than crack initiation. The rule does not require the qualifying nodes to form a connected crack path.

All 120 saved peaks in each calculation were checked. Table 4.3 gives the results. Confirmation is the prescribed reporting label three physical cycles after first detection. It is distinct from first detection and is not a requirement for three additional detections. In these trajectories, the threshold remains satisfied at every subsequent saved peak.
''')
P.append(tab(3,'Event times reconstructed from all 480 saved peaks in the paired study.',['Calculation','First detection','Global peak step','Confirmation cycle','Qualifying nodes at first detection'],[[r['arm'],r['first_detection_cycle'],r['first_detection_global_step'],r['confirmation_cycle'],r['qualifying_nodes_at_first']] for r in I['events']]))
P.append(fig(3,'unified_event_timeline',r'Qualifying-node counts over all 120 peaks and the resulting event times. The two FEM count curves coincide. Circles mark first detection; open squares mark the three-cycle confirmation label. All results use the paired five-substep trajectories.'))
P.append(r'''PIDL-Q4 reaches the threshold one cycle later than FEM-Q4. PIDL-T3 reaches it five cycles later than FEM-T3. Changing topology leaves the FEM event at c84 but delays the PIDL event from c85 to c89. Event timing is therefore more sensitive to the topology change in PIDL for this study.

The earliest event is c84, so the c20, c60 and c83 comparisons all precede first detection in every calculation. The one-cycle Q4 event difference provides a useful overall measure of agreement. The local-field comparisons below examine how much agreement that event measure captures.

## 4.4 Evolution of damage and fatigue

### 4.4.1 Damage at the common late-cycle peak

Figure 4.4 compares the damage fields at c83 peak. All four calculations are still below the event threshold. Parts of the PIDL damage band are broader in the crack wake, while negative PIDL-FEM differences occur near the advancing front. The mismatch therefore changes with position rather than following a uniform damage offset.
''')
P.append(fig(4,'hard5_c83_damage_comparison',r'Damage at the common c83 peak for Q4 and T3, followed by PIDL minus FEM. The absolute panels share a zero-to-one display range and the difference panels share a zero-centred scale. The fields are saved nodal values. A fixed split of the common Q4 cells is used only for display.'))
P.append(r'''The damage integral also responds differently to the topology change. At c83, replacing Q4 with T3 reduces the FEM damage integral by 1.75% but increases the PIDL integral by 18.21%, each relative to its own Q4 result. These opposite changes are consistent with the greater event-time sensitivity seen in PIDL. They describe the response of the complete implementations, including their interpolation, integration and solution procedures.

### 4.4.2 Early, middle and late fatigue states

The fatigue fields show how local differences develop before the event. Figure 4.5 compares domain means and field differences at c20, c60 and c83. All four calculations accumulate fatigue history and reduce the fatigue factor as cycling continues. The domain means remain close, but the spatial differences follow different patterns on Q4 and T3.
''')
P.append(fig(5,'early_middle_late_metrics',r'Domain means and native-Gauss-point differences at c20, c60 and c83 peaks, after history refresh. In the lower panels, solid lines show the full domain and dashed lines show the central strip $|y_{\mathrm{GP}}|\leq0.03$. History uses the relative $L^2$ difference; the factor uses MAE. Lines connect only the three sampled cycles.'))
rows=[]
for a in ['q4','t3']:
 for c in [20,60,83]:
  rows.append([a.upper(),c,f"{100*float(gap(a,c,'H')['relative_L2']):.2f}%",f"{100*float(gap(a,c,'H','corridor_abs_y_le_0.03')['relative_L2']):.2f}%",f"{float(gap(a,c,'F')['MAE']):.5f}",f"{float(gap(a,c,'F','corridor_abs_y_le_0.03')['MAE']):.5f}"])
P.append(tab(4,r'History and fatigue-factor differences at the three selected peaks. The central strip is $|y_{\mathrm{GP}}|\leq0.03$.',['Topology','Cycle','History L2, full','History L2, strip','Factor MAE, full','Factor MAE, strip'],rows))
P.append(r'''On Q4, the full-domain history difference rises from 21.59% at c20 to 29.87% at c83. In the central strip, it rises from 45.82% to 64.56%. On T3, the full-domain difference falls from 20.59% at c20 to 16.29% at c60, then rises slightly to 16.90% at c83. The T3 strip follows the same decrease and small late increase. The history mismatch therefore does not grow in the same way on the two meshes.

The fatigue-factor MAE increases across the three checkpoints on both meshes. At c83, the full-domain values are 0.00735 for Q4 and 0.00812 for T3. Within the strip they are 0.02712 and 0.03617. The small domain-average differences conceal larger local differences near the crack line.

### 4.4.3 Fatigue history at c83

Figure 4.6 shows the saved accumulated history at the common c83 peak. FEM and PIDL have similar broad distributions, while the difference panels locate narrow regions of disagreement. The shared linear difference scale retains the largest cell-mean differences; weaker differences appear pale. The Gauss-point statistics in Table 4.5 supplement this cell-mean view.
''')
P.append(fig(6,'c83_history_post_commit',r'Accumulated fatigue history $\bar\alpha$ at c83 peak after the accepted-step history update. Rows show Q4 and T3; columns show FEM, PIDL and PIDL minus FEM. Absolute fields use a shared logarithmic scale with display floor $10^{-4}$. Differences use a shared linear, zero-centred scale. Colours represent weighted native-cell means.'))
rows=[]
for a in ['q4','t3']:
 f,p=stat('FEM',a,83),stat('PIDL',a,83)
 rows.append([a.upper(),f"{float(f['history_mean']):.5f}",f"{float(p['history_mean']):.5f}",f"{float(f['history_max_GP']):.3f}",f"{float(p['history_max_GP']):.3f}"])
P.append(tab(5,'Domain-mean and maximum Gauss-point fatigue history at c83.',['Topology','FEM mean','PIDL mean','FEM maximum','PIDL maximum'],rows))
P.append(r'''The PIDL history mean is lower than FEM on both meshes, but the local maximum changes in the opposite direction between topologies. On Q4, the PIDL maximum is 17.03 compared with 21.44 in FEM. On T3, it is 26.77 compared with 22.28. A general statement that PIDL underestimates the fatigue history would miss this spatial and topology dependence.

### 4.4.4 Fatigue degradation at c83

The fatigue factor translates the accumulated history into a reduction in fracture resistance. Figure 4.7 shows the corresponding c83 factor fields. Positive PIDL-FEM differences mean that PIDL retains a larger fatigue factor at that location; negative differences mean greater fatigue degradation in PIDL.
''')
P.append(fig(7,'c83_factor_post_commit',r'Fatigue factor $f(\bar\alpha)$ at c83 peak after history refresh. Rows show Q4 and T3; columns show FEM, PIDL and PIDL minus FEM. Absolute values use the common range [0,1], and signed differences use [-1,1]. The factor is averaged independently within each cell.'))
rows=[]
for a in ['q4','t3']:
 f,p=stat('FEM',a,83),stat('PIDL',a,83)
 rows.append([a.upper(),f"{float(f['factor_mean']):.5f}",f"{float(p['factor_mean']):.5f}",f"{float(gap(a,83,'F')['MAE']):.5f}",f"{float(gap(a,83,'F','corridor_abs_y_le_0.03')['MAE']):.5f}"])
P.append(tab(6,'Fatigue-factor means and spatial differences at c83.',['Topology','FEM mean','PIDL mean','MAE, full domain','MAE, central strip'],rows))
P.append(r'''The factor means are close on each mesh, but even their ordering depends on topology. The PIDL mean is slightly higher than FEM on Q4 and slightly lower on T3. The local difference maps contain both signs. The fatigue factor therefore gives a more specific account of where fracture resistance differs than a single history maximum or mean can provide.

### 4.4.5 Spatial evolution across the three checkpoints

Figures 4.8 and 4.9 show the history fields at all three checkpoints on Q4 and T3. Figures 4.10 and 4.11 show the fatigue factor. The row-by-row comparison uses the same peak phase and post-update timing. Shared colour scales allow changes across cycles and methods to be read directly.

Both history sequences retain a strong concentration around the crack region as the accumulated history grows. The similar broad patterns coexist with the native-point differences in Table 4.4. Cell averaging and a shared extreme-based difference scale make the narrowest discrepancies less prominent in the images, so the spatial norms remain part of the comparison.
''')
P.append(fig(8,'q4_history_evolution',r'Q4 fatigue history at c20, c60 and c83, from top to bottom. Columns show FEM, PIDL and PIDL minus FEM. Every panel uses the accepted peak state after history update. The history and signed-difference scales match Figure 4.6.'))
P.append(fig(9,'t3_history_evolution',r'T3 fatigue history at c20, c60 and c83. The fields are displayed on the native T3 cells with the same scales, phase and output timing as Figure 4.8.'))
P.append(fig(10,'q4_factor_evolution',r'Q4 fatigue factor at c20, c60 and c83, from top to bottom. Columns show FEM, PIDL and PIDL minus FEM. All states are saved after history update. The factor range is [0,1] and the difference range is [-1,1] throughout.'))
P.append(fig(11,'t3_factor_evolution',r'T3 fatigue factor at c20, c60 and c83, using the same ranges and saved-state timing as Figure 4.10.'))
P.append(r'''The region of reduced fatigue factor expands with cycling in both implementations. Its broad shape is similar, but local differences develop around its boundary and along the crack line. Taken together, the damage, history and factor results show that a close event time can accompany different local paths to that event.

## 4.5 Interpreting the field differences

### 4.5.1 The local combination of energy and damage

The fatigue history accumulates information from earlier accepted states. To examine the instantaneous fields contributing to that history, the c83 analysis separates raw tensile energy, damage degradation and their product, $\psi_{\mathrm{active}}=g(d)\psi_{\mathrm{raw}}$. Table 4.7 compares each quantity with the same quantity in the other implementation, using native Gauss-point values and physical weights.

The energy diagnostic uses the saved c83 displacement and accepted damage fields. The PIDL gradient export precedes fatigue-history refresh; the accumulated-history plots in Section 4.4 follow refresh. These outputs describe different parts of the same accepted step. The active-energy values are not the fatigue factor held fixed in the PIDL objective.
''')
rows=[]
for a,z in [('Q4',Q),('T3',T)]:
 for key,name in [('psi_raw_pidl_vs_fem','Raw tensile energy'),('g_pidl_vs_fem','Damage degradation g'),('psi_active_pidl_vs_fem','Active energy')]:
  v=z['factor_comparisons'][key]
  rows.append([a,name,f"{v['delta_pct']:+.2f}%",f"{v['relative_l2']:.4f}",f"{v['correlation']:.3f}"])
P.append(tab(7,'Same-variable energy and damage-degradation comparisons at c83. Integral changes use FEM as the reference within each topology. Norms and correlations use native integration weights.',['Topology','Quantity','Integral difference','Relative L2','Correlation'],rows))
P.append(r'''For Q4, the active-energy integral differs by 5.81%, while the relative field difference is 0.476. The raw-energy integral is also close, with a difference of -2.36%, but its field difference is 0.989. These pairs of values show how spatial differences can be hidden by integration. For T3, the active-energy integral difference is 33.83% and the relative field difference is 1.026. The energy comparison is therefore also sensitive to topology.

Figure 4.12 illustrates the Q4 active field. The raw-energy concentration is strongly reduced where it coincides with high damage. The relative locations of the energy concentration and damaged region matter because the two fields are multiplied at each point before integration.
''')
P.append(fig(12,'hard5_c83_active_q4',r'Q4 active-energy density at c83 peak for FEM and PIDL, followed by PIDL minus FEM. Products are evaluated at Gauss points before cell reduction. The absolute panels share a logarithmic scale with display floor $10^{-12}$; the difference panel uses a linear zero-centred scale.'))
P.append(r'''An existing field-exchange diagnostic makes the spatial relationship clearer. It combines the raw-energy field from one calculation with the damage-degradation field from the other. Across the Q4 and T3 checks, the exchanged active-energy integrals are about 17-60 times the corresponding FEM value. Each original calculation suppresses much of its own raw-energy concentration through its own damage field. Exchanging the fields weakens that local suppression. The exchanged products describe this spatial relationship; they are not additional equilibrium solutions.

An earlier reduced-field comparison had mixed raw FEM energy with degraded PIDL energy. The present analysis uses the corrected, same-variable native-point quantities. The distinction is essential because the damaged region can strongly reduce the raw tensile-energy contribution.

### 4.5.2 Fatigue during a loading step

The saved history fields in Section 4.4 have the same output timing. Their values reflect the loading paths taken by two different algorithms. During PIDL optimisation, the fatigue factor derived from the previous accepted history remains fixed. After fitting, the accepted fields are evaluated, the accumulated history is updated and the factor is refreshed for the next loading step.

FEM also holds the previous accepted history unchanged during iteration. Its phase-field assembly calculates a trial active driver from the current trial damage, then uses a trial fatigue increment and factor in the current phase-field solve. The accepted history is committed when the step is accepted. Thus both methods preserve the old stored history, but the factor acting during the current solve can differ.

The difference between consecutive accepted states shows why output timing matters. Table 4.8 compares s3 with the subsequent peak s4 at c83. The domain-mean changes in the factor are small, while the largest local changes range from about 0.20 to 0.38. These are changes across a loading substep, including its solution and history update, rather than an isolated measurement of a commit operation.
''')
rows=[]
for u in U:
 if int(u['cycle'])==83:
  rows.append([u['solver']+'-'+u['topology'].upper(),f"{float(u['history_increment_mean']):.7f}",f"{float(u['factor_change_MAE']):.7f}",f"{float(u['factor_change_max']):.4f}"])
P.append(tab(8,'Changes between the previous accepted s3 state and the accepted peak s4 state at c83.',['Calculation','Mean history increment','Factor-change MAE','Maximum absolute factor change'],rows))
P.append(r'''The current-step fatigue treatment is therefore a specific difference to test. The stored fields alone do not measure how much of the FEM-PIDL trajectory gap it causes. The initial damage differences and the coupled displacement-damage response remain part of the comparison.

## 4.6 Attempts to understand and reduce the gap

### 4.6.1 Representation and discretisation

Development trials tested whether richer local representations could recover the missing crack-region pattern. The changes included crack-tip features, Fourier features, local correction heads and local subnetworks. Event times and local fields changed, but the trials did not produce a consistent match of the fatigue fields. Because settings evolved across those studies, they provide a record of development rather than a controlled ranking of network architectures.

The paired Q4/T3 study addressed a more specific question by matching the node locations and realised loading sequence. The results show that changing topology affects FEM and PIDL differently: the c83 damage integrals move in opposite directions, and the PIDL event shifts by four cycles while the FEM event remains unchanged. Matching discretisation made the comparison easier to interpret, while exposing sensitivity that a single-mesh result would miss.

### 4.6.2 Re-solving displacement with damage fixed

An existing diagnostic tested whether improving displacement equilibrium alone would substantially reduce the active-field gap. At c1, c60, c83 and c85, each saved damage field was bounded to [0,1] and held fixed while displacement was re-solved using the topology-specific equilibrium operator. This keeps the damage pattern prescribed while changing the displacement solution.

Some bounded zero-residual-stiffness problems were singular or did not meet the required residual tolerance. A common residual-stiffness sensitivity value of $\eta=10^{-6}$ was therefore used to compare the selected re-solves. It changes the original $\eta=0$ setting and is reported as a separate fixed-state diagnostic.

Across the selected Q4 and T3 states, about 88-103% of the original active-field relative difference remained after the displacement re-solve. At c83, the Q4 difference changed from 0.476 to 0.463, and the T3 difference from 1.026 to 1.018. Improving displacement equilibrium alone therefore removed little of the selected field discrepancy. The prescribed damage pattern and the location of the crack transition remain important candidates for further comparison.

### 4.6.3 Damage constraints and final-state checks

The damage bounds also affect the mechanical interpretation. With $g(d)=(1-d)^2$ and zero residual stiffness, a value above one introduces nonzero stiffness where a bounded fully damaged value would give zero. Existing T3 fixed-damage checks found that upper-bound violations could supply this stiffness: imposing the upper bound could make the zero-stiffness problem singular. The result gives a mechanical reason to examine how the PIDL damage constraint is enforced.

Final-state checks matter for FEM as well. A stored stopping residual can precede the last damage update or clipping operation, so it may not describe the final saved displacement-damage pair. Existing endpoint checks found differences between cached stopping values and residuals recomputed from the final fields, including imbalance around the crack wake and advancing front. These checks identify a need for consistent evaluation of both implementations' final states.

Table 4.9 brings the diagnostic studies together. The useful outcome is a more specific set of numerical questions, rather than a single explanation assigned to every field difference.
''')
P.append(tab(9,'Questions examined during development and the conclusions supported by the existing results.',['Question','Change or check','Main result','Implication'],[
['Can the network represent the local pattern?','Local features and correction networks','Fields and event times changed; no consistent fatigue-field match','Representation changes alone did not resolve the trials'],
['Does discretisation matter?','Paired Q4/T3 calculations','Opposite damage-integral changes; larger PIDL event shift','Evaluate discretisation within each implementation'],
['Can similar totals conceal local differences?','Raw energy, g and their pointwise products','Close Q4 totals coexist with local differences','Compare spatial combinations as well as totals'],
['Is displacement imbalance sufficient to explain the gap?','Fixed-damage displacement re-solves','About 88-103% of the active-field discrepancy remained','Examine damage and coupled updates alongside equilibrium'],
['Do constraints and stopping values describe the final state?','Bounded-damage and endpoint checks','Bounds affect stiffness; cached and final residuals can differ','Check constraints and residuals on accepted fields']
]))
P.append(r'''## 4.7 Findings and the next stage of the PhD

The first-year work established a fatigue-augmented PIDL implementation and a comparison of complete FEM and PIDL trajectories on paired Q4 and T3 meshes. The initial-state analysis measured the recovered damage differences. Applying one event rule to all 480 saved peaks gave first detection at c84 for both FEM calculations, c85 for PIDL-Q4 and c89 for PIDL-T3. The Q4 event time is therefore closer in this study.

Local fields provide a different measure of agreement. At the common c83 peak, Q4 has a fatigue-history relative difference of 29.87% and an active-energy relative difference of 0.476, despite a 5.81% difference in the active-energy integral. T3 has a smaller fatigue-history relative difference of 16.90%, but a larger active-energy relative difference of 1.026. Agreement depends on the quantity being examined, its spatial distribution and the topology. An event cycle or one domain average cannot describe all of these aspects.

The diagnostic work narrowed the next research questions. Initial damage profiles differ before cycling. Raw energy and damage combine differently in space. Current-step fatigue treatment differs between the solvers, and damage constraints can affect the stiffness of highly damaged regions. Fixed-damage displacement re-solves leave most of the selected active-field gap. Together, these findings motivate controlled comparisons of the initial state, fatigue update and damage constraints, with residuals evaluated on the final accepted fields.

These comparisons are the next part of the first stage of the PhD. Their purpose is to establish a more reliable numerical basis for fatigue crack evolution. Chapter 5 then sets out how that basis will be extended to a defined pavement cracking problem and, later, connected to observations for prediction of future crack evolution. The present results provide the implementation and the numerical questions needed to plan those stages; prediction of observed road cracks remains the longer-term objective.
''')
text='\n\n'.join(P)+'\n'
(O/'draft/Chapter4_Integrated_Rewrite.md').write_text(text)
print('Chapter words (including captions/tables):',len(text.split()))
print('Figures copied:',len(list((O/'figures').glob('*.png'))))
