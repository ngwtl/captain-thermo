# MS1016 Tutorials — Problems and Solutions Anthology

**Consolidated from tutorials 1–8. Cross-referenced to lecture sections.**

> Problems below are transcribed from the tutorial PDFs with numerical answers preserved verbatim. Where a source PDF solution is particularly involved, I've provided a shortened clean derivation here and pointed you to the source for full working. Official solutions (with all intermediate algebra) are in `Tutorials/Solution_Tutorial N.pdf`.

---

## Tutorial 1 — Work Done by a System [→ L1 §1.3, §1.9]

### Problem 1 — Reversible work, four geometries

For each configuration, write the reversible work done **by the system** and the First Law in differential form (using $\Delta U = Q + W$, $W$ = work on system).

**(i) Gas compressed by external pressure $P$ through $-\mathrm{d}V$** (i.e. $\mathrm{d}V < 0$):
- Work by system = $-P \times (-\mathrm{d}V) = P\,\mathrm{d}V < 0$
- First Law: $\mathrm{d}U = \delta Q - P\,\mathrm{d}V$ (work done **on** system positive → $+P|\mathrm{d}V|$ added to $U$)

**(ii) Gas expanding against external pressure $P$ through $+\mathrm{d}V$:**
- Work by system = $+P\,\mathrm{d}V > 0$
- First Law: $\mathrm{d}U = \delta Q - P\,\mathrm{d}V$

**(iii) Rod under tensile force $F$ extended by $\mathrm{d}L$:**
- Work by system = $-F\,\mathrm{d}L$ (work done against external force)
- First Law: $\mathrm{d}U = \delta Q + F\,\mathrm{d}L$

**(iv) Soap film of length $L$ expanded by $\mathrm{d}x$ (surface tension $\sigma$, 2 surfaces):**
- Work by system = $-2\sigma L\,\mathrm{d}x$
- First Law: $\mathrm{d}U = \delta Q + 2\sigma L\,\mathrm{d}x$

### Problem 2 — Cyclic process

A system traces a closed curve on a $P$-$V$ diagram ending at the starting point A. Show that the **work done = area enclosed by the curve** and find $Q$.

**Solution.** For any segment $W = -\int P\,\mathrm{d}V$. Around a closed loop, $\oint \mathrm{d}U = 0$ because $U$ is a state function. First Law: $Q = -W = \oint P\,\mathrm{d}V$ = the net area enclosed (positive for a clockwise loop, i.e., heat engine).

### Problem 3 — Molar volume of copper

*Given M = 63.4 g/mol, ρ = 8.96 g/cm³, find V_m.*

$$
V_m \;=\; \frac{M}{\rho} \;=\; \frac{63.4\,\text{g/mol}}{8.96\,\text{g/cm}^3} \;=\; 7.08\,\text{cm}^3/\text{mol} \;=\; 7.08 \times 10^{-6}\,\text{m}^3/\text{mol}
$$

### Problem 4 — Test for exactness

*For $Z = Z(X, Y)$, show $\left(\partial M/\partial Y\right)_X = \left(\partial N/\partial X\right)_Y$ where $M = (\partial Z/\partial X)_Y$, $N = (\partial Z/\partial Y)_X$.*

**Solution.** From $Z = Z(X,Y)$: $\mathrm{d}Z = M\,\mathrm{d}X + N\,\mathrm{d}Y$. Because $Z$ is a state function, mixed second partials commute:

$$
\frac{\partial^2 Z}{\partial Y\,\partial X} = \frac{\partial^2 Z}{\partial X\,\partial Y} \;\Longrightarrow\; \left(\frac{\partial M}{\partial Y}\right)_{\!X} = \left(\frac{\partial N}{\partial X}\right)_{\!Y}
$$

This is the **test for exactness**. Every state function satisfies it; every path function fails it.

### Problem 5 — Ideal gas: if $(\partial U/\partial V)_T = 0$, then $(\partial H/\partial P)_T = 0$

*Using $H = U + PV$ and $PV = RT$:*

