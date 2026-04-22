# MS1016 — Consolidated Notes Master Index

**Thermodynamics of Materials · NTU · Prof Leonard Ng · 2025-26 S1**

> This is the master table-of-contents and cross-reference document for the consolidated lecture notes (L0–L7). All lectures follow a consistent structure: learning outcomes → derivations → worked examples → common-mistake callouts → "Test Your Understanding" answers → source-slide corrections.

---

## Lecture roster

| # | Title | File | Length | Figures |
|---|---|---|---:|---:|
| L0 | [Introduction to Thermodynamics](L0.md) | L0.md | 477 lines | 12 |
| L1 | [The First Law: Conservation of Energy](L1.md) | L1.md | 922 lines | 10 |
| L2 | [The Second Law: Entropy and Direction](L2.md) | L2.md | 470 lines | 11 |
| L3 | [Free Energy, Property Relationships, Equilibrium](L3.md) | L3.md | 559 lines | 1 |
| L4 | [Phase Equilibrium in Single-Component Systems](L4.md) | L4.md | 489 lines | 5 |
| L5 | [Solid Solutions and Multi-Component Systems](L5.md) | L5.md | 548 lines | 6 |
| L6 | [Gibbs Phase Rule and Phase Diagrams](L6.md) | L6.md | 403 lines | 10 |
| L7 | [Chemical Equilibrium](L7.md) | L7.md | 515 lines | 10 |
| — | [Key-equation cheat sheet](CHEAT_SHEET.md) | | 1 page | — |
| — | [Tutorial problems anthology](TUTORIALS.md) | | 8 tutorials | — |

**Total:** 4,383 lines of markdown, 65 inline figures, ~42K words.

---

## Reading paths

### Start-to-finish (standard course flow)
L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7

