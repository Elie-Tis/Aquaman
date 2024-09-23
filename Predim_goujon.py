import streamlit as st
import Calc_goujon as cg

lien_image_profile = "Image3.png"
lien_image_L_t = "ImageL_t.png"
lien_image_delta = "Imagedelta.png"
lien_image_Vrds = "Image_vrds.png"
lien_image_sem = "Image_semelle.png"

st.set_page_config(layout="wide", initial_sidebar_state ="expanded", page_title= "Predim Aquaman", page_icon="🐟")
st.title("Outil de prédimensionnement (V.Git_V2)")

with st.sidebar:
    st.image(lien_image_profile, caption="Géométrie du profilé", use_column_width=True, )
    st.header("Objectifs")
    gaine = st.selectbox("Type de gaine", ['Uniaxiale', "Biaxiale"])
    V_cible_elu = st.number_input("V cible à l'ELU (kN)", value=35.5)
    d_max_axe = st.number_input("Déformation maximale dans le joint à l'ELS (mm)", value=1., format="%.1f")
    d_max_rot = st.number_input("Déformation maximale des semelles à l'ELS (mm)",
                                value=0.5) if gaine == 'Biaxiale' else 0

    param = st.expander("Paramètres")
    with param:
        beta = st.number_input("Coefficient de répartition des contraintes : beta", value=0.85, format="%.2f")
        delta_lat = st.number_input("Débattement latéral dans une direction (mm) : delta_lat",
                                    value=10) if gaine == 'Biaxiale' else 0
        l_joint = st.number_input("Largeur du joint (mm) : t", value=35)

        gamma_s = st.number_input("Coeffcicient acier", value=1.1)
        E = st.number_input("Module d'élasticité (MPa)", value=210_000)
        rho = st.number_input("Masse volumique (kg/m3)", value=7800)
        X0 = cg.X0[gaine]

col_titre_joint, col_titre_sem = st.columns([1,1])
col_titre_joint.subheader("Dans le joint")
col_geo_joint, col_res_joint, col_geo_sem, col_res_semelle = st.columns([0.6,1,0.6,1])


with col_geo_joint:
    st.markdown("**Semelle supérieure**", )
    col1, col2, col3 = st.columns(3)
    b_sup = col1.number_input("b (mm)", value=50., key="b_sup")
    h_sup = col2.number_input("h (mm)", value=3., key="h_sup")
    fy_sup = col3.number_input("fy (MPa)", value=280, key="fy_sup")
    st.markdown("**Ame**", )
    col1, col2, col3 = st.columns(3)
    b_a = col1.number_input("b (mm)", value=3., key="b_a")
    h_a = col2.number_input("h (mm)", value=64., key="h_a")
    fy_a = col3.number_input("fy (MPa)", value=280, key="fy_a")
    geo_ame = dict(b=b_a, h=h_a, f_y=fy_a)
    st.markdown("**Semelle inférieure**", )
    col1, col2, col3 = st.columns(3)
    b_inf = col1.number_input("b (mm)", value=50., key="b_inf", )
    h_inf = col2.number_input("h (mm)", value=3., key="h_inf")
    fy_inf = col3.number_input("fy (MPa)", value=280, key="fy_inf")
    geo_inf = dict(b=b_inf, h=h_inf, f_y=fy_inf)

    L_gaine = st.number_input("Profondeur de la semelle dans la gaine à \n\n t = tmax (mm) : L", value=90)
    geo_sup = dict(b=b_sup, h=h_sup, f_y=fy_sup, )

# Création de l'axe dans le joint
axe_joint = cg.create_axe(geo_inf, geo_ame, geo_sup, E, nb_rot=0)
# Calcul de l'axe dans le joint
verif_joint, df_caract_joint, V_max_joint = cg.verif_axe(axe_joint, t=l_joint, L=L_gaine, d_max=d_max_axe, X0=X0, gamma_s=gamma_s, V_elu=V_cible_elu, beta=beta, rho=rho )

