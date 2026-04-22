# MS1016 Cheat Sheet — One-Page Formula Summary

## The Laws

**0th:** A ≡ C, B ≡ C ⟹ A ≡ B (defines temperature)
**1st:** $\;\Delta U = Q + W\;$ ($Q$ into system, $W$ done on system)
**2nd:** $\;\mathrm{d}S = \delta Q_\text{rev}/T\;$ and $\;\Delta S_\text{universe} \geq 0$
**3rd:** $S \to 0$ as $T \to 0$ for a perfect crystal

## Constants

$R = 8.314\;\text{J mol}^{-1}\text{K}^{-1}\,$ · $\,k_B = 1.38\times 10^{-23}$ J/K · $\,N_A = 6.022\times 10^{23}$

## Differential forms

| Potential | Definition | Differential | Natural vars |
|---|---|---|---|
| $U$ | internal energy | $\mathrm{d}U = T\,\mathrm{d}S - P\,\mathrm{d}V$ | $S, V$ |
| $H$ | $U + PV$ | $\mathrm{d}H = T\,\mathrm{d}S + V\,\mathrm{d}P$ | $S, P$ |
| $F$ | $U - TS$ | $\mathrm{d}F = -S\,\mathrm{d}T - P\,\mathrm{d}V$ | $T, V$ |
| $G$ | $H - TS$ | $\mathrm{d}G = -S\,\mathrm{d}T + V\,\mathrm{d}P$ | $T, P$ |
| $\mu$ | $G/n$ | $\mathrm{d}\mu = -\underline{S}\,\mathrm{d}T + \underline{V}\,\mathrm{d}P$ | $T, P$ |

## Key partials

$$
\left(\tfrac{\partial G}{\partial T}\right)_{\!P} = -S, \quad
\left(\tfrac{\partial G}{\partial P}\right)_{\!T} = V, \quad
C_P = \left(\tfrac{\partial H}{\partial T}\right)_{\!P}, \quad
C_V = \left(\tfrac{\partial U}{\partial T}\right)_{\!V}
$$

## Heat capacities & ideal gas

$C_P - C_V = R$ (ideal gas, per mole)
Monoatomic: $C_V = \tfrac{3}{2}R$, $C_P = \tfrac{5}{2}R$, $\gamma = 5/3$
Diatomic: $C_V = \tfrac{5}{2}R$, $C_P = \tfrac{7}{2}R$, $\gamma = 7/5$
$\Delta H = \int_{T_1}^{T_2} C_P\,\mathrm{d}T$ · $\,\Delta S = \int_{T_1}^{T_2} \tfrac{C_P}{T}\,\mathrm{d}T$

## Ideal gas shortcuts

$PV = nRT$ · $\,(\partial U/\partial V)_T = 0$ · $\,(\partial H/\partial P)_T = 0$
Adiabatic reversible: $\;PV^\gamma = \text{const},\;\,TV^{\gamma-1} = \text{const},\;\,TP^{(1-\gamma)/\gamma} = \text{const}$
Isothermal entropy (1 mol): $\;\Delta S = -R\ln(P_2/P_1) = R\ln(V_2/V_1)$

## Four Maxwell relations

$$
\left(\tfrac{\partial T}{\partial V}\right)_{\!S} = -\left(\tfrac{\partial P}{\partial S}\right)_{\!V}, \qquad
\left(\tfrac{\partial T}{\partial P}\right)_{\!S} = \left(\tfrac{\partial V}{\partial S}\right)_{\!P}
$$
$$
\left(\tfrac{\partial S}{\partial V}\right)_{\!T} = \left(\tfrac{\partial P}{\partial T}\right)_{\!V}, \qquad
\left(\tfrac{\partial S}{\partial P}\right)_{\!T} = -\left(\tfrac{\partial V}{\partial T}\right)_{\!P}
$$

## Entropy

Boltzmann: $\;S = k_B\ln\Omega$
Standard entropy: $\;S^\circ_{298} = \int_0^{298} (C_P/T)\,\mathrm{d}T + \sum \Delta H_\text{trans}/T_\text{trans}$
Reaction: $\;\Delta S^\circ_\text{rxn} = \sum_p n_p S^\circ_p - \sum_r n_r S^\circ_r$
Phase change: $\;\Delta S_\text{trans} = \Delta H_\text{trans}/T_\text{trans}$

## Free energy & spontaneity

$\Delta G = \Delta H - T\,\Delta S$ at constant $T$
$\Delta G < 0\,$: spontaneous · $\,\Delta G = 0\,$: equilibrium · $\,\Delta G > 0$: reverse spontaneous
**2×2 matrix:**

| | $\Delta H < 0$ | $\Delta H > 0$ |
|---|---|---|
| $\Delta S > 0$ | spontaneous all $T$ | spontaneous high $T$ |
| $\Delta S < 0$ | spontaneous low $T$ | never spontaneous |

## Single-component phase equilibrium

Criterion: $\;\mu_A^\alpha = \mu_A^\beta$ at equilibrium
Clapeyron: $\;\tfrac{\mathrm{d}P}{\mathrm{d}T} = \tfrac{\Delta_\text{trs} S}{\Delta_\text{trs} V} = \tfrac{\Delta_\text{trs} H}{T\,\Delta_\text{trs} V}$
Clausius-Clapeyron (liquid-vapour): $\;\tfrac{\mathrm{d}\ln P}{\mathrm{d}T} = \tfrac{\Delta_\text{vap} H}{RT^2}$
Integrated: $\;\ln(P_2/P_1) = -\tfrac{\Delta_\text{vap} H}{R}(1/T_2 - 1/T_1)$
Kelvin (droplet): $\;\ln(P/P^{*}) = \tfrac{2\gamma V_\text{liq}}{RTr}$

