import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Configuration de la page
st.set_page_config(page_title="Planning", layout="wide")

# Constantes
DB_PATH = "crm_data.db"
TYPES_TACHE = ["tache", "r1", "maintenance", "upsell", "à rappeller"]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table des tâches
    c.execute('''CREATE TABLE IF NOT EXISTS taches (
        tache_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        commande_id INTEGER,
        type_tache TEXT,
        titre TEXT,
        description TEXT,
        date_debut DATETIME,
        date_fin DATETIME,
        statut TEXT DEFAULT 'à faire',
        est_process BOOLEAN DEFAULT 0,
        service TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id),
        FOREIGN KEY(commande_id) REFERENCES commandes(commande_id)
    )''')
    
    conn.commit()
    conn.close()

def get_client_name(client_id):
    if not client_id:
        return "Process"
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT name FROM clients WHERE client_id = ?", conn, params=(client_id,))
        return df.iloc[0]['name'] if not df.empty else "Client inconnu"

def get_commande_service(commande_id):
    if not commande_id:
        return ""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT nom_service FROM commandes WHERE commande_id = ?", conn, params=(commande_id,))
        return df.iloc[0]['nom_service'] if not df.empty else ""

def format_duration(start, end):
    if not start or not end:
        return "0h"
    duration = pd.to_datetime(end) - pd.to_datetime(start)
    hours = duration.total_seconds() / 3600
    return f"{hours:.1f}h"

# Initialisation de la base de données
init_db()

# Titre de la page
st.title("Planning")

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["À faire", "Calendrier", "Planning hebdomadaire"])

with tab1:
    # Section À faire
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Deadlines proches")
        with sqlite3.connect(DB_PATH) as conn:
            # Commandes à échéance dans les 5 jours ou en retard
            today = datetime.now().date()
            five_days = today + timedelta(days=5)
            df_deadlines = pd.read_sql_query("""
                SELECT c.commande_id, cl.name as client, c.nom_service, c.date_fin, c.statut
                FROM commandes c
                JOIN clients cl ON c.client_id = cl.client_id
                WHERE c.date_fin <= ? AND c.statut != 'validé'
                ORDER BY c.date_fin ASC
            """, conn, params=(five_days.strftime("%Y-%m-%d"),))
            
            if not df_deadlines.empty:
                for _, row in df_deadlines.iterrows():
                    date_fin = pd.to_datetime(row['date_fin']).date()
                    jours_restants = (date_fin - today).days
                    status = "🔴 En retard" if jours_restants < 0 else "🟡 Bientôt"
                    st.warning(f"{status} : {row['client']} - {row['nom_service']} ({jours_restants} jours)")
            else:
                st.info("Aucune deadline proche")
    
    with col2:
        st.subheader("Rendez-vous du jour")
        with sqlite3.connect(DB_PATH) as conn:
            # Tâches du jour par type
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            df_rdv = pd.read_sql_query("""
                SELECT type_tache, COUNT(*) as count
                FROM taches
                WHERE date_debut >= ? AND date_debut < ?
                AND type_tache IN ('r1', 'à rappeller', 'upsell', 'maintenance')
                GROUP BY type_tache
            """, conn, params=(today_start, today_end))
            
            if not df_rdv.empty:
                for _, row in df_rdv.iterrows():
                    st.info(f"{row['type_tache']}: {row['count']}")
            else:
                st.info("Aucun rendez-vous aujourd'hui")

    # Compteurs
    st.write("---")
    st.subheader("Compteurs du jour")
    col1, col2, col3, col4 = st.columns(4)
    
    with sqlite3.connect(DB_PATH) as conn:
        # Tâches effectuées
        df_taches = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM taches
            WHERE date_debut >= ? AND date_debut < ?
            AND statut = 'terminé'
        """, conn, params=(today_start, today_end))
        
        # Heures travaillées
        df_heures = pd.read_sql_query("""
            SELECT SUM((julianday(date_fin) - julianday(date_debut)) * 24) as hours
            FROM taches
            WHERE date_debut >= ? AND date_debut < ?
            AND statut = 'terminé'
        """, conn, params=(today_start, today_end))
        
        # R1 effectués
        df_r1 = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM taches
            WHERE date_debut >= ? AND date_debut < ?
            AND type_tache = 'r1'
            AND statut = 'terminé'
        """, conn, params=(today_start, today_end))
        
        # Missions terminées
        df_missions = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM commandes
            WHERE date_fin >= ? AND date_fin < ?
            AND statut = 'validé'
        """, conn, params=(today_start, today_end))
    
    with col1:
        st.metric("Tâches effectuées", df_taches.iloc[0]['count'])
    with col2:
        st.metric("Heures travaillées", f"{df_heures.iloc[0]['hours']:.1f}h")
    with col3:
        st.metric("R1 effectués", df_r1.iloc[0]['count'])
    with col4:
        st.metric("Missions terminées", df_missions.iloc[0]['count'])

with tab2:
    st.subheader("Calendrier mensuel")
    # TODO: Implémenter le calendrier mensuel

with tab3:
    st.subheader("Planning hebdomadaire")
    # TODO: Implémenter le planning hebdomadaire

# Bouton d'ajout de tâche
st.sidebar.title("Ajouter une tâche")
# TODO: Implémenter le formulaire d'ajout de tâche 