with col_res_joint:
    st.markdown("**Ruine Acier (kN)**")
    df_ruine_acier = df_caract_joint.loc[:, ["V_Rds", "V_ELU", "verif_Vrds", "tau_V"]].round(2)
    df_ruine_acier['tau_V'] = df_ruine_acier['tau_V'].apply(lambda x: f'{x : .0%}')
    st.dataframe(df_ruine_acier, hide_index=True, use_container_width=True)

    st.markdown("**Déformation à l'ELS (mm)**")
    df_def_joint = df_caract_joint.loc[:, ["d", "d_max", "verif_def", "tau_d", "V_max_d"]].round(2)
    df_def_joint['tau_d'] = df_def_joint['tau_d'].apply(lambda x: f'{x : .0%}')
    st.dataframe(df_def_joint, hide_index=True, use_container_width=True)

    st.markdown("**Plastification à l'ELS (kN, kN.m)**")
    df_fat_joint = df_caract_joint.loc[:,
                   ["V_els", "V_pl", "M_els", "M_pl", "verif_def", "tau_fat", "V_max_fat"]].round(2)
    df_fat_joint['tau_fat'] = df_fat_joint['tau_fat'].apply(lambda x: f'{x : .0%}')
    st.dataframe(df_fat_joint, hide_index=True, use_container_width=True)

    if verif_joint:
        st.success(" Le profilé permet de reprendre les efforts cible au niveau du joint", icon="✅")
    else:
        st.error("Le profilé permet pas de reprendre les efforts cible au niveau du joint", icon="❌")

if gaine == "Biaxiale":
    col_titre_sem.subheader("Dans la gaine biaxiale")
    with col_geo_sem:
        st.markdown("**Semelle**", )
        col1, col2, col3 = st.columns(3)
        b_sem = col1.number_input("b (mm)", value=50., key="b_sem")
        h_sem = col2.number_input("h (mm)", value=3., key="h_sem")
        fy_sem = col3.number_input("fy (MPa)", value=280, key="fy_sem")
        nb_rot = st.number_input("Nombre de rotule plastique", value=1, key="nb_rot")

    # Création de l'axe dans la gaine biaxiale
    axe_sem = dict(b=b_sem, h=h_sem, f_y=fy_sem, nb_rot=nb_rot, E=E)
    # Calcul dans la semelle dans la gaine biaxiale
    verif_sem, df_caract_sem, V_max_sem = cg.verif_semelle(semelle=axe_sem, nb_rotule=nb_rot, L_gaine=L_gaine,
                                                           beta=beta, delta_lat=delta_lat, V_elu=V_cible_elu,
                                                           d_max=d_max_rot, X0=X0, gamma_s=gamma_s)

    with col_res_semelle:
        st.markdown("**Ruine Acier (kN.m, kN)**")
        df_ruine_rotule = df_caract_sem.loc[:, ["M_rot", "M_pl", "verif_Mpl", "tau_M", "V_max_rot"]].round(2)
        df_ruine_rotule['tau_M'] = df_ruine_rotule['tau_M'].apply(lambda x: f'{x : .0%}')
        st.dataframe(df_ruine_rotule, hide_index=True, use_container_width=True)

        st.markdown("**Déformation à l'ELS (mm)**")
        df_def_sem = df_caract_sem.loc[:, ["d", "d_max", "verif_d", "tau_d", "V_max_d"]].round(2)
        df_def_sem['tau_d'] = df_def_sem['tau_d'].apply(lambda x: f'{x : .0%}')
        st.dataframe(df_def_sem, hide_index=True, use_container_width=True)

        st.markdown("**Plastification à l'ELS (kN, kN.m)**")
        df_fat_rot = df_caract_sem.loc[:, ["M_els", "M_pl", "verif_fat", "tau_fat", "V_max_fat"]].round(2)
        df_fat_rot['tau_fat'] = df_fat_rot['tau_fat'].apply(lambda x: f'{x : .0%}')
        st.dataframe(df_fat_rot, hide_index=True, use_container_width=True)

        if verif_sem:
            st.success(" La semelle supérieure permet de reprendre les efforts cible", icon="✅")
        else:
            st.error("La semelle supérieure ne permet pas de reprendre les efforts cible", icon="❌")

V_max = min(V_max_joint, V_max_sem) if gaine == "Biaxiale" else V_max_joint
nb_gouj_m = V_cible_elu / V_max
dist_gouj = V_max / V_cible_elu
st.info(f"Effort ELU max admissible pour le goujon : **{round(V_max,2)} kN**, soit une distance entre goujons de **{round(dist_gouj, 2)} m**"
        f" ou **{nb_gouj_m} goujon(s)** par mètre")

col_im1, colim2, colim3, colim4 = st.columns([0.6, 1, 1, 0.6], vertical_alignment="bottom")
col_im1.image( lien_image_delta, )
colim2.image(lien_image_L_t)
colim3.image(lien_image_Vrds)
colim4.image(lien_image_sem)