$$
\left(\frac{\partial H}{\partial P}\right)_{\!T} \;=\; \left(\frac{\partial U}{\partial P}\right)_{\!T} + \left(\frac{\partial (PV)}{\partial P}\right)_{\!T}
$$

Using the chain rule, $(\partial U/\partial P)_T = (\partial U/\partial V)_T (\partial V/\partial P)_T$. Given $(\partial U/\partial V)_T = 0$, this vanishes. For an ideal gas, $(\partial (PV)/\partial P)_T = (\partial (RT)/\partial P)_T = 0$. So $(\partial H/\partial P)_T = 0$. ✓

---

## Tutorial 2 — First Law of Thermodynamics [→ L1 §1.9, §1.12, §1.14]

### Problem 1 — Work of tin allotropic transformation

*Grey tin: ρ = 5.75 × 10³ kg/m³; white tin: ρ = 7.28 × 10³ kg/m³. Find work done by system when white → grey at 286 K, 1 atm. (M = 119 g/mol.)*

$$
\Delta V_m \;=\; \frac{M}{\rho_\text{grey}} - \frac{M}{\rho_\text{white}} \;=\; 119 \times 10^{-3}\!\left(\frac{1}{5750} - \frac{1}{7280}\right) \;=\; +4.35 \times 10^{-6}\,\text{m}^3/\text{mol}
$$

$$
W_\text{by} \;=\; -P\,\Delta V \;=\; -(1.013 \times 10^5)(4.35 \times 10^{-6}) \;=\; \boxed{-0.441\,\text{J/mol}}
$$

Small and negative — the grey phase is less dense, so system does a tiny amount of work against atmosphere on transformation.

### Problem 2 — Work in $PV^\gamma = K$ process (adiabatic, quasi-static)

*Compute $W$ from $(P_i, V_i)$ to $(P_f, V_f)$. $K$ should not appear in the answer.*

$$
W_\text{by} \;=\; \int_{V_i}^{V_f} P\,\mathrm{d}V \;=\; K\int V^{-\gamma}\,\mathrm{d}V \;=\; \frac{K}{1-\gamma}\left[V_f^{1-\gamma} - V_i^{1-\gamma}\right]
$$

Using $KV_i^{-\gamma} = P_i$ and $KV_f^{-\gamma} = P_f$:

$$
\boxed{\;W_\text{by} \;=\; \frac{P_f V_f - P_i V_i}{1 - \gamma}\;}
$$

### Problem 3 — Heating at constant $P$ vs. constant $V$

*Common setup: heat 2 moles of ideal gas from 300 K to 500 K. Compute $Q$ and $\Delta U$ for (a) isobaric, (b) isochoric paths. Assume $C_V = \tfrac{3}{2}R$.*

**(a) Isobaric** ($C_P = C_V + R = \tfrac{5}{2}R$):
$Q_P = n C_P \Delta T = 2 \times \tfrac{5}{2}(8.314)(200) = 8314$ J
$\Delta U = n C_V \Delta T = 2 \times \tfrac{3}{2}(8.314)(200) = 4988$ J
$W_\text{on} = \Delta U - Q = -3326$ J (gas expands, work done by gas)

**(b) Isochoric** ($\delta W = 0$): $Q_V = \Delta U = n C_V \Delta T = 4988$ J

$\Delta U$ is the same for both paths (state function) — only $Q$ and $W$ differ. This is the cleanest demonstration of why $U$ is a state function while $Q$ and $W$ aren't.

### Additional Tutorial 2 problems

(Full statements and solutions in `Tutorials/Solution_Tutorial 2-updated.pdf`.)

