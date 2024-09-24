import numpy as np
import pandas as pd
import scipy
from scipy.optimize import fsolve

X0 = {
    "Uniaxiale": 0.9,
    "Biaxiale": 0.81,
}

def create_axe(geo_Sinf, geo_Ame, geo_Ssup, E, nb_rot):
    S_inf = dict(b=geo_Sinf["b"],  ### ATTENTION b NE DOIT JAMAIS ETRE NUL, ON L'ABSCENSE DE LA PIECE METTRE h A 0
        h=geo_Sinf["h"], f_y=geo_Sinf["f_y"], x_inf=0, )
    Ame = dict(b=geo_Ame["b"],  ### ATTENTION b NE DOIT JAMAIS ETRE NUL, ON L'ABSCENSE DE LA PIECE METTRE h A 0
        h=geo_Ame["h"], f_y=geo_Ame["f_y"], x_inf=S_inf["x_inf"] + geo_Sinf["h"], )
    S_sup = dict(b=geo_Ssup["b"],  ### ATTENTION b NE DOIT JAMAIS ETRE NUL, ON L'ABSCENSE DE LA PIECE METTRE h A 0
        h=geo_Ssup["h"], f_y=geo_Ssup["f_y"], x_inf=Ame["x_inf"] + geo_Ame["h"], nb_rot=nb_rot )

    axe = dict(S_inf=S_inf, Ame=Ame, S_sup=S_sup, )

    for _, piece in axe.items():
        piece["x_sup"] = piece["x_inf"] + piece["h"]
        piece["A"] = piece["b"] * piece["h"]
        piece["A_fy"] = piece["f_y"] * piece["A"]
        piece["E"] = E

    return axe


def calc_AN_in_Sinf(axe):
    x_min, x_max = axe["S_inf"]["x_inf"], axe["S_inf"]["x_sup"]
    A_fy_tot = sum(piece["A_fy"] for piece in axe.values())
    x = A_fy_tot / (2 * axe["S_inf"]["b"]) / axe["S_inf"]["f_y"]
    return (x, True) if (x < x_max) & (x >= x_min) else (x, False)


def calc_AN_in_Ame(axe):
    S_inf = axe["S_inf"]
    Ame = axe["Ame"]
    S_sup = axe["S_sup"]
    x_min, x_max = Ame["x_inf"], Ame["x_sup"]
    x = (S_sup["A_fy"] - S_inf["A_fy"] + Ame["A_fy"] + 2 * S_inf["h"] * Ame["b"] * Ame["f_y"]) / (
                2 * Ame["b"] * Ame["f_y"])

    return (x, True) if (x < x_max) & (x >= x_min) else (x, False)


def calc_AN_in_Ssup(axe):
    S_inf = axe["S_inf"]
    Ame = axe["Ame"]
    S_sup = axe["S_sup"]
    x_min, x_max = S_sup["x_inf"], S_sup["x_sup"]
    x = (S_sup["A_fy"] - S_inf["A_fy"] - Ame["A_fy"] + 2 * S_sup["b"] * S_sup["f_y"] * (S_inf["h"] + Ame["h"])) / (
                2 * S_sup["b"] * S_sup["f_y"])

    return (x, True) if (x < x_max) & (x >= x_min) else (x, False)


def calc_AN(axe):
    # On calcul les axes neutre dans chacune des hypothèses
    AN_Sinf = calc_AN_in_Sinf(axe)
    AN_Ame = calc_AN_in_Ame(axe)
    AN_Ssup = calc_AN_in_Ssup(axe)
    pos_AN_test = dict(AN_Sinf=AN_Sinf, AN_Ame=AN_Ame, AN_Ssup=AN_Ssup)
    AN = [(x, verif) for x, verif in pos_AN_test.values() if verif][0]
    pos_AN = [key for key, val in pos_AN_test.items() if val == AN][0]

    return pos_AN, AN

