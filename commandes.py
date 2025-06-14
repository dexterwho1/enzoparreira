import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import re

DB_PATH = "crm_data.db"

st.title("Gestion des commandes")

# --- Ajout manuel de commande ---
st.header("Ajouter une commande manuellement")
with st.form("ajout_commande_form"):
    # Récupération des clients et prospects
    with sqlite3.connect(DB_PATH) as conn:
        clients = pd.read_sql_query("SELECT * FROM clients", conn)
        prospects = pd.read_sql_query("SELECT * FROM prospects", conn)
    
    # Combinaison clients + prospects pour le sélecteur
    all_contacts = []
    for _, client in clients.iterrows():
        all_contacts.append(f"CLIENT: {client['name']} (ID: {client['client_id']})")
    for _, prospect in prospects.iterrows():
        all_contacts.append(f"PROSPECT: {prospect['name']} (ID: {prospect['place_id']})")
    
    contact_choisi = st.selectbox("Client/Prospect *", ["Sélectionner..."] + all_contacts)
    nom_service = st.text_input("Nom du service *", "")
    prestation = st.text_input("Description de la prestation", "")
    prix = st.number_input("Prix (€) *", min_value=0.0, step=10.0)
    date_debut = st.date_input("Date de début *", value=datetime.now())
    date_fin = st.date_input("Date de fin *", value=datetime.now())
    recurrence = st.selectbox("Récurrence", ["Non", "2 semaines", "1 mois", "3 mois", "6 mois", "1 an"])
    argent_encaisse = st.number_input("Argent encaissé (€)", min_value=0.0, step=10.0, value=0.0)
    
    submitted = st.form_submit_button("Ajouter la commande")
    if submitted:
        if not (contact_choisi != "Sélectionner..." and nom_service and prix):
            st.error("Merci de remplir tous les champs obligatoires.")
        else:
            # Extraction de l'ID du contact choisi
            if contact_choisi.startswith("CLIENT:"):
                client_id = int(contact_choisi.split("(ID: ")[1].split(")")[0])
                place_id = None
            else:  # PROSPECT
                place_id = contact_choisi.split("(ID: ")[1].split(")")[0]
                # Créer un client à partir du prospect
                prospect = prospects[prospects['place_id'] == place_id].iloc[0]
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO clients (place_id, name, phone, address, date_conversion, last_contact)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        place_id,
                        prospect['name'],
                        prospect['phone'],
                        prospect['address'],
                        date_debut.strftime("%Y-%m-%d"),
                        date_debut.strftime("%Y-%m-%d")
                    ))
                    client_id = c.lastrowid
                    conn.commit()
            
            # Insertion de la commande
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO commandes (client_id, nom_service, prestation, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    nom_service,
                    prestation,
                    prix,
                    recurrence if recurrence != "Non" else None,
                    date_debut.strftime("%Y-%m-%d"),
                    date_fin.strftime("%Y-%m-%d"),
                    argent_encaisse,
                    None  # statut initial
                ))
                conn.commit()
            st.success("Commande ajoutée avec succès !")
            st.rerun()

# --- Liste des commandes ---
st.header("Liste des commandes")

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
    filtre_service = st.selectbox("Service", ["Tous"] + sorted(commandes['nom_service'].dropna().unique().tolist()))
with col4:
    filtre_statut = st.selectbox("Statut", ["Tous", "En retard", "À l'heure", "Livré"])

# --- Application des filtres ---
df = commandes.copy()
if filtre_txt:
    mask = (df['nom_service'].str.contains(filtre_txt, case=False, na=False) | 
            df['prestation'].str.contains(filtre_txt, case=False, na=False) | 
            df['name'].str.contains(filtre_txt, case=False, na=False))
    df = df[mask]
if filtre_client != "Tous":
    df = df[df['name'] == filtre_client]
if filtre_service != "Tous":
    df = df[df['nom_service'] == filtre_service]

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
    headers = ["Client", "Nom du service", "Description", "Date début", "Date fin", "Prix", "Statut", "Action"]
    col_widths = [2,2,2,1.5,1.5,1,1.5,1.5]
    header_cols = st.columns(col_widths)
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")
    
    for idx, row in df.iterrows():
        statut = get_statut(row)
        jours = get_jours_restant(row)
        is_livre = row.get('statut') == 'livré'
        line_cols = st.columns(col_widths)
        
        line_cols[0].write(row['name'])
        line_cols[1].write(row.get('nom_service', '-') or '-')
        line_cols[2].write(row.get('prestation', '-') or '-')
        line_cols[3].write(row['date_debut'])
        line_cols[4].write(row['date_fin'])
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
        
        # Action (Modifier/Supprimer)
        col_action = line_cols[7]
        if col_action.button("Modifier", key=f"mod_{row['commande_id']}"):
            st.session_state['edit_commande'] = row['commande_id']
        if col_action.button("Supprimer", key=f"del_{row['commande_id']}"):
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM commandes WHERE commande_id=?", (row['commande_id'],))
                conn.commit()
            st.success("Commande supprimée !")
            st.rerun()

        # Gestion des erreurs
        tel = row.get('tel', '')
        tel_clean = re.sub(r"[^\d+]", "", tel)  # retire tout sauf chiffres et +
        # Gère les formats +33 7..., 07..., 06...
        if tel_clean.startswith("+33"):
            tel_clean = "0" + tel_clean[3:]
        if not (tel_clean.startswith("06") or tel_clean.startswith("07")):
            st.error(f"Ligne {idx+2} ignorée : numéro non mobile FR (06, 07, +336, +337).")
            continue 