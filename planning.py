import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import calendar
import locale

# Configuration locale pour les noms en français
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR')
    except:
        pass

# Constantes
DB_PATH = "crm_data.db"
TYPES_TACHE = ["tache", "r1", "maintenance", "upsell", "à rappeller"]
JOURS_SEMAINE = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
HEURES_TRAVAIL = [f"{h:02d}:00" for h in range(8, 20)]  # De 8h à 19h

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

def get_month_calendar(year, month):
    cal = calendar.monthcalendar(year, month)
    return cal

def get_tasks_for_period(start_date, end_date):
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT t.*, c.name as client_name, co.nom_service
        FROM taches t
        LEFT JOIN clients c ON t.client_id = c.client_id
        LEFT JOIN commandes co ON t.commande_id = co.commande_id
        WHERE date(t.date_debut) >= date(?) AND date(t.date_debut) <= date(?)
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    return df

def get_task_hours(task):
    start = pd.to_datetime(task['date_debut'])
    end = pd.to_datetime(task['date_fin'])
    
    # Liste des heures pendant lesquelles la tâche est active
    hours = []
    current = start.replace(minute=0, second=0, microsecond=0)
    end_hour = end.replace(minute=0, second=0, microsecond=0)
    
    while current <= end_hour:
        if 8 <= current.hour <= 19:  # Heures de travail
            hours.append(current.strftime('%H:00'))
        current += timedelta(hours=1)
    
    return hours

def get_task_days(task):
    start = pd.to_datetime(task['date_debut']).date()
    end = pd.to_datetime(task['date_fin']).date()
    
    # Liste des jours pendant lesquels la tâche est active
    days = []
    current = start
    
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    
    return days

# Initialisation de la base de données
init_db()

# Titre de la page
st.title("Planning")

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["À faire", "Calendrier", "Planning hebdomadaire"])

with tab1:
    # Section À faire aujourd'hui
    st.subheader("À faire aujourd'hui")
    today = datetime.now().date()
    today_tasks = get_tasks_for_period(today, today)
    if not today_tasks.empty:
        for _, task in today_tasks.iterrows():
            st.info(f"{task['titre']} - {task['client_name'] if task['client_name'] else 'Process'}")
    else:
        st.info("Aucune tâche pour aujourd'hui")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Deadlines proches")
        with sqlite3.connect(DB_PATH) as conn:
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
        heures = df_heures.iloc[0]['hours']
        st.metric("Heures travaillées", f"{heures if heures else 0:.1f}h")
    with col3:
        st.metric("R1 effectués", df_r1.iloc[0]['count'])
    with col4:
        st.metric("Missions terminées", df_missions.iloc[0]['count'])

with tab2:
    st.subheader("Calendrier mensuel")
    
    # Navigation du mois
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Mois précédent"):
            if current_month == 1:
                current_month = 12
                current_year -= 1
            else:
                current_month -= 1
    with col2:
        st.write(f"{calendar.month_name[current_month]} {current_year}")
    with col3:
        if st.button("Mois suivant"):
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Rechercher...", placeholder="Client, titre ou type")
    with col2:
        type_filter = st.selectbox("Type", ["Tous"] + TYPES_TACHE)

    # Affichage du calendrier
    cal = get_month_calendar(current_year, current_month)
    
    # En-têtes des jours
    cols = st.columns(7)
    for i, jour in enumerate(JOURS_SEMAINE):
        with cols[i]:
            st.markdown(f"**{jour}**")
    
    # Dates et tâches
    first_day = datetime(current_year, current_month, 1)
    last_day = datetime(current_year, current_month + 1, 1) - timedelta(days=1)
    tasks = get_tasks_for_period(first_day, last_day)
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day != 0:
                    st.write(f"**{day}**")
                    day_tasks = tasks[pd.to_datetime(tasks['date_debut']).dt.day == day]
                    if not day_tasks.empty:
                        for _, task in day_tasks.iterrows():
                            if (not search or 
                                search.lower() in str(task['client_name']).lower() or 
                                search.lower() in str(task['titre']).lower() or 
                                search.lower() in str(task['type_tache']).lower()):
                                if type_filter == "Tous" or type_filter == task['type_tache']:
                                    st.info(f"{task['titre']}")