### Just-the-math (derivations-heavy)
L3 (§3.9–3.11, Maxwell) → L6 (§6.3, Gibbs phase rule derivation) → L7 (§7.10, Gibbs-Helmholtz and Van't Hoff)

### Materials-science first
L4 → L5 → L6 → L7 (get to phase diagrams, solid solutions, and reactions quickly; refer back to L0–L3 as needed)

### Exam revision (last two weeks)
CHEAT_SHEET.md → TUTORIALS.md → skim "Worked example" sections across L1, L4, L7

---

## Cross-reference by topic

### Foundational concepts

| Topic | Introduced in | Used later in |
|---|---|---|
| Systems, boundaries | L0 §0.4, L1 §1.2 | every lecture |
| State vs. path functions | L0 §0.5, L1 §1.4 | L2, L3, L7 |
| Intensive vs. extensive | L0 §0.5, L1 §1.2 | L5, L6 |
| Equilibrium | L0 §0.6, L3 §3.8 | L4–L7 |
| Sign convention ($\Delta U = Q + W$) | L1 §1.3 | L2, L7 |

### Mathematical toolkit

| Topic | Introduced in | Used later in |
|---|---|---|
| Differentiation rules | L0 §0.9 | L1, L3 |
| Partial derivatives & total differential | L0 §0.9, L3 §3.9 | everywhere |
| Exact vs. inexact differentials | L0 §0.9, L1 §1.4 | L3 (Maxwell), L7 |
| Integration (for $\int C_P\,\mathrm{d}T$, etc.) | L1 §1.9 | L2, L7 |

### The Laws

| Law | Stated in | Used in | Key equations |
|---|---|---|---|
| Zeroth | L0 §0.2 | — | — |
| First | L1 §1.3 | L1, L2, L3, L7 | $\Delta U = Q + W$, $\mathrm{d}H = \delta Q_P$ |
| Second | L2 §2.3 | L2, L3, L4, L6, L7 | $\mathrm{d}S = \delta Q_\text{rev}/T$, $\Delta S_\text{univ} \geq 0$ |
| Third | L2 §2.5 | L2 (standard entropy) | $S \to 0$ as $T \to 0$ |

### Thermodynamic potentials

| Potential | Definition | Where derived | Used in |
|---|---|---|---|
| $U$ | internal energy | L0 §0.7 | L1, L2, L3 |
| $H = U + PV$ | enthalpy | L1 §1.7 | L1, L2, L7 |
| $F = U - TS$ | Helmholtz | L3 §3.3 | L3 (rarely used in engineering) |
| $G = H - TS$ | Gibbs | L3 §3.2 | L3, L4, L5, L6, L7 |
| $\mu = G/n$ | chemical potential | L4 §4.2, L5 §5.2 | L4, L5, L6, L7 |

### Phase equilibria

| Topic | Lecture | Section |
|---|---|---|
| Equilibrium criterion $\mu_A = \mu_B$ | L4 | §4.3 |
| Single-component phase diagrams | L4 | §4.7 |
| Clapeyron equation | L4 | §4.8 |
| Clausius-Clapeyron | L4 | §4.9 |
| Kelvin equation (droplet) | L4 | §4.11 |
| Gibbs energy of solution | L5 | §5.4–5.6 |
| Ideal solution (zero $\Delta H_\text{mix}$) | L5 | §5.5 |
| Regular solution (non-zero $\Delta H_\text{mix}$) | L5 | §5.7 |
| Gibbs-Duhem equation | L5 | §5.9 |
| Multi-phase equilibrium | L6 | §6.2 |
| Gibbs phase rule $F = C - P + 2$ | L6 | §6.3 |
| Common tangent construction | L6 | §6.4 |
| Lever rule | L6 | §6.5 |
| Isomorphous, eutectic, peritectic | L6 | §6.6–6.8 |

### Reactions and their direction

| Topic | Lecture | Section |
|---|---|---|
| Reaction quotient $Q$ and equilibrium constant $K$ | L7 | §7.3–7.4 |
| $\Delta G^\circ = -RT\ln K$ | L7 | §7.4 |
| Hess's Law for $\Delta H$ | L1 | §1.13 |
| Hess's Law for $\Delta G$ | L3 | §3.6 |
| Kirchhoff's Law for $\Delta H(T)$ | L1 | §1.14 |
| Kirchhoff's Law for $\Delta S(T)$ | L2 | §2.6 |
| Solid-vapour equilibrium | L7 | §7.5 |
| Ellingham diagram | L7 | §7.7 |
| Van't Hoff equation $\mathrm{d}\ln K/\mathrm{d}T$ | L7 | §7.8, 7.10 |

### Practical applications (engineering context)

| Application | Lecture | Section |
|---|---|---|
| Heating Al for casting | L1 | §1.10 |
| Joule-Thomson valve cooling | L1 | §1.12 |
| FeO + CO reduction (blast furnace) | L1 | §1.14 |
| Heat-engine / Carnot efficiency | L2 | §2.9 |
| Rankine cycle (power plants) | L2 | §2.10 |
| Metastability (diamond, tempered glass, austenite) | L3 | §3.7 |
| Water's anomalous ice-skate physics | L4 | §4.5 |
| Joule-Thomson of He tank | L4 | §4.12 |
| Grain coarsening / Ostwald ripening | L4 | §4.12 |
| Cu-Au ordering (superalloys) | L5 | §5.8 |
| Pb-Sn solder eutectic | L6 | §6.7 |
| Fe-C phase diagram (steel heat treatment) | L6 | §6.8 |
| Controlling metal oxidation with H$_2$/H$_2$O or CO/CO$_2$ | L7 | §7.7 |

---

## Unit reminders

- $R = 8.314$ J mol$^{-1}$ K$^{-1}$ (universal gas constant)
- $k_B = 1.38 \times 10^{-23}$ J K$^{-1}$ (Boltzmann constant)
- $N_A = 6.022 \times 10^{23}$ mol$^{-1}$ (Avogadro's number)
- Standard state $P^\circ = 1$ atm $= 101{,}325$ Pa
- Standard state $T = 298$ K (or 298.15 K for high-precision work)
- $1\text{ atm·L} = 101.3$ J

---

## Sign convention (used throughout these notes)

$$
\Delta U \;=\; Q \;+\; W
$$

with:
- $Q > 0$: heat **absorbed by** the system
- $W > 0$: work done **on** the system
- $\delta W = -P\,\mathrm{d}V$ for reversible expansion/compression

The original course slides occasionally use $\Delta U = Q - W$ (work done *by* the system); this is flagged in L1 and L2's corrections. All formulas and worked examples in these consolidated notes use the "work-on" convention consistently.

---

## Files in this folder

```
consolidated/
├── INDEX.md          (this file)
├── CHEAT_SHEET.md    (one-page formula summary)
├── TUTORIALS.md      (problems and solutions for Tutorials 1-8)
├── L0.md ... L7.md   (main lecture notes)
└── images/
    ├── L0/ ... L7/   (figures, named by source page)
```

## To open

- **VS Code** — install "Markdown Preview Enhanced" or use the built-in preview; supports LaTeX math via MathJax.
- **Obsidian** — open the `consolidated/` folder as a vault; links between files work as wiki-links.
- **GitHub** — if you push this folder to a repo, GitHub renders everything with LaTeX support via MathJax.
- **Browser** — via any live markdown server (e.g. `markdown-preview-enhanced` from VS Code exports to HTML).
- **LaTeX/PDF** — see the [LaTeX build README](../../../latex/README.md) for pandoc conversion and Overleaf upload instructions.
