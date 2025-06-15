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
                    INSERT INTO commandes (client_id, nom_service, prix, recurrence, date_debut, date_fin, argent_encaisse, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    nom_service,
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

# --- Calcul du coût à l'heure pour chaque commande ---
def get_cout_heure_commande(commande_id):
    with sqlite3.connect(DB_PATH) as conn:
        prix = pd.read_sql_query("SELECT prix FROM commandes WHERE commande_id = ?", conn, params=(commande_id,)).iloc[0]['prix'] or 0
        taches = pd.read_sql_query("SELECT date_debut, date_fin, temps_passe FROM taches WHERE commande_id = ?", conn, params=(commande_id,))
        total_heures = 0
        for _, row in taches.iterrows():
            if row.get('temps_passe') and not pd.isnull(row['temps_passe']):
                try:
                    total_heures += float(row['temps_passe'])
                except:
                    pass
            elif pd.notnull(row.get('date_debut')) and pd.notnull(row.get('date_fin')):
                try:
                    debut = pd.to_datetime(row['date_debut'])
                    fin = pd.to_datetime(row['date_fin'])
                    total_heures += (fin - debut).total_seconds() / 3600
                except:
                    pass
        if total_heures > 0:
            return round(prix / total_heures, 2)
        else:
            return None

# --- Affichage du tableau ---
if df.empty:
    st.info("Aucune commande trouvée.")
else:
    st.write("")
    headers = ["Client", "Nom du service", "Date début", "Date fin", "Prix", "Statut", "Action", "Coût à l'heure"]
    col_widths = [2,2,1.5,1.5,1,1.5,1.5,1.5]
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
        line_cols[2].write(row['date_debut'])
        line_cols[3].write(row['date_fin'])
        line_cols[4].write(f"{row.get('prix', 0)} €")
        statut_color = 'green' if statut == 'Livré' else ('red' if statut == 'En retard' else 'orange')
        statut_label = f"<span style='color:{statut_color}'>{statut}</span>"
        if statut == "À l'heure" and jours != "-":
            statut_label += f" <span style='color:gray;font-size:0.9em'>({jours})</span>"
        line_cols[5].markdown(statut_label, unsafe_allow_html=True)
        checked = is_livre
        if line_cols[5].checkbox("", value=checked, key=f"livre_{row['commande_id']}"):
            if not is_livre:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("UPDATE commandes SET statut=? WHERE commande_id=?", ("livré", row['commande_id']))
                    conn.commit()
                st.rerun()
        # Actions
        if line_cols[6].button("Modifier", key=f"edit_{row['commande_id']}"):
            st.session_state['edit_commande_id'] = row['commande_id']
            st.rerun()
        if line_cols[6].button("Supprimer", key=f"delete_{row['commande_id']}"):
            st.session_state['delete_commande_id'] = row['commande_id']
            st.rerun()
        if line_cols[6].button("Ajouter tâche", key=f"add_task_{row['commande_id']}"):
            st.session_state['show_add_task_form'] = row['commande_id']
            st.session_state['add_task_client_id'] = row['client_id']
            st.session_state['add_task_commande_nom'] = row['nom_service']
            st.session_state['add_task_client_nom'] = row['name']
            st.rerun()
        cout_heure = get_cout_heure_commande(row['commande_id'])
        line_cols[7].write(f"{cout_heure} €/h" if cout_heure else "-")
        # Affichage du formulaire juste sous la ligne concernée
        if st.session_state.get('show_add_task_form') == row['commande_id']:
            import planning
            with st.form(f"add_task_from_commande_{row['commande_id']}"):
                st.subheader("Ajouter une tâche au planning")
                st.markdown(f"**Client :** {row['name']}")
                st.markdown(f"**Commande :** {row['nom_service']}")
                type_tache = st.selectbox("Type de tâche", planning.TYPES_TACHE, key=f"type_tache_{row['commande_id']}")
                titre = st.text_input("Titre", key=f"titre_{row['commande_id']}")
                description = st.text_area("Description", value=f"{row['nom_service']} - {row['name']}", key=f"desc_{row['commande_id']}")
                date = st.date_input("Date", value=datetime.now(), key=f"date_{row['commande_id']}")
                heure = st.time_input("Heure de début", key=f"heure_{row['commande_id']}")
                heure_fin = st.time_input("Heure de fin", key=f"heure_fin_{row['commande_id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Ajouter"):
                        if not titre:
                            st.error("Le titre est obligatoire")
                        elif heure_fin <= heure:
                            st.error("L'heure de fin doit être après l'heure de début")
                        else:
                            with sqlite3.connect(DB_PATH) as conn:
                                c = conn.cursor()
                                date_debut = datetime.combine(date, heure)
                                date_fin = datetime.combine(date, heure_fin)
                                duree = (date_fin - date_debut).total_seconds() / 3600
                                c.execute("""
                                    INSERT INTO taches (client_id, commande_id, type_tache, titre, description, date_debut, date_fin, temps_passe, est_process)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                                """, (row['client_id'], row['commande_id'], type_tache, titre, description, date_debut, date_fin, duree))
                                conn.commit()
                            st.success("Tâche ajoutée au planning !")
                            st.session_state['show_add_task_form'] = None
                            st.rerun()
                with col2:
                    if st.form_submit_button("Annuler"):
                        st.session_state['show_add_task_form'] = None
                        st.rerun()