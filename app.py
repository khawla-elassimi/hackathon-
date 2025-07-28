import streamlit as st
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary

st.title("Planification Maintenance Optimale avec Minimisation des Coûts")

# --- Génération données plus grandes ---
random.seed(123)

components = [f"C{i}" for i in range(1, 11)]
skills = [f"S{i}" for i in range(1, 6)]
employees = [f"P{i}" for i in range(1, 7)]
days = list(range(1, 11))

phi = {p: 8 for p in employees}
delta = {c: random.randint(1, 3) for c in components}
lambda1 = 1000

alpha = {(s, p): random.choices([0, 1], weights=[0.3, 0.7])[0] for s in skills for p in employees}
tau = {(c, s, p): random.randint(2, 6)
       for c in components for s in skills for p in employees if alpha.get((s, p), 0) == 1}
C = {(c, s, p, t): random.randint(100, 500) for (c, s, p) in tau.keys() for t in days}
beta = {(random.choice(components), random.choice(days)): 1 for _ in range(20)}

# --- Modèle ---
model = LpProblem("Planification_Maintenance", LpMinimize)
x = LpVariable.dicts("x", [(c, s, p, t) for (c, s, p) in tau.keys() for t in days], cat=LpBinary)
z = LpVariable.dicts("z", [(c, s, t) for c in components for s in skills for t in days], cat=LpBinary)

cost_term = lpSum(C.get((c, s, p, t), 0) * x[(c, s, p, t)] for (c, s, p) in tau.keys() for t in days)
penalty_term = lpSum(beta.get((c, t), 0) * (1 - lpSum(z[(c, s, tt)] for tt in days if t <= tt <= t + delta[c]))
                     for c in components for s in skills for t in days if beta.get((c, t), 0) == 1)
model += cost_term + lambda1 * penalty_term

for (c, s, p) in tau.keys():
    for t in days:
        model += x[(c, s, p, t)] <= z[(c, s, t)]

for c in components:
    for s in skills:
        for t in days:
            model += lpSum(x[(c, s, p, t)] for p in employees if (c, s, p) in tau.keys()) == z[(c, s, t)]

for p in employees:
    for t in days:
        model += lpSum(tau[(c, s, p)] * x[(c, s, p, t)]
                       for (c, s, p_) in tau.keys() if p_ == p) <= phi[p]

for c in components:
    for s in skills:
        for t in days:
            if beta.get((c, t), 0) == 1:
                model += lpSum(z[(c, s, tt)] for tt in days if t <= tt <= t + delta[c]) == 1

# --- Résolution ---
model.solve()

# --- Extraction résultats ---
planification = []
for (c, s, p, t), var in x.items():
    if var.varValue == 1:
        planification.append({"Composant": c, "Compétence": s, "Employé": p, "Jour": t,
                             "Durée": tau[(c, s, p)], "Coût": C[(c, s, p, t)]})

df_plan = pd.DataFrame(planification)

# Affichage DataFrame dans Streamlit
st.subheader("Planification détaillée")
st.dataframe(df_plan)

# Calcul et affichage coût total minimisé
total_cost = df_plan["Coût"].sum()
st.markdown(f"## Coût total minimisé : **{total_cost} unités**")

# --- Visualisation Gantt par composant ---
fig, ax = plt.subplots(figsize=(14, 8))
colors = sns.color_palette("Set2", len(skills))
color_map = dict(zip(skills, colors))
for i, c in enumerate(components):
    df_c = df_plan[df_plan.Composant == c]
    for _, row in df_c.iterrows():
        ax.barh(i, row.Durée, left=row.Jour - 1, color=color_map[row.Compétence], edgecolor='black', alpha=0.7)
        ax.text(row.Jour - 0.5 + row.Durée / 2, i, row.Employé, ha='center', va='center', fontsize=7, color='black')
ax.set_yticks(range(len(components)))
ax.set_yticklabels(components)
ax.set_xlabel("Jour")
ax.set_title("Diagramme de Gantt : Planification maintenance par composant")
ax.grid(axis='x')
plt.tight_layout()
st.pyplot(fig)

# --- Heatmap interventions par employé et jour ---
heatmap_data = df_plan.groupby(['Employé', 'Jour']).size().unstack(fill_value=0)
fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", cbar=True, linewidths=0.5, linecolor='gray', ax=ax2)
ax2.set_title("Nombre d'interventions par employé et jour")
ax2.set_xlabel("Jour")
ax2.set_ylabel("Employé")
st.pyplot(fig2)

# --- Histogramme des coûts ---
fig3, ax3 = plt.subplots(figsize=(8, 5))
sns.histplot(df_plan.Coût, bins=20, kde=True, ax=ax3)
ax3.set_title("Distribution des coûts des interventions")
ax3.set_xlabel("Coût")
ax3.set_ylabel("Nombre d'interventions")
plt.tight_layout()
st.pyplot(fig3)




