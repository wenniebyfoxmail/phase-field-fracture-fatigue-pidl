# Pro design advice received — 2026-10-05

Source: https://chatgpt.com/c/6ac2e1ce-9940-83ed-a562-b17182126205, completed response visible on continuation, titled DESIGN PASS. This is a focused transcription of the relevant advice, not the full response.

- First evaluate the exact FEM current nodal field in Ephys=Eel+Efrac+Ehist with frozen projected PIDL413 histories. No re-solve.
- Use independent physical nodal leaf derivatives, avoiding the network raw/clamp derivative chain.
- M=diag(m_i/A), E_s=A*t*E*(U_s/H)^2, g_u=d(Ephys/E_s)/d(u/U_s), g_d=d(Ephys/E_s)/dd.
- rho_u=||M_u^(-1/2)*g_u,free||2; rho_d=||M^(1/2)*(d-clip(d-M^(-1)*g_d,0,1))||2.
- Exclude only truly prescribed DOFs. Box is[0,1], not[d_prev,1], because irreversibility remains the original penalty. Report healing independently.
- Practical frozen stationarity screen: both residuals<=1e-3. A failed screen does not uniquely identify history, penalty or optimization as cause.
- Confirm directional derivatives on a smooth float64 patch at normalized error<=1e-5; retain input/state identity checks.
- Full design also covers supervised fit/polish, but those stages are outside this user's current go instruction for the audit.

Local adoption: cross_residual_protocol.md. The review's arithmetic U413=.08999991 is rejected in favor of actual recorded schedule .08999988; U414=.11999988 is unchanged.
