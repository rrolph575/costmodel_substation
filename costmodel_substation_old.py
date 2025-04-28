"""
Unless otherwise specified, costs are USD2023/mile
"""

#%% Imports
import os
import numpy as np
import pandas as pd

projpath = os.path.dirname(__file__)

datapath  = os.path.join(projpath,'data','MISO','2024')

#%% Constants
SQFT_PER_ACRE = 43560
KVS = [69, 115, 138, 161, 230, 345, 500, 765]

#%% Assumptions

#%% Functions

def get_land_terrain_cost(
        kv=500,
        substation_option = 'upgrade',
        num_positions=1,
        landtype = 'light_veg'
    ):
    """
    Substation options:  new or upgrade
    for upgrade: add 1 or 2 positions
    for new substation: 4 or 6 positions
    """
    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)

    ## Access road cost
    access_road_cost_per_mile = pd.read_csv(os.path.join(datapath, f'access_road_cost.csv')).iloc[0][0]
    access_road_cost = subspecs.loc['access_road_miles']*access_road_cost_per_mile
    
    ## Site terrain cost
    df = pd.read_csv(os.path.join(datapath, f'substruct_terraincost.csv'))
    cost_per_acre = df.loc[df['landtype'] == landtype, '$peracre'].values[0]
    num_acres = subspecs.loc['acres']
    terrain_cost = cost_per_acre*num_acres
    
    land_terrain_cost = access_road_cost + terrain_cost

    return land_terrain_cost

land_terrain_cost = get_land_terrain_cost()


def get_controlcable_conduit_cabletrench_cost(
        kv=500,
        substation_option = 'upgrade',
        num_positions=1
    ):
    """
    Control cable, conduit, and cable trench costs
    Control cable and conduit unit costs (both material and installation) are associated with 1,000 ft of control cable/conduit.
    Cable trench unit cost is associated with 1 ft of cable trench

    Substation options:  new or upgrade
    for upgrade: add 1 or 2 positions
    for new substation: 4 or 6 positions
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)
    
    ## Control cable
    # Unit cost
    df = pd.read_csv(os.path.join(datapath, f'control_cable_unit_costs.csv'), index_col=0, header=None)
    control_cable_material_unit_cost = df.loc['material_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    control_cable_installation_unit_cost = df.loc['installation_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    # Number units
    control_cable_length = subspecs.loc['control_cable']/1000 # Convert units to 1000s of ft bc unit cost is associated with 1000s of ft.  
    # Total control cable cost
    cc_cost = control_cable_length * (control_cable_material_unit_cost + control_cable_installation_unit_cost)

    ## Conduit
    df = pd.read_csv(os.path.join(datapath, f'conduit_unit_costs.csv'), index_col=0, header=None)
    conduit_material_unit_cost = df.loc['material_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    conduit_installation_unit_cost = df.loc['installation_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    # Number units
    conduit_length = subspecs.loc['conduit_ft']/1000 # Convert units to 1000s of ft.  
    # Total control cable cost
    conduit_cost = conduit_length * (conduit_material_unit_cost + conduit_installation_unit_cost)

    ## Cable trench (unit costs per foot)
    df = pd.read_csv(os.path.join(datapath, f'cable_trench_unit_costs.csv'), index_col=0, header=None)
    cable_trench_material_unit_cost = df.loc['material_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    cable_trench_installation_unit_cost = df.loc['installation_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
    # Number units
    cable_trench_length = subspecs.loc['cable_trench_ft'] # Units are ft
    # Total control cable cost
    cable_trench_cost = cable_trench_length * (cable_trench_material_unit_cost + cable_trench_installation_unit_cost)

    ## Total cable cost
    total_cable_cost = cc_cost + conduit_cost + cable_trench_cost

    return total_cable_cost
    
total_cable_cost = get_controlcable_conduit_cabletrench_cost()

print('break')

def circuit_breaker_cost(
        kv = 500,
        substation_option = 'upgrade',
        num_positions=1
    ):
    """
    Total circuit breaker unit costs are a sum of circut breaker components. 
    This function calculates the unit sum, then multiplies by number of circuit breakers depending on project specified.
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)
    
    # Circuit breaker summed unit costs
    df = pd.read_csv(os.path.join(datapath, f'circuit_breaker_unit_costs.csv'), index_col=0, header=None)
    _df = df.loc[:, df.columns[df.loc['voltage_kv'] == kv][0]].copy()
    _circuit_breaker_cost = _df.loc[[i for i in _df.index if 'cost' in i]].copy()
    circuit_breaker_cost = _circuit_breaker_cost.copy() 
    circuit_breaker_cost = circuit_breaker_cost.sum()

    # Number circuit breakers
    num_breakers = subspecs.loc['circuit_breaker']

    # Total circuit breaker cost
    total_circuit_breaker_cost = num_breakers * circuit_breaker_cost

    return total_circuit_breaker_cost