def calc_piece(piece, x):
    if x >= piece["x_sup"]:
        # Géométrie de la pièce
        delta = x - (piece["x_sup"] + piece["x_inf"]) / 2  # Bras de levier
        A = piece["A"]
        # Calcul du moment plastique
        W_pl = delta * A
        M_pl = W_pl * piece["f_y"] * 10 ** -6
        #  Calcul du module d'inertie de la pièce
        I_base = (piece["b"] * piece["h"] ** 3) / 12  # Inertie de la pièce seule
        I = I_base + piece["A"] * delta ** 2  # Inertie de la pièce dans l'axe complet
    elif x < piece["x_inf"]:
        # Géométrie de la pièce
        delta = (piece["x_sup"] + piece["x_inf"]) / 2 - x  # Bras de levier
        A = piece["A"]
        # Calcul du moment plastique
        W_pl = delta * A
        M_pl = W_pl * piece["f_y"] * 10 ** -6
        #  Calcul du module d'inertie de la pièce
        I_base = (piece["b"] * piece["h"] ** 3) / 12  # Inertie de la pièce seule
        I = I_base + piece["A"] * delta ** 2  # Inertie de la pièce dans l'axe complet
    else:
        # Géométrie de la pièce inférieure
        delta_inf = (x - piece["x_inf"]) / 2  # Bras de levier
        A_inf = piece["b"] * (x - piece["x_inf"])
        # Calcul du moment plastique de la partie inférieure de la pièce
        W_inf = delta_inf * A_inf
        M_pl_inf = W_inf * piece["f_y"] * 10 ** -6
        #  Calcul du module d'inertie de la pièce inférieure
        I_base_inf = (piece["b"] * (x - piece["x_inf"]) ** 3) / 12
        I_inf = I_base_inf + A_inf * delta_inf ** 2
        # Géométrie de la pièce supérieure
        delta_sup = (piece["x_sup"] - x) / 2  # Bras de levier
        A_sup = piece["b"] * (piece["x_sup"] - x)
        # Calcul du moment plastique de la partie supérieure de la pièce
        W_sup = delta_sup * A_sup
        M_pl_sup = W_sup * piece["f_y"] * 10 ** -6
        #  Calcul du module d'inertie de la pièce inférieure
        I_base_sup = (piece["b"] * (piece["x_sup"] - x) ** 3) / 12
        I_sup = I_base_sup + A_sup * delta_sup ** 2
        # Calcul du moment plastique de la pièce complète
        M_pl = M_pl_inf + M_pl_sup
        I = I_inf + I_sup

    return M_pl, I


def calc_caract(axe):
    list_M_pl, list_I, list_A = [], [], []
    pos_AN, (x, _) = calc_AN(axe)
    for _, piece in axe.items():
        M_pl_piece, I_piece = calc_piece(piece, x)
        list_M_pl.append(M_pl_piece)
        list_I.append(I_piece)
        list_A.append(piece["A"])
    M_pl = sum(list_M_pl)
    I = sum(list_I)
    V_pl = axe.get("Ame")["A"] * axe.get("Ame")["f_y"] / 3 ** 0.5 * 10 ** -3
    E = max(axe.get("Ame")["E"], 210_000)
    A_tot = sum(list_A)


    return dict(pos_AN=pos_AN, x=x, M_pl=M_pl, V_pl=V_pl, I=I, list_M_pl=list_M_pl, list_I=list_I, E=E, A=A_tot )


def calc_Vrks(M_pl, V_pl, t, e):
    bras_levier = (t + 2 * e) * 10 ** -3  # bras de levier en m
    inter = lambda V_rks: (V_rks / V_pl) ** 2 + (V_rks * bras_levier / (2 * M_pl)) ** 2 - 1  # Equation Interaction CSTB
    V_rks = fsolve(inter, V_pl)[0]  # On résolve l'équation
    print(e)

    return V_rks