## Solutions

Chemical potential in mixture: $\;\mu_i = \mu_i^\circ + RT\ln a_i$, with $a_i = \gamma_i X_i$
Ideal solution: $a_i = X_i$, $\gamma_i = 1$
$\Delta G_\text{mix}^\text{ideal} = RT\sum_i X_i\ln X_i < 0$
$\Delta S_\text{mix}^\text{ideal} = -R\sum_i X_i\ln X_i > 0$
$\Delta H_\text{mix}^\text{ideal} = 0$
Regular solution: $\;\Delta H_\text{mix} = \Omega X_A X_B$
Raoult ($X \to 1$): $\gamma \to 1$, $P_i = X_i P_i^{*}$
Henry ($X \to 0$): $\gamma \to \gamma^\infty$, $P_i = k_H X_i$
Gibbs-Duhem: $\;X_A\,\mathrm{d}\mu_A + X_B\,\mathrm{d}\mu_B = 0$ at constant $T, P$

## Phase rule & diagrams

**Gibbs phase rule:** $\;F = C - P + 2\;$ (general) · $F = C - P + 1\;$ (fixed $P$)
Common tangent: $\mu_i^\alpha = \mu_i^\beta$ requires tangent lines to $G^\alpha$ and $G^\beta$ to coincide
Lever rule: $\;f^\alpha = (X^\beta - X_0)/(X^\beta - X^\alpha)$, $\;f^\beta = (X_0 - X^\alpha)/(X^\beta - X^\alpha)$
Eutectic: 3-phase invariant at fixed $P$ in binary, L → $\alpha + \beta$ on cooling

## Chemical equilibrium

$\Delta G_\text{rxn}^\circ = \sum_p n_p \Delta G_f^\circ - \sum_r n_r \Delta G_f^\circ$
$\Delta G^\circ = -RT\ln K\;$ ⟺ $\;K = \exp(-\Delta G^\circ/RT)$
For $aA + bB \rightleftharpoons cC + dD$: $\;K = \dfrac{a_C^c\,a_D^d}{a_A^a\,a_B^b}$
Reaction direction: $Q < K$ forward, $Q > K$ backward, $Q = K$ equilibrium
Pure solids/liquids: activity $= 1$ (drop from $K$ expression)
Ideal gas: $a_i = P_i/P^\circ$

**Temperature dependence (Van't Hoff):** $\;\dfrac{\mathrm{d}\ln K}{\mathrm{d}T} = \dfrac{\Delta H_\text{rxn}^\circ}{RT^2}$
Integrated: $\;\ln(K_2/K_1) = -\dfrac{\Delta H^\circ}{R}(1/T_2 - 1/T_1)$
**Le Chatelier:** $T\uparrow$ favours endothermic direction; $T\downarrow$ favours exothermic.

**Heat engine Carnot efficiency:** $\;\eta = 1 - T_L/T_H$

## Heat engines (§2.9)

$\eta_\text{Carnot} = (T_H - T_L)/T_H$
Rankine cycle: 1→2 pump (isentropic), 2→3 boiler (constant $P$), 3→4 turbine (isentropic), 4→1 condenser (constant $P$)
Net work per cycle = enclosed area on $P$-$V$; net heat = enclosed area on $T$-$S$.

## Useful differentials you'll see again

$\mathrm{d}(PV) = P\,\mathrm{d}V + V\,\mathrm{d}P$ (product rule)
$\mathrm{d}\ln x = \mathrm{d}x/x$
$\int \mathrm{d}x/x = \ln|x|$

## Six thermodynamic path conditions

| Name | What's constant |
|---|---|
| Isobaric | $P$ ($\mathrm{d}P = 0$) |
| Isochoric | $V$ ($\mathrm{d}V = 0$, no $PV$ work) |
| Isothermal | $T$ |
| Isentropic | $S$ (reversible adiabatic) |
| Isenthalpic | $H$ (e.g. Joule-Thomson) |
| Adiabatic | no heat flow ($\delta Q = 0$) |

## Common pitfalls checklist

- ☐ Don't confuse $C_P$ with $C_V$ — $C_P$ for constant-$P$ heating, $C_V$ for constant-$V$.
- ☐ Reactions at constant $P$: use $\Delta H$. At constant $V$: use $\Delta U$.
- ☐ $\int C_P\,\mathrm{d}T$ for $\Delta H$; $\int (C_P/T)\,\mathrm{d}T$ for $\Delta S$. Don't mix.
- ☐ Phase changes: add $\Delta H_\text{trans}$ or $\Delta H_\text{trans}/T$ separately — don't skip them.
- ☐ Products minus reactants, with stoichiometric coefficients, for every $\Delta$ of reaction.
- ☐ Activities: pure solid/liquid = 1; ideal gas = $P_i/P^\circ$; solution ideal = $X_i$.
- ☐ Equilibrium: $\mu_A^\alpha = \mu_A^\beta$ for **every component**, in **every phase pair**.
- ☐ Ordered vs. disordered, eutectic vs. peritectic — draw the common tangent, count phases.
- ☐ Van't Hoff sign: $\Delta H^\circ > 0$ → $K$ rises with $T$; $\Delta H^\circ < 0$ → $K$ falls with $T$.
- ☐ $\Delta G < 0$ means thermodynamically allowed, NOT kinetically fast.