total_circuit_breaker_cost = circuit_breaker_cost()

print('break')

def disconnect_switch_cost(
        kv = 500,
        substation_option = 'upgrade',
        num_positions=1
    ):
    """
    Total disconnect switch unit cost is a sum of its components. 
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)  
    
    # Summed unit costs
    df = pd.read_csv(os.path.join(datapath, f'disconnect_switch_unit_costs.csv'), index_col=0, header=None)
    _df = df.loc[:, df.columns[df.loc['voltage_kv'] == kv][0]].copy()
    _disconnect_switch_cost = _df.loc[[i for i in _df.index if 'cost' in i]].copy()
    disconnect_switch_cost = _disconnect_switch_cost.copy() 
    disconnect_switch_cost = disconnect_switch_cost.sum()

    # Number 
    num = subspecs.loc['disconnect_switches']

    # Total cost
    total_disconnect_switch_cost = num * disconnect_switch_cost

    return total_disconnect_switch_cost

total_disconnect_switch_cost = disconnect_switch_cost()

def bus_costs(
        kv = 500,
        substation_option = 'upgrade',
        num_positions=1
    ):
    """
    Total disconnect switch unit cost is a sum of its components. 
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)  
 
    # Summed unit costs
    df = pd.read_csv(os.path.join(datapath, f'bus_unit_costs.csv'), index_col=0, header=None)
    _df = df.loc[:, df.columns[df.loc['voltage_kv'] == kv][0]].copy()
    _bus_cost = _df.loc[[i for i in _df.index if 'cost' in i]].copy()
    bus_cost = _bus_cost.copy() 
    bus_cost = bus_cost.sum()

    # Number
    num = subspecs.loc['bus_support']

    # Total cost
    total_bus_cost = num * bus_cost

    return total_bus_cost

total_bus_cost = bus_costs()

print('break')


#### Trying to have a csv as an input

def costs(
        kv = 500,
        substation_option = 'upgrade',
        num_positions=1,
        csv = 'bus_unit_costs.csv',
        component_name = 'bus_support'
    ):
    """
    Total disconnect switch unit cost is a sum of its components. 
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        #'double_breaker'
    ]
    dictin_substation = {
        bus: pd.read_csv(
            os.path.join(
                datapath,
                f'substation_{substation_option}_{num_positions}_positions_{bus}.csv'
            ),
            index_col=0,
        )
        for bus in bus_types
    }
    subspecs = pd.concat(dictin_substation, axis=0)[str(kv)].unstack(0)  
 
    # Summed unit costs
    df = pd.read_csv(os.path.join(datapath, csv), index_col=0, header=None)
    _df = df.loc[:, df.columns[df.loc['voltage_kv'] == kv][0]].copy()
    _cost = _df.loc[[i for i in _df.index if 'cost' in i]].copy()
    cost = _cost.copy() 
    cost = cost.sum()

    # Number
    num = subspecs.loc[component_name]

    # Total cost
    total_cost = num * cost

    return total_cost

total_cost = costs(csv='disconnect_switch_unit_costs.csv', component_name='disconnect_switches') 

print('break')
