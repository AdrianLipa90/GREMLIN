# GREMLIN Intention→Flavor Bridge Audit v1.7

Status: `CANDIDATE / TYPE REPAIR / MECHANISM OPEN`

## Historical debt

The historical CIEL/0 relation

\[
R(S,I)=|\langle S|I\rangle|^2
\]

is well-typed only when `S` and `I` belong to the same Hilbert space. If intention lives in \(H_I\) and neutrino flavor lives in \(H_F\cong\mathbb C^3\), the bare overlap is a type error.

v1.7 replaces the hidden identification with an explicit bridge.

## Candidate A — coherent isometry

\[
\mathcal B:H_I\to H_F,\qquad \mathcal B^\dagger\mathcal B=I_{H_I}.
\]

Then \(R_\alpha(I)=|\langle\nu_\alpha|\mathcal B|I\rangle|^2\). An isometry into a flavor qutrit requires \(\dim H_I\le3\). A global unitary identification requires exactly \(\dim H_I=3\).

BELZEBUB verdict: structurally admissible coherent special case; physical mechanism still open.

## Candidate B — projection/postselection

For a single successful filter branch,

\[
|\phi\rangle=\frac{B|I\rangle}{\sqrt{\langle I|B^\dagger B|I\rangle}}.
\]

The denominator is a success probability. Therefore this map cannot be silently treated as a deterministic physical bridge. A failure branch is required to complete a physical channel.

BELZEBUB verdict: admissible only as explicitly conditioned/postselected branch.

## Candidate C — CPTP channel

\[
\mathcal B(\rho_I)=\sum_k K_k\rho_IK_k^\dagger,\qquad \sum_kK_k^\dagger K_k=I_{H_I}.
\]

Flavor readout is

\[
R_\alpha(I)=\operatorname{Tr}[\Pi_\alpha\,\mathcal B(|I\rangle\langle I|)].
\]

The Kraus representation supplies complete positivity and the completeness equation supplies trace preservation.

BELZEBUB verdict: most general structurally admissible class, but arbitrary Kraus operators do not explain the physical mechanism. Their origin must be derived or experimentally constrained.

## Comparison verdict

No canonical physical bridge is selected.

- coherent pure special case: isometry;
- conditional measurement branch: projection/postselection;
- general deterministic open-system bridge: CPTP.

The next debt is to derive or constrain the bridge from the declared neutrino mass/mixing/topological dynamics.

## Information boundary

The vector \((R_e,R_\mu,R_\tau)\) is retained. v1.7 does not collapse it to a single `resonance truth` scalar. Downstream Shannon entropy or mutual information is computed only after the preparation/readout channel has been declared.
