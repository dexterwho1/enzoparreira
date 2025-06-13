import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

DB_PATH = "crm_data.db"

st.title("Liste des commandes")

# --- Récupération des données ---
with sqlite3.connect(DB_PATH) as conn:
    commandes = pd.read_sql_query("SELECT * FROM commandes", conn)
    clients = pd.read_sql_query("SELECT * FROM clients", conn)

# --- Jointure pour nom client ---
commandes = commandes.merge(clients[['client_id', 'name']], on='client_id', how='left', suffixes=('', '_client'))

# --- Filtres ---
col1, col2, col3, col4 = st.columns([2,2,2,2])
with col1:
    filtre_txt = st.text_input("Rechercher...")
with col2:
    filtre_client = st.selectbox("Client", ["Tous"] + sorted(clients['name'].unique().tolist()))
with col3:
    filtre_service = st.selectbox("Service", ["Tous"] + sorted(commandes['prestation'].dropna().unique().tolist()))
with col4:
    filtre_statut = st.selectbox("Statut", ["Tous", "En retard", "À l'heure", "Livré"])

# --- Application des filtres ---
df = commandes.copy()
if filtre_txt:
    mask = df['prestation'].str.contains(filtre_txt, case=False, na=False) | df['name'].str.contains(filtre_txt, case=False, na=False)
    df = df[mask]
if filtre_client != "Tous":
    df = df[df['name'] == filtre_client]
if filtre_service != "Tous":
    df = df[df['prestation'] == filtre_service]

# --- Calcul du statut ---
def get_statut(row):
    if row.get('statut') == 'livré':
        return 'Livré'
    try:
        date_fin = pd.to_datetime(row['date_fin']).date()
    except:
        return 'À l\'heure'
    today = date.today()
    if date_fin < today:
        return 'En retard'
    else:
        return "À l'heure"

def get_jours_restant(row):
    try:
        date_fin = pd.to_datetime(row['date_fin']).date()
    except:
        return "-"
    today = date.today()
    if date_fin >= today and row.get('statut') != 'livré':
        return f"{(date_fin - today).days} j restants"
    return "-"

# --- Affichage du tableau ---
if df.empty:
    st.info("Aucune commande trouvée.")
else:
    st.write("")
    headers = ["Client", "Service", "Date de début", "Date de fin", "Temps passé", "Prix", "Statut", "Prix/horaire", "Action"]
    col_widths = [2,2,1.5,1.5,1,1,1.5,1,1.5]
    header_cols = st.columns(col_widths)
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")
    for idx, row in df.iterrows():
        statut = get_statut(row)
        jours = get_jours_restant(row)
        is_livre = row.get('statut') == 'livré'
        line_cols = st.columns(col_widths)
        line_cols[0].write(row['name'])
        line_cols[1].write(row['prestation'])
        line_cols[2].write(row['date_debut'])
        line_cols[3].write(row['date_fin'])
        line_cols[4].write(row.get('temps_passe', '-') or '-')
        line_cols[5].write(f"{row.get('prix', 0)} €")
        # Statut + case à cocher
        statut_color = 'green' if statut == 'Livré' else ('red' if statut == 'En retard' else 'orange')
        statut_label = f"<span style='color:{statut_color}'>{statut}</span>"
        if statut == "À l'heure" and jours != "-":
            statut_label += f" <span style='color:gray;font-size:0.9em'>({jours})</span>"
        line_cols[6].markdown(statut_label, unsafe_allow_html=True)
        # Checkbox pour marquer livré
        checked = is_livre
        if line_cols[6].checkbox("", value=checked, key=f"livre_{row['commande_id']}"):
            if not is_livre:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("UPDATE commandes SET statut=? WHERE commande_id=?", ("livré", row['commande_id']))
                    conn.commit()
                st.rerun()
        else:
            if is_livre:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("UPDATE commandes SET statut=? WHERE commande_id=?", (None, row['commande_id']))
                    conn.commit()
                st.rerun()
        # Prix horaire (placeholder)
        line_cols[7].write("- €/h")
        # Action (Ajouter tâche)
        line_cols[8].button("Ajouter tâche", key=f"tache_{row['commande_id']}") 