with tab3:
    st.subheader("Planning hebdomadaire")
    
    # Navigation de la semaine
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Semaine précédente"):
            start_of_week -= timedelta(days=7)
    with col2:
        st.write(f"Semaine du {start_of_week.strftime('%d/%m/%Y')} au {(start_of_week + timedelta(days=6)).strftime('%d/%m/%Y')}")
    with col3:
        if st.button("Semaine suivante"):
            start_of_week += timedelta(days=7)

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        search_week = st.text_input("Rechercher...", placeholder="Client, titre ou type", key="search_week")
    with col2:
        type_filter_week = st.selectbox("Type", ["Tous"] + TYPES_TACHE, key="type_week")

    # Récupération des tâches de la semaine
    week_end = start_of_week + timedelta(days=7)
    week_tasks = get_tasks_for_period(start_of_week, week_end)
    
    # En-têtes des jours
    cols = st.columns(7)
    for i, day_offset in enumerate(range(7)):
        current_day = start_of_week + timedelta(days=day_offset)
        with cols[i]:
            st.write(f"**{current_day.strftime('%A %d/%m')}**")
    
    # Affichage du planning
    for hour in HEURES_TRAVAIL:
        st.write(f"**{hour}**")
        cols = st.columns(7)
        
        # Pour chaque jour de la semaine
        for i, day_offset in enumerate(range(7)):
            current_day = start_of_week + timedelta(days=day_offset)
            with cols[i]:
                # Filtrer les tâches pour ce jour et cette heure
                day_tasks = []
                for _, task in week_tasks.iterrows():
                    task_days = get_task_days(task)
                    task_hours = get_task_hours(task)
                    
                    if current_day in task_days and hour in task_hours:
                        if (not search_week or 
                            search_week.lower() in str(task['client_name']).lower() or 
                            search_week.lower() in str(task['titre']).lower() or 
                            search_week.lower() in str(task['type_tache']).lower()):
                            if type_filter_week == "Tous" or type_filter_week == task['type_tache']:
                                day_tasks.append(task)
                
                # Afficher les tâches
                for task in day_tasks:
                    start_time = pd.to_datetime(task['date_debut']).strftime('%H:%M')
                    end_time = pd.to_datetime(task['date_fin']).strftime('%H:%M')
                    st.info(f"{start_time}-{end_time}\n{task['titre']}\n{task['client_name'] if task['client_name'] else 'Process'}")

# Bouton d'ajout de tâche (flottant)
st.sidebar.title("Ajouter une tâche")
with st.sidebar:
    with st.form("new_task"):
        # Choix client/process
        est_process = st.checkbox("Process (sans client)")
        if not est_process:
            # Liste des clients
            with sqlite3.connect(DB_PATH) as conn:
                df_clients = pd.read_sql_query("SELECT client_id, name FROM clients", conn)
            client_id = st.selectbox("Client", df_clients['name'].tolist())
            client_id = df_clients[df_clients['name'] == client_id]['client_id'].iloc[0] if client_id else None
            
            # Liste des commandes du client
            if client_id:
                with sqlite3.connect(DB_PATH) as conn:
                    df_commandes = pd.read_sql_query(
                        "SELECT commande_id, nom_service FROM commandes WHERE client_id = ?",
                        conn, params=(client_id,)
                    )
                commande_id = st.selectbox("Commande", df_commandes['nom_service'].tolist())
                commande_id = df_commandes[df_commandes['nom_service'] == commande_id]['commande_id'].iloc[0] if commande_id else None
        else:
            client_id = None
            commande_id = None
        
        type_tache = st.selectbox("Type de tâche", TYPES_TACHE)
        titre = st.text_input("Titre")
        description = st.text_area("Description")
        date_debut = st.date_input("Date de début")
        heure_debut = st.time_input("Heure de début")
        date_fin = st.date_input("Date de fin")
        heure_fin = st.time_input("Heure de fin")
        
        if st.form_submit_button("Ajouter"):
            if not titre:
                st.error("Le titre est obligatoire")
            else:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    date_debut_complete = datetime.combine(date_debut, heure_debut)
                    date_fin_complete = datetime.combine(date_fin, heure_fin)
                    c.execute("""
                        INSERT INTO taches (client_id, commande_id, type_tache, titre, description, 
                                         date_debut, date_fin, est_process)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (client_id, commande_id, type_tache, titre, description, 
                          date_debut_complete, date_fin_complete, est_process))
                    conn.commit()
                st.success("Tâche ajoutée avec succès !")
                st.rerun() 