def calc_def_axe(E, I, t, e, V_els, d_max):
    b_l = (t+ 2*e) # en mm
    d = V_els *10**3 * b_l**3 / (3 * E* I) # en mm
    V_max_ELS = d_max * 3*E*I / b_l**3 * 10**-3  # Effort ELS correspondant au déplacement max
    V_max_ELU = V_max_ELS * 1.4 # Effort max ELU correspondant au déplacement max
    return d, V_max_ELU

def calc_fat_axe(V_els, t, e, V_pl, M_pl):
    b_l = (t + 2*e) * 10**-3 # en m
    M_els = V_els * b_l   # en kN.m
    taux_min = min(V_pl / V_els, M_pl / M_els)
    V_max_ELS = V_els * taux_min
    V_max_ELU = V_max_ELS * 1.4
    verif = True if round(taux_min,2) >= 1 else False
    return taux_min, verif, V_max_ELU

def verif_axe(axe, t, L, beta, d_max, X0, gamma_s, V_elu, rho):
    # On récupére les caractéristiques de l'axe
    caract = calc_caract(axe)
    # Calcul e l'effort atteint ELU et vérification$
    e = L / (3*beta) / 2  # Distance du fixing point au bord du béton
    V_Rks = calc_Vrks(caract["M_pl"], caract["V_pl"], t, e,)
    V_Rds = V_Rks * X0 / gamma_s
    verif_Vrds = V_Rds >= V_elu
    # Calcul de l'effort cible ELS
    V_els = V_elu / 1.4
    M_els = V_els * (t+2*e)
    # Calcul des déformation dans l'axe et vérification
    d, V_max_d = calc_def_axe(caract["E"], caract["I"], t, e, V_els, d_max)
    verif_def = True if d <= d_max else False
    # Calcul de la fatigue et vérifiation
    tau_fat, verif_fat, V_max_fat = calc_fat_axe(V_els, t, e, caract["V_pl"], caract["M_pl"])
    verif_axe = verif_Vrds * verif_def * verif_fat
    # Rajout des caractéristique calculés dans le dict
    var = [V_Rks, V_Rds, verif_Vrds, V_els, M_els, d, verif_def, V_max_d, tau_fat, verif_fat, V_max_fat, verif_axe]
    keys = ["V_Rks", "V_Rds", "verif_Vrds","V_els", "M_els", "d", "verif_def", "V_max_d", "tau_fat", "verif_fat", "V_max_fat","verif_axe"]
    dict_var = dict(zip(keys, var))
    caract.update(dict_var)
    df_caract = pd.DataFrame(caract)
    df_caract.drop(["list_M_pl", "list_I"], axis=1, inplace=True)
    df_caract.drop([1, 2], axis=0, inplace=True)
    df_caract["tau_V"] = df_caract["V_Rds"].apply(lambda x: round(x / V_elu,3))
    df_caract["V_ELU"] = V_elu
    df_caract["d_max"] = d_max
    df_caract["tau_d"] = df_caract["d"].apply(lambda x: d_max / x)
    df_caract["Volume"] = df_caract["A"] * (L + 35 + 90)  # Volume du profilé en mm3
    df_caract["Masse"] = df_caract["Volume"] * rho * 10**-9  # Masse du profilé en kg

    V_Rds = df_caract.loc[0, "V_Rds"]
    V_max = min(V_Rds, V_max_d, V_max_fat)

    return verif_axe, df_caract, V_max


def verif_Mpl_semelle(M_pl, nb_rotule, V_elu, delta_lat, X0, gamma_s):
    V_rot = V_elu * gamma_s / X0 / nb_rotule
    M_rot = V_rot * (delta_lat) * 10 ** -3  # En kN.m moment à reprendre dans chaque rotule
    V_rot_max = M_pl / (delta_lat * 10**-3)
    V_max = V_rot_max * X0 * nb_rotule / gamma_s  # Effort max de reprise à l'ELU
    verif = round(M_rot,2) <= round(M_pl,2)
    dic = {"M_pl": M_pl, "M_rot": M_rot, "verif_Mpl": verif, "V_max_rot": V_max,}

    return dic


