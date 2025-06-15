import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "crm_data.db"

st.title("Modèles de checklist")

# --- Liste des modèles ---
with sqlite3.connect(DB_PATH) as conn:
    templates = pd.read_sql_query("SELECT * FROM checklist_templates", conn)

if st.button("Créer un modèle de checklist"):
    st.session_state['show_new_template'] = True
if st.session_state.get('show_new_template'):
    with st.form("form_new_template"):
        nom = st.text_input("Nom du modèle")
        description = st.text_area("Description")
        submitted = st.form_submit_button("Créer")
        if submitted and nom:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO checklist_templates (nom, description) VALUES (?, ?)", (nom, description))
                conn.commit()
            st.success("Modèle créé !")
            st.session_state['show_new_template'] = False
            st.rerun()
        if st.form_submit_button("Annuler"):
            st.session_state['show_new_template'] = False
            st.rerun()

if not templates.empty:
    for _, tpl in templates.iterrows():
        st.subheader(f"Modèle : {tpl['nom']}")
        st.write(tpl['description'])
        with sqlite3.connect(DB_PATH) as conn:
            items = pd.read_sql_query("SELECT * FROM checklist_template_items WHERE template_id=? ORDER BY ordre", conn, params=(tpl['id'],))
        for idx, item in items.iterrows():
            st.markdown(f"{idx+1}. {item['texte']}")
        if st.button(f"Ajouter un item", key=f"add_item_tpl_{tpl['id']}"):
            st.session_state[f"show_add_item_tpl_{tpl['id']}"] = True
        if st.session_state.get(f"show_add_item_tpl_{tpl['id']}"):
            with st.form(f"form_add_item_tpl_{tpl['id']}"):
                texte = st.text_input("Texte de l'item")
                ordre = st.number_input("Ordre", min_value=1, value=len(items)+1)
                if st.form_submit_button("Ajouter") and texte:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute("INSERT INTO checklist_template_items (template_id, texte, ordre) VALUES (?, ?, ?)", (tpl['id'], texte, ordre))
                        conn.commit()
                    st.success("Item ajouté !")
                    st.session_state[f"show_add_item_tpl_{tpl['id']}"] = False
                    st.rerun()
                if st.form_submit_button("Annuler"):
                    st.session_state[f"show_add_item_tpl_{tpl['id']}"] = False
                    st.rerun()
        if st.button(f"Supprimer ce modèle", key=f"del_tpl_{tpl['id']}"):
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM checklist_template_items WHERE template_id=?", (tpl['id'],))
                c.execute("DELETE FROM checklist_templates WHERE id=?", (tpl['id'],))
                conn.commit()
            st.success("Modèle supprimé !")
            st.rerun() 