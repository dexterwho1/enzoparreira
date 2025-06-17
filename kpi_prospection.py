import streamlit as st
import traceback
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "crm_data.db"

st.title("KPI Prospection")

try:
    # --- Récupération des données ---
    with sqlite3.connect(DB_PATH) as conn:
        histo = pd.read_sql_query("SELECT * FROM historique_statuts", conn)
        prospects = pd.read_sql_query("SELECT * FROM prospects", conn)
        clients = pd.read_sql_query("SELECT * FROM clients", conn)
        taches = pd.read_sql_query("SELECT * FROM taches", conn)

    # --- Préparation des données ---
    # Dernier statut par prospect (y compris ceux devenus clients)
    if not histo.empty and 'date_changement' in histo.columns:
        # Conversion robuste en datetime
        histo['date_changement'] = pd.to_datetime(histo['date_changement'], errors='coerce')
        # Supprime les lignes avec date_changement invalide
        histo = histo.dropna(subset=['date_changement'])
        if not histo.empty:
            last_statut = histo.sort_values('date_changement').groupby('place_id').tail(1)
        else:
            last_statut = pd.DataFrame(columns=['place_id','statut','date_changement'])
    else:
        last_statut = pd.DataFrame(columns=['place_id','statut','date_changement'])

    # Pour les périodes
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    start_week = today - timedelta(days=today.weekday())
    start_last_week = start_week - timedelta(days=7)
    end_last_week = start_week - timedelta(days=1)
    start_month = today.replace(day=1)
    periods = {
        "Aujourd'hui": (today, today),
        "Hier": (yesterday, yesterday),
        "Cette semaine": (start_week, today),
        "Semaine dernière": (start_last_week, end_last_week),
        "Ce mois": (start_month, today)
    }

    # --- Appels passés ---
    # Tous les place_id ayant au moins un changement de statut (historique) ou présents dans clients
    place_ids_appel = set(histo['place_id'].unique()) | set(clients['place_id'].dropna().unique())
    # Pour les périodes, on regarde la date du dernier changement de statut
    last_statut_period = last_statut.copy()
    if not last_statut_period.empty and 'date_changement' in last_statut_period.columns:
        last_statut_period['date'] = last_statut_period['date_changement'].dt.date
    else:
        last_statut_period['date'] = pd.Series(dtype='object')

    def count_appels_periode(start, end):
        if last_statut_period.empty:
            return 0
        mask = (last_statut_period['date'] >= start) & (last_statut_period['date'] <= end)
        return last_statut_period[mask]['place_id'].nunique() + clients[~clients['place_id'].isin(last_statut_period[mask]['place_id'])]['place_id'].nunique()

    kpi_data = {p: count_appels_periode(*d) for p, d in periods.items()}

    # --- Clients estimés ---
    def count_clients_periode(start, end):
        # On prend la date_conversion du client
        if 'date_conversion' in clients.columns and not clients.empty:
            clients_copy = clients.copy()
            clients_copy['date_conversion_dt'] = pd.to_datetime(clients_copy['date_conversion'], errors='coerce')
            clients_copy = clients_copy.dropna(subset=['date_conversion_dt'])
            if not clients_copy.empty:
                mask = (clients_copy['date_conversion_dt'].dt.date >= start) & (clients_copy['date_conversion_dt'].dt.date <= end)
                return clients_copy[mask]['client_id'].nunique()
        return 0
    clients_data = {p: count_clients_periode(*d) for p, d in periods.items()}

    # --- Ratio appels/clients ---
    def safe_ratio(a, b):
        return f"{a/b:.1f}" if b else "∞"

    # --- NOUVEAU : Ratio Appel/R1 (et à rappeller) ---
    # On exclut les statuts "n'a pas répondu" pour le dénominateur
    if not taches.empty:
        # On considère comme "appel" toute tâche dont type_tache est 'tache', 'r1', 'à rappeller', 'pas intérréssé'
        appels_total = taches[~taches['type_tache'].isin([None, "", "n'a pas répondu"])]
        # Exclure explicitement "n'a pas répondu" si jamais il existe dans type_tache
        appels_total = appels_total[appels_total['type_tache'] != "n'a pas répondu"]
        nb_appels = appels_total.shape[0]
        nb_r1 = appels_total[appels_total['type_tache'] == 'r1'].shape[0]
        nb_a_rappeller = appels_total[appels_total['type_tache'] == 'à rappeller'].shape[0]
        nb_refus = appels_total[appels_total['type_tache'] == 'pas intérréssé'].shape[0]
        ratio_r1 = (nb_r1 + nb_a_rappeller) / nb_appels if nb_appels else 0
    else:
        nb_appels = nb_r1 = nb_a_rappeller = nb_refus = 0
        ratio_r1 = 0

    st.subheader("Indicateurs d'appels (tâches)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Appels total", nb_appels)
    col2.metric("R1", nb_r1)
    col3.metric("À rappeller", nb_a_rappeller)
    col4.metric("Refus", nb_refus)
    st.metric("Ratio (R1 + À rappeller) / Appels", f"{ratio_r1:.2%}")

    # --- Comparaison R1 vs À rappeller ---
    st.subheader("Comparaison R1 / À rappeller")
    comp_df = pd.DataFrame({
        'Type': ['R1', 'À rappeller'],
        'Nombre': [nb_r1, nb_a_rappeller]
    })
    st.bar_chart(comp_df.set_index('Type'))

    # --- Section KPI ---
    st.subheader("KPI Prospection")
    st.write(pd.DataFrame([kpi_data], index=["Appels passés"]))
    st.write(pd.DataFrame([clients_data], index=["Clients (transformés)"]))
    ratio = safe_ratio(sum(kpi_data.values()), sum(clients_data.values()))
    st.metric("Ratio Appels/Clients", ratio)

    # --- Comparatif R1 / À rappeller par période ---
    st.subheader("Comparatif R1 / À rappeller par période")
    def count_type_periode(type_tache, start, end):
        if taches.empty:
            return 0
        taches['date_debut_dt'] = pd.to_datetime(taches['date_debut'], errors='coerce')
        mask = (
            (taches['type_tache'] == type_tache)
            & (taches['date_debut_dt'].dt.date >= start)
            & (taches['date_debut_dt'].dt.date <= end)
        )
        return taches[mask].shape[0]
    comp_period = {
        p: {
            'R1': count_type_periode('r1', *d),
            'À rappeller': count_type_periode('à rappeller', *d)
        }
        for p, d in periods.items()
    }
    comp_df = pd.DataFrame(comp_period).T
    st.table(comp_df)

    # --- Affichage des clients signés (même hors prospects) ---
    st.subheader("Clients signés (tous)")
    if not clients.empty:
        st.dataframe(clients[['name','phone','address','date_conversion']])
    else:
        st.info("Aucun client signé.")

    # --- Funnel de vente ---
    st.subheader("Funnel de vente (statut d'appel)")
    if not last_statut.empty:
        total = last_statut['place_id'].nunique()
        funnel = last_statut['statut'].value_counts().reset_index()
        funnel.columns = ['Statut', 'Nombre']
        funnel['%'] = funnel['Nombre'] / total * 100
        st.dataframe(funnel)
    else:
        st.info("Aucun prospect avec statut d'appel.")

    # --- Pipeline 4 semaines (appels) ---
    st.subheader("Pipeline 4 semaines (appels)")
    four_weeks_ago = today - timedelta(days=28)
    if not last_statut.empty and 'date' in last_statut_period.columns:
        pipeline = last_statut_period[last_statut_period['date'] >= four_weeks_ago]
        if not pipeline.empty:
            pipeline_stats = pipeline.groupby(pipeline['date'].apply(lambda d: d.isocalendar()[1])).size()
            st.bar_chart(pipeline_stats)
        else:
            st.info("Aucun appel sur les 4 dernières semaines.")
    else:
        st.info("Aucun appel sur les 4 dernières semaines.")

except Exception as e:
    st.error(f"Erreur dans KPI Prospection : {e}")
    st.text(traceback.format_exc()) 