def calc_def_semelle(E, I, nb_rotule, V_els, delta_lat, d_max):
    d = (V_els * 10 ** 3 / nb_rotule) * (delta_lat) ** 3 / (3 * E * I)
    V_max_ELS = d_max / delta_lat**3 * (3*E*I) * nb_rotule / 10**3  # Effort max pour le déplacement max à l'ELS
    V_max_ELU = V_max_ELS * 1.4  # Effort equivalent à l'ELU
    return d, V_max_ELU


def calc_fat_semelle(V_els, delta_lat, M_pl, nb_rotule):
    M_els = V_els * delta_lat * 10 ** -3 / nb_rotule # en kN.m
    taux_min = M_pl / M_els
    V_max_ELS = M_pl * nb_rotule / delta_lat * 10**3
    V_max_ELU = V_max_ELS * 1.4
    verif = True if taux_min >= 1 else False
    return taux_min, verif, V_max_ELU


def calc_caract_semelle(semelle, L_gaine, beta, ):
    l = L_gaine / (3 * beta)  # Calcul de la longueur d'application des contraintes  (Mattock & Gaafar)
    # Récupération géométrie
    h = semelle["h"]
    # Calcul du moment plastique
    f_y = semelle["f_y"]
    W_pl = l * h ** 2 / 4
    M_pl = W_pl * f_y * 10 ** -6  # en kN.m
    # Calcul Inertie
    I = l * h ** 3 / 12
    caract_bis = dict(M_pl=M_pl, I=I, L_gaine=L_gaine, l=l)
    semelle.update(caract_bis)

    return semelle


def verif_semelle(semelle, nb_rotule, L_gaine, beta, delta_lat, V_elu, d_max, X0, gamma_s):
    caract = calc_caract_semelle(semelle, L_gaine, beta)
    M_pl = caract["M_pl"]
    I = caract["I"]
    E = caract["E"]
    V_els = V_elu / 1.4
    M_els = V_els * delta_lat * 10 ** -3 / nb_rotule
    dict_verif_Mpl = verif_Mpl_semelle(M_pl, nb_rotule=nb_rotule, V_elu=V_elu, delta_lat=delta_lat, X0=X0, gamma_s=gamma_s)
    M_rot = dict_verif_Mpl["M_rot"]
    d, V_max_d = calc_def_semelle(E, I, nb_rotule, V_els, delta_lat, d_max)
    verif_d = bool(d <= d_max)
    tau_fat, verif_fat, V_max_fat = calc_fat_semelle(V_els, delta_lat, M_pl, nb_rotule=nb_rotule)
    verif_semelle = bool(dict_verif_Mpl["verif_Mpl"] * verif_d * verif_fat)
    var = [nb_rotule, M_rot, d, verif_d,V_max_d, M_els, tau_fat, verif_fat, V_max_fat, verif_semelle]
    keys = ["nb_rotule", "M_rot", "d", "verif_d", "V_max_d", "M_els", "tau_fat", "verif_fat", 'V_max_fat', "verif_semelle"]
    dict_var = dict(zip(keys, var))
    caract.update(dict_var)
    caract.update(dict_verif_Mpl)
    df_caract = pd.DataFrame(caract, index=[0])
    df_caract["d_max"] = d_max

    df_caract["tau_M"] = df_caract["M_rot"].apply(lambda x: round(M_pl / x, 1))
    df_caract["tau_d"] = df_caract["d"].apply(lambda x: d_max / x)

    V_max_rot = df_caract.loc[0, "V_max_rot"]
    V_max = min(V_max_rot, V_max_d, V_max_fat)

    return verif_semelle, df_caract, V_max

def caract_prod(df_caract_axe, df_caract_sem):
    V_min_axe = df_caract_axe[["V_Rds", "V_max_d", "V_max_fat"]].min()
    print(V_min_axe)
    V_min_sem = df_caract_sem[["V_max_rot", "V_max_d", "V_max_fat"]].min()
    V_min_prod = min(V_min_axe, V_min_sem)

    return V_min_prod, V_min_axe, V_min_sem