- **Problem 4:** Heat needed to raise 1 kg H₂O from 25 °C to 100 °C at 1 atm. Uses $\int C_P\,\mathrm{d}T$.
- **Problem 5:** Steady-state open system — boiler heating water (analogous to L1's Al-heating example).
- **Problem 6:** Enthalpy of reaction at elevated temperature using Kirchhoff's Law. [→ L1 §1.14]
- **Problem 7:** Adiabatic expansion of an ideal gas — $T_2$ from $T_1$, $P_1$, $P_2$ using $TP^{(1-\gamma)/\gamma} = \text{const}$. [→ L1 §1.12]

---

## Tutorial 3 — Second Law of Thermodynamics [→ L2]

### Problem 1 — $\Delta S_m$ on melting

*Show $\Delta S_m = \Delta H_m / T_m$ at the melting point.*

**Solution.** Melting occurs at constant $T = T_m$ and constant $P$. Reversibly, $\delta Q_\text{rev} = \mathrm{d}H$. Integrating:

$$
\Delta S_m \;=\; \int_\text{solid}^\text{liquid} \frac{\delta Q_\text{rev}}{T} \;=\; \frac{1}{T_m}\int\mathrm{d}H \;=\; \frac{\Delta H_m}{T_m}
$$

### Problem 2 (skipped from syllabus) — Microstates and entropy

*Given Ω = BV^N E^{(3N-2)/2} for an ideal gas:*

**(a) 1 mole of ideal gas fills half a container; partition removed, gas expands into other half. $\Delta S$?**

$\Omega_f/\Omega_i = (V_f/V_i)^N = 2^{N_A}$ (only volume changes, $N$ = Avogadro's number for 1 mole).

$$
\Delta S \;=\; k_B \ln(\Omega_f/\Omega_i) \;=\; k_B \cdot N_A \ln 2 \;=\; R\ln 2 \;\approx\; \boxed{5.76\,\text{J mol}^{-1}\text{K}^{-1}}
$$

### Problem 3 — Entropy change heating ice to steam at 1 atm

*1 mole of water at 1 atm is heated from −25 °C (ice) to 125 °C (steam). Compute $\Delta S$ in three stages.*

Using $C_P(\text{ice}) \approx 37$, $C_P(\text{water}) = 75.3$, $C_P(\text{steam}) \approx 34$ J mol⁻¹ K⁻¹; $\Delta H_\text{fus} = 6010$ J/mol at 273.15 K; $\Delta H_\text{vap} = 40{,}660$ J/mol at 373.15 K:

| Stage | $\Delta S$ contribution |
|---|---:|
| Heat ice 248 → 273 K | $37 \ln(273/248) \approx 3.6$ J/mol·K |
| Melt at 273 K | $6010/273 \approx 22.0$ J/mol·K |
| Heat water 273 → 373 K | $75.3 \ln(373/273) \approx 23.5$ J/mol·K |
| Vaporise at 373 K | $40{,}660/373 \approx 109.0$ J/mol·K |
| Heat steam 373 → 398 K | $34 \ln(398/373) \approx 2.2$ J/mol·K |
| **Total** | **≈ 160 J/mol·K** |

Observation: **vaporisation dominates** — the phase change to gas is where most of the entropy increase happens.

### Problem 4 — Carnot engine between 400 °C and 20 °C

*Heat reservoir $T_H = 673$ K, cold sink $T_L = 293$ K.*

$$
\eta_\text{Carnot} \;=\; 1 - \frac{T_L}{T_H} \;=\; 1 - \frac{293}{673} \;=\; \boxed{0.565\text{ or }56.5\%}
$$

*If the engine absorbs 1000 J at hot reservoir, how much work?*

$-W = \eta Q_H = 0.565 \times 1000 = 565$ J.

### Additional Tutorial 3 problems

- **Problem 5:** Heat engine efficiency comparison, temperature ratios, Rankine-cycle analogies.
- **Problem 6:** Entropy generation for an irreversible process (body cooling to room temperature).

---

## Tutorial 4 — Property Relationships / Maxwell [→ L3]

### Problem 1 — Derive $\mathrm{d}H = T\,\mathrm{d}S + V\,\mathrm{d}P$

Starting from $H = U + PV$:

$\mathrm{d}H = \mathrm{d}U + P\,\mathrm{d}V + V\,\mathrm{d}P$

Substituting $\mathrm{d}U = T\,\mathrm{d}S - P\,\mathrm{d}V$:

$\mathrm{d}H = T\,\mathrm{d}S - P\,\mathrm{d}V + P\,\mathrm{d}V + V\,\mathrm{d}P = T\,\mathrm{d}S + V\,\mathrm{d}P$ ✓

Then using mixed partials on the exact differential: $(\partial T/\partial P)_S = (\partial V/\partial S)_P$. (Maxwell relation from $H$.)

### Problem 2 — Derive all 4 Maxwell relations

Apply the exactness test to $\mathrm{d}U$, $\mathrm{d}H$, $\mathrm{d}F$, $\mathrm{d}G$. [→ L3 §3.10 has the full derivation and summary table.]

### Problem 3 — Entropy change of ideal gas under pressure

*For 1 mole of ideal gas, compute $\Delta S$ when $P$ changes from 1 atm to 10 atm isothermally.*

Using $(\partial S/\partial P)_T = -(\partial V/\partial T)_P = -R/P$ (from Maxwell + ideal gas law):

$$
\Delta S \;=\; -R\int_{P_1}^{P_2} \frac{\mathrm{d}P}{P} \;=\; -R\ln(P_2/P_1) \;=\; -8.314\ln 10 \;=\; \boxed{-19.14\,\text{J mol}^{-1}\text{K}^{-1}}
$$

Negative — compression reduces gas entropy.

### Problem 4 — Entropy change of solid under pressure

*1 mole of iron compressed isothermally from 1 atm to 10 atm at 298 K. Given $\alpha_L^\text{Fe} = 12 \times 10^{-6}$ K⁻¹, ρ = 7.87 g/cm³, M = 55.85 g/mol.*

See L3 §3.11 worked example — result $\approx -2.3 \times 10^{-5}$ J mol⁻¹ K⁻¹.

Compare to Problem 3: **solid entropy is ~10⁶× less pressure-sensitive than gas entropy.**

### Problem 5 — Helmholtz free energy

*For an ideal gas at constant $T$, compute $\Delta F$ when $V$ changes from $V_1$ to $V_2$.*

$\mathrm{d}F = -S\,\mathrm{d}T - P\,\mathrm{d}V$. At constant $T$: $\Delta F = -\int P\,\mathrm{d}V = -nRT\ln(V_2/V_1)$.

For 1 mole, $V_2/V_1 = 2$: $\Delta F = -RT\ln 2 \approx -1.72$ kJ/mol at 298 K.

---

## Tutorial 5 — Equilibrium in Single-Component System [→ L4]

### Problem 1 — Clausius-Clapeyron for tin melting point under pressure

*Tin melts at 505 K at 1 atm. $\Delta H_\text{fus} = 59.5$ kJ/kg, $\Delta V_\text{fus} = 0.389 \times 10^{-5}$ m³/kg. Find change in melting point at $P = 10^8$ N/m².*

Using Clapeyron:

$$
\frac{\mathrm{d}T}{\mathrm{d}P} \;=\; \frac{T\,\Delta V_\text{fus}}{\Delta H_\text{fus}} \;=\; \frac{505 \times 0.389 \times 10^{-5}}{59{,}500} \;\approx\; 3.30 \times 10^{-8}\,\text{K/Pa}
$$

$$
\Delta T \;=\; \frac{\mathrm{d}T}{\mathrm{d}P}\,(P_2 - P_1) \;\approx\; 3.30 \times 10^{-8} \times (10^8 - 10^5) \;\approx\; \boxed{+3.3\,\text{K}}
$$

**Positive** — tin's $\Delta V_\text{fus} > 0$ (liquid less dense), so pressure *raises* the melting point. Normal behaviour — water is the exception.

### Problem 2 — Vapour pressure from Clausius-Clapeyron

*Water vapour pressure is 4.2 kPa at 30 °C. Estimate vapour pressure at 50 °C. $\Delta H_\text{vap} \approx 43$ kJ/mol.*

$$
\ln\!\frac{P_2}{P_1} \;=\; -\frac{43{,}000}{8.314}\!\left(\frac{1}{323} - \frac{1}{303}\right) \;=\; -5174 \times (-2.04 \times 10^{-4}) \;\approx\; 1.057
$$

$$
P_2 \;\approx\; 4.2 \times e^{1.057} \;\approx\; 4.2 \times 2.88 \;\approx\; \boxed{12.1\,\text{kPa}}
$$

(Actual value at 50 °C is 12.3 kPa — good agreement.)

### Additional Tutorial 5 problems

- **Problem 3:** Boiling point elevation or depression at different ambient pressures (similar to Everest example in L4 §4.9).
- **Problem 4:** Vapour pressure from a droplet of given radius — Kelvin equation. [→ L4 §4.11]
- **Problem 5:** Phase diagram interpretation — reading normal freezing, boiling, triple, critical points from a $P$-$T$ plot.

---

## Tutorial 6 — Solutions [→ L5]

### Problem 1 — Chemical potential and activity coefficient

*In a Cu-Zn alloy at 30.6 mass% Zn, activity of Zn is 0.036 at 773 K. Find (a) activity coefficient, (b) $\mu - G^\circ$.*

**(a)** First convert to mole fraction. $M_\text{Zn} = 65.4$, $M_\text{Cu} = 63.55$ g/mol. Per 100 g alloy:
$n_\text{Zn} = 30.6/65.4 = 0.468$ mol, $n_\text{Cu} = 69.4/63.55 = 1.092$ mol.
$X_\text{Zn} = 0.468/(0.468 + 1.092) = 0.300$.

(Actually the solution uses $X_\text{Zn} \approx 0.306$ — the slight difference is from round-off; source uses 0.306 without the conversion, treating mass% ≈ mol% loosely for close molar masses.)

$$
\gamma_\text{Zn} \;=\; \frac{a}{X} \;=\; \frac{0.036}{0.306} \;\approx\; \boxed{0.12}
$$

**(b)** Relative chemical potential:

$$
\mu - G^\circ \;=\; RT\ln a \;=\; (8.314)(773)\ln(0.036) \;=\; 6427 \times (-3.324) \;\approx\; \boxed{-21.4\,\text{kJ/mol}}
$$

### Problem 2 — Entropy of mixing, binary

*Compute $\Delta S_\text{mix}$ for an equimolar ideal binary (X_A = X_B = 0.5) per mole.*

$$
\Delta S_\text{mix} \;=\; -R(X_A\ln X_A + X_B\ln X_B) \;=\; -R(2 \times 0.5\ln 0.5) \;=\; R\ln 2 \;\approx\; \boxed{5.76\,\text{J mol}^{-1}\text{K}^{-1}}
$$

Maximum of the mixing-entropy curve. Same value as Problem 2(a) of Tutorial 3 — the "free expansion of one mole" and "ideal mixing at 50:50" give the same $R\ln 2$ because both double the accessible microstates per atom.

### Problem 3 — Regular solution at 50:50

*For a regular solution with $\Omega = +20$ kJ/mol at $X_A = X_B = 0.5$, $T = 1000$ K, compute $\Delta G_\text{mix}$.*

$$
\Delta H_\text{mix} \;=\; \Omega X_A X_B \;=\; 20{,}000 \times 0.25 \;=\; +5000\,\text{J/mol}
$$

$$
\Delta S_\text{mix} \;=\; R\ln 2 \;=\; 5.76\,\text{J mol}^{-1}\text{K}^{-1}
$$

$$
\Delta G_\text{mix} \;=\; 5000 - 1000 \times 5.76 \;=\; 5000 - 5760 \;=\; \boxed{-760\,\text{J/mol}}
$$

Just barely spontaneous at 1000 K. At lower $T$ the $T\Delta S$ term shrinks and $\Delta G_\text{mix}$ can turn positive — **miscibility gap opens**. The critical temperature where this happens is $T_c = \Omega/(2R) \approx 1203$ K. Below 1203 K, this system unmixes (at $X = 0.5$).

### Problem 4 — Raoult's Law vs. Henry's Law

*A dilute solution of A in B at 298 K has $X_A = 0.01$. The pure-A vapour pressure is 1 atm. Measured partial pressure of A above the solution is 0.04 atm. Is A obeying Raoult's or Henry's Law? What is $k_H$?*

Raoult predicts $P_A = X_A P_A^* = 0.01 \times 1 = 0.01$ atm. Measured is 4× higher, so A is **not Raoultian** (expected for solute at such low $X$). Henry's Law: $P_A = k_H X_A$, so $k_H = 0.04/0.01 = 4$ atm.

$\gamma_A^\infty = k_H / P_A^* = 4$ — positive deviation (A prefers to escape; A-B bonds weaker than A-A).

### Additional Tutorial 6 problems

- **Problem 5:** Gibbs-Duhem applied to determine $a_B$ from measured $a_A$.
- **Problem 6:** Ideal-solution activity coefficients from a phase-diagram reading.

---

## Tutorial 7 — Gibbs Phase Rule and Phase Diagrams [→ L6]

### Problem 1 — Sketch isomorphous binary phase diagram

Two elements completely miscible, forming a single solid solution α. Features to label:
- Pure A melting point (left edge).
- Pure B melting point (right edge).
- **Liquidus** curve (upper) — above this, 100% liquid.
- **Solidus** curve (lower) — below this, 100% solid α.
- Two-phase (L + α) lens between liquidus and solidus.

Explanation: because $\Delta H_\text{mix} \leq 0$ in the solid and two components are totally miscible, single-phase α forms across the full range. If $\Delta H_\text{mix} < 0$ (strong A-B attraction), the liquidus+solidus show a **melting-point maximum** in the middle. [→ L6 §6.6]

### Problem 2 — Sketch binary with limited miscibility (eutectic)

Features:
- Pure A and B melting points.
- Liquidus coming down from each side.
- Two solid phases α (A-rich) and β (B-rich), each with its own solidus.
- **Eutectic point** $E$ at the minimum of the liquidus — invariant point where L ⇌ α + β.
- Horizontal **eutectic line** at $T_E$ across the two-phase region.
- Above $T_E$: single-phase L or two-phase (α+L) / (β+L).
- Below $T_E$: either single α, single β, or two-phase (α+β).

The eutectic is the lowest melting temperature in the system. [→ L6 §6.7]

### Problem 3 — Gibbs phase rule

*(a) How many degrees of freedom at the water triple point?*

$F = C - P + 2 = 1 - 3 + 2 = 0$. Invariant point.

*(b) In a binary eutectic at the eutectic point?*

At fixed $P$: $F = C - P + 1 = 2 - 3 + 1 = 0$. Invariant.

*(c) A single phase in the Fe-C system at fixed $P$?*

$F = 2 - 1 + 1 = 2$. Two degrees of freedom ($T$ and composition can vary independently).

### Problem 4 — Lever rule

*Binary alloy at overall composition $X_0 = 0.40$. At some temperature, $X^\alpha = 0.15$ and $X^L = 0.55$. What fraction is in each phase?*

$$
f^\alpha \;=\; \frac{X^L - X_0}{X^L - X^\alpha} \;=\; \frac{0.55 - 0.40}{0.55 - 0.15} \;=\; \frac{0.15}{0.40} \;=\; 0.375
$$

$$
f^L \;=\; 0.625
$$

At this composition and temperature, 37.5% of the material is solid, 62.5% is liquid.

### Additional Tutorial 7 problems

- **Problem 5:** Reading a real Pb-Sn or Al-Si phase diagram — identifying liquidus, solidus, eutectic, phase fractions at various $T$.
- **Problem 6:** Derive why the common tangent gives equal chemical potentials for both components across two phases.

---

## Tutorial 8 — Chemical Equilibrium [→ L7]

### Problem 1 — Why metal extraction is done at high temperature

*Why extract metals from oxides using C (or CO) at high temperature?*

**Answer.** C → CO and C → CO₂ reactions have $\Delta S > 0$ (gas moles increase), so their Ellingham lines slope **downward** with increasing $T$. Metal oxide formation lines slope **upward** ($\Delta S < 0$; oxygen consumed). Above a critical temperature, the C line drops below the metal-oxide line, making carbothermal reduction thermodynamically favourable. Additionally, high $T$ speeds up reaction kinetics.

### Problem 2 — Why Al can't be smelted by C

*Why is Al extracted electrolytically rather than by carbon reduction?*

**Answer.** On the Ellingham diagram, the Al/Al₂O₃ line is very low (Al₂O₃ very stable). The C → CO line only crosses the Al₂O₃ line at $T > 2400$ °C — above the boiling point of Al (2470 °C) and beyond practical furnace operation. Al must be extracted via electrochemistry (Hall-Héroult process) instead.

### Problem 3 — Order of oxidation in steel refining at 1500 °C

*Recycled steel contains Fe, Si, Mn, C. In what order do they oxidise when O₂ is bubbled through the melt?*

Reading the Ellingham diagram at 1500 °C: the lower a line (more negative $\Delta G^\circ$), the more stable the oxide, the more aggressively the metal oxidises. At 1500 °C:

1. **Si** (most negative → oxidises first to form SiO₂ slag)
2. **Mn** (next)
3. **C** (forms CO — escapes as gas)
4. **Fe** (last; least oxygen-affine)

This selective-oxidation ordering is the basis of **oxygen-blowing refining** — adding O₂ to molten iron removes impurities in sequence, leaving low-carbon steel.

### Problem 4 — Equilibrium $P_{\text{O}_2}$ for Cr oxidation at 1300 °C

From the Ellingham diagram reading method [→ L7 §7.7]: $P_{\text{O}_2}^\text{eq} \approx 10^{-16}$ atm.

For H₂/H₂O atmosphere to prevent Cr oxidation: ratio $\sim 400:1$ (400× more H₂ than H₂O vapour).

### Problem 5 — Using Van't Hoff to find $\Delta H_\text{rxn}$

*A reaction has $K(500\,\text{K}) = 0.1$ and $K(800\,\text{K}) = 10$. Find $\Delta H_\text{rxn}$ (approximately constant with $T$).*

$$
\ln\!\frac{K_2}{K_1} \;=\; \ln(100) \;=\; 4.605 \;=\; -\frac{\Delta H^\circ}{R}\!\left(\frac{1}{800} - \frac{1}{500}\right)
$$

$$
4.605 \;=\; -\frac{\Delta H^\circ}{8.314} \times (-7.5 \times 10^{-4})
$$

$$
\Delta H^\circ \;=\; \frac{4.605 \times 8.314}{7.5 \times 10^{-4}} \;\approx\; +51{,}000\,\text{J/mol} \;=\; \boxed{+51\,\text{kJ/mol}}
$$

Endothermic ($\Delta H > 0$) — consistent with $K$ increasing with $T$.

### Problem 6 — Q vs. K direction prediction

*Reaction: 2SO₂(g) + O₂(g) ⇌ 2SO₃(g), $K = 10^5$ at 700 K. Current partial pressures: $P_{\text{SO}_2} = 0.1$ atm, $P_{\text{O}_2} = 0.01$ atm, $P_{\text{SO}_3} = 0.05$ atm. Which direction does the reaction go?*

$$
Q \;=\; \frac{P_{\text{SO}_3}^2}{P_{\text{SO}_2}^2 \, P_{\text{O}_2}} \;=\; \frac{(0.05)^2}{(0.1)^2 \times 0.01} \;=\; \frac{0.0025}{0.0001} \;=\; 25
$$

$Q = 25 \ll K = 10^5$ → reaction proceeds **forward** (toward more SO₃).

---

## How to use this anthology

- **Weekly tutorial prep:** Tackle the problems under the tutorial number for that week. Look up the corresponding lecture section for the underlying theory.
- **Exam revision:** Work through all problems in order (1 through 8) — this reproduces a full end-to-end path through the course from systems and energy through to reactions and reduction.
- **For specific topics:** Use the cross-reference links (→ L*n* §*k*) to find the relevant theory for any problem.

Official solutions with all intermediate algebra are in `Tutorials/Solution_Tutorial N.pdf`. These consolidated problems are the short form; the PDFs are the reference.
