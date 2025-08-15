import traci
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET

def costs_matrix(origins: list, destinations: list, netfile: str) -> dict:
    sumo_binary = "sumo" # On-View

    # Launching SUMO with TraCI
    sumo_cmd = [
        sumo_binary,
        "-n", netfile,
        "--start",
        "--quit-on-end",
        ]
    traci.start(sumo_cmd)

    # Computing costs
    costs = {}

    for o in origins:
        for d in destinations:
            if o != d:
                route = traci.simulation.findRoute(o,d)
                time = route.travelTime
                costs[(o,d)] = round(time,2)

    traci.close()

    return costs

def read_counts(excel_path: str) -> list[dict, dict]:
    df = pd.read_excel(excel_path, index_col=0, header=0)
    df['access_id'] = df['tipo_acceso'] + '_' + df['sentido'] + '_' + df['avenida']
    counts_dict = df.set_index('access_id')['conteo_veh_h'].to_dict()

    G = {}
    A = {}
    for acceso, conteo in counts_dict.items():
        if 'in_' in acceso:
            G[acceso] = conteo
        elif 'out_' in acceso:
            A[acceso] = conteo

    return G, A

def gravity_model(G: dict, A: dict, costs: dict,BETA = 0.2) -> pd.DataFrame:
    matrix_od = {}

    for o in G:
        for d in A:
            key = (o, d)
            if key in costs:
                c_ij = costs[key]
                t_ij = G[o] * A[d] * np.exp(-BETA * c_ij)
                matrix_od[(o,d)] = t_ij
            else:
                matrix_od[(o,d)] = 0 # There is no connection

    # Normalizing
    for o in G:
        total_row = sum(matrix_od[(o, d)] for d in A)
        if total_row > 0:
            for d in A:
                matrix_od[(o, d)] *= G[o] / total_row

    for d in A:
        total_col = sum(matrix_od[(o, d)] for o in G)
        if total_col > 0:
            for o in G:
                matrix_od[(o, d)] *= A[d] / total_col
    
    # Matrix in pandas
    df_od = pd.DataFrame.from_dict(matrix_od, orient='index', columns=['viajes'])
    df_od.index = pd.MultiIndex.from_tuples(df_od.index, names = ['origen', 'destino'])
    df_od = df_od.reset_index()
    df_od['viajes'] = df_od['viajes'].round().astype(int)
    # df_od['viajes'] = df_od['viajes'].apply(lambda x: np.random.poisson(x))

    return df_od

def contours_finder(netfile: str):
    tree = ET.parse(netfile)
    net_tag = tree.getroot()
    edges = net_tag.findall('edge')
    ORIGINS, DESTINATIONS = [], []
    for edge in edges:
        name = edge.get('id')
        if 'in_' in name:
            ORIGINS.append(name)
        elif 'out_' in name:
            DESTINATIONS.append(name)
    
    return ORIGINS, DESTINATIONS