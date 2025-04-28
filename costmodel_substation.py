"""
Unless otherwise specified, costs are USD2024/mile
"""

#%% Imports
import os
import pandas as pd
import matplotlib.pyplot as plt

projpath = os.path.dirname(__file__)

datapath  = os.path.join(projpath,'data','MISO','2024','substation')
figpath = os.path.join(projpath,'plots')

#%% Constants
SQFT_PER_ACRE = 43560
KVS = [69, 115, 138, 161, 230, 345, 500, 765]

#%% Assumptions

#%% Functions

### Land terrain cost
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
        'double_breaker'
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
    access_road_cost_per_mile = pd.read_csv(
        os.path.join(datapath, 'access_road_cost.csv')
    ).squeeze()
    access_road_cost = subspecs.loc['access_road_miles']*access_road_cost_per_mile

    df_access = pd.DataFrame(list(access_road_cost.items()), columns=['bus_type','cost'])
    df_access['cost_type'] = 'Access road'

    ## Site terrain cost
    df = pd.read_csv(os.path.join(datapath, 'substruct_terraincost.csv'))
    cost_per_acre = df.loc[df['landtype'] == landtype, '$peracre'].values[0]
    num_acres = subspecs.loc['acres']
    terrain_cost = cost_per_acre*num_acres

    df_terrain = pd.DataFrame(list(terrain_cost.items()), columns=['bus_type', 'cost'])
    df_terrain['cost_type'] = 'Terrain'

    df_access_and_terrain = pd.concat([df_access, df_terrain])

    return df_access_and_terrain



### Control cable, conduit, and cable trenching costs
def get_cable_costs(
        kv=500,
        substation_option='upgrade',
        num_positions=1,
    ):
    """
    Control cable, conduit, and cable trench costs combined into one DataFrame.

    Substation options: new or upgrade
    for upgrade: add 1 or 2 positions
    for new substation: 4 or 6 positions
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        'double_breaker'
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

    #combined_cable_costs = pd.DataFrame()
    full_costs_df = []

    cost_types=['control_cable', 'conduit', 'cable_trench']  # List of cost types

    for cost_type in cost_types:
        df = pd.read_csv(
            os.path.join(datapath, f'{cost_type}_unit_costs.csv'),
            index_col=0, header=None)
        material_cost = df.loc['material_cost', df.columns[df.loc['voltage_kv'] == kv][0]]
        installation_cost = df.loc['installation_cost', df.columns[df.loc['voltage_kv'] == kv][0]]

        # Determine length based on cost type
        length = (
            subspecs.loc[f'{cost_type}_ft'] / 1000 if cost_type != 'cable_trench'
            else subspecs.loc[f'{cost_type}_ft']
        )

        material_cost_total = length * material_cost
        installation_cost_total = length * installation_cost

        df_materials = pd.DataFrame(
            list(material_cost_total.items()), columns=['bus_type', 'cost'])
        df_materials['cost_cat'] = 'Materials'
        df_installation = pd.DataFrame(
            list(installation_cost_total.items()), columns=['bus_type', 'cost'])
        df_installation['cost_cat'] = 'Installation'

        df_costs = pd.concat([df_materials, df_installation])
        df_costs['cost_type'] = cost_type

        full_costs_df.append(df_costs)

    cable_costs_df = pd.concat(full_costs_df)

    return cable_costs_df



### Other component costs
def component_costs(
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
        'double_breaker'
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



### Common costs
def get_common_cost_mult(**kwargs):
    """
    Use keyword arguments matching common_costs.csv to overwrite default values
    """
    filepath = os.path.join(os.path.dirname(datapath),'common_costs.csv')
    common_costs = pd.read_csv(filepath, index_col=0).squeeze(1)
    for key, val in kwargs.items():
        if key in common_costs.index:
            common_costs[key] = val
        else:
            raise KeyError(f"{key} is not in {filepath}")

    soft_costs_mult = common_costs[[
        'project_management',
        'administrative_general',
        'engineering',
    ]].sum() + 1

    total_mult = (
        soft_costs_mult
        * (common_costs['contingency'] + 1)
        * (common_costs['afudc'] + 1)
    )

    return total_mult



## Get valdiation costs
def get_validation_cost(
        kv=500,
        substation_option='upgrade',
        num_positions=1,
        bus_type_for_plot='ring'
    ):
    """
    """

    bus_types = [
        'ring',
        'breaker_and_half',
        'double_breaker'
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
    total_cost = subspecs.loc['validation']
    total_cost['kv']=kv

    return total_cost

# Plotting
def stacked_bar(final_plot_df, MISO_validation_costs, fig_filename):
    # Filter for the 'ring' bus type
    data = final_plot_df.loc[[bus_type_for_plot]]
    columns = final_plot_df.columns.drop('kv')
    colors = plots.rainbowmapper(columns)

    # Create a bar chart without kv values as part of the data
    plt.close()
    f,ax = plt.subplots(figsize=(4.75,3.25))
    data.drop(columns=['kv']).plot(
        ax=ax, kind='bar', stacked=True, color=colors,
    )

    # Adding dots for validation values
    for i, row in enumerate(MISO_validation_costs):
        heights = row
        ax.plot(
            i, heights,
            lw=0, marker='o', markerfacecolor='none', markeredgecolor='k',
            label='_nolabel',
        )

    # Set x-tick label to read kv value from the final_plot_df
    kv_value = data['kv'] # Get the kv value
    ax.set_xticks(range(len(kv_value)))  # Only one bar, so x index is 0
    ax.set_xticklabels(kv_value.values, rotation=0)  # Use the kv value

    # ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    handles, labels = ax.get_legend_handles_labels()
    _leg = ax.legend(
        handles=handles[::-1], labels=labels[::-1],
        ncol=1, columnspacing=0.5, frameon=False,
        # handletextpad=0.5, handlelength=0.8,
        handletextpad=0.3, handlelength=0.7,
        loc='center left', bbox_to_anchor=(1.02, 0.5),
    )
    ax.set_title(f'{substation_option}_{bus_type_for_plot}_{num_positions}positions_{landtype}')
    ax.set_xlabel('Voltage [kV]')
    ax.set_ylabel('Cost [$M]')
    plots.despine(ax)
    # plt.xticks(final_plot_df['kv'].unique())  # Set x-ticks to unique kv values
    # plt.tight_layout()
    # plt.savefig(fig_filename, bbox_inches='tight')
    plt.show()

    return


#%%### Procedure
if __name__ == '__main__':
    #%% Imports
    import matplotlib.pyplot as plt
    import site
    site.addsitedir(os.path.expanduser('~/github/ReEDS-2.0/postprocessing'))
    import plots
    plots.plotparams()

    # %%
    ### Call functions
    # List of kv values to loop through
    kv_values = [69,115,138,161,230,345,500,765]  # Add more kv values as needed

    # Constants for other parameters
    substation_option = 'new'  # 'upgrade' for 1 or 2 positions, 'new', for 4 or 6 positions
    num_positions = 4
    landtype = 'light_veg' # light_veg, forest, wetland
    # 'ring', 'breaker_and_half', 'double_breaker'  ... note the code produces data for all 3
    # bus types given the constants above... can be reworked to be more efficient if desired
    bus_type_for_plot = 'breaker_and_half'
    fig_filename = os.path.join(
        figpath, f"{substation_option}_{bus_type_for_plot}_{num_positions}positions_{landtype}.png"
    )


    # List to collect plot data for all kv values
    all_plot_data = []

    # Loop through each kv value
    for kv in kv_values:
        # Access road and terrain costs
        df_access_and_terrain = get_land_terrain_cost(
            kv=kv,
            substation_option=substation_option,
            num_positions=num_positions,
            landtype=landtype
        )

        # Cable component costs
        cable_costs_df = get_cable_costs(
            kv=kv,
            substation_option=substation_option,
            num_positions=num_positions
        )

        # Other component costs
        components = [
            ('circuit_breaker_unit_costs.csv', 'circuit_breaker'),
            ('disconnect_switch_unit_costs.csv', 'disconnect_switches'),
            ('bus_unit_costs.csv', 'bus_support'),
            ('voltage_transformer_unit_costs.csv', 'voltage_transformers'),
            ('control_enclosure_unit_costs.csv', 'control_enclosure'),
            ('relay_panel_costs.csv', 'relay_panel'),
            ('deadend_angled_structure_costs.csv', 'deadend_struct')
        ]

        # Dictionary to store the costs
        component_costs_dict = {}

        # Loop through each component to calculate costs
        for csv_file, component_name in components:
            component_costs_dict[component_name] = component_costs(
                kv=kv,
                substation_option=substation_option,
                num_positions=num_positions,
                csv=csv_file,
                component_name=component_name
            )

        # Transforming the data into a DataFrame
        rows = []
        for cost_type, series in component_costs_dict.items():
            for bus_type, cost in series.items():
                rows.append({'bus_type': bus_type, 'cost': cost, 'cost_type': cost_type})

        component_costs_df = pd.DataFrame(rows)

        ### Combine dataframes
        df = pd.concat([df_access_and_terrain, cable_costs_df, component_costs_df])

        ### Add common costs
        pivot_df = df.pivot_table(
            index='bus_type', columns='cost_type', values='cost', aggfunc='sum').fillna(0)
        total_cost_by_bustype = pivot_df.copy()
        total_cost_by_bustype = total_cost_by_bustype.sum(axis=1)
        total_mult = get_common_cost_mult()
        pivot_df['softcost'] = total_cost_by_bustype * (total_mult - 1)

        ### Prepare for plotting
        plot_df = pivot_df.copy()
        plot_df = plot_df / 1e6  # Convert to millions
        plot_df['kv'] = kv  # Add kv to the plot DataFrame

        # Append the current plot data to the list
        all_plot_data.append(plot_df)



    ## Get validation costs for each kv
    validation_costs = []
    for kv in kv_values:
        MISO_validation_costs = get_validation_cost(
            kv=kv,
            substation_option=substation_option,
            num_positions=num_positions,
            bus_type_for_plot=bus_type_for_plot
        )
        validation_costs.append(MISO_validation_costs)

    validation_to_plot = pd.DataFrame(validation_costs)


    # Concatenate all plot data into a single DataFrame
    final_plot_df = pd.concat(all_plot_data)

    # Run and save plot
    stacked_bar(
        final_plot_df=final_plot_df,
        MISO_validation_costs=validation_to_plot[bus_type_for_plot],
        fig_filename=fig_filename,
    )


    #### !!! NOTES BELOW TO BE DISCUSSED !!! #####

    #  Table 2.3 -6 (current transformer)
    # !! Verify with MISO these are not included in costs

    #  Table 2.3 -8 (Grid supporting devices unit costs)
    # !! Verify with MISO these are not included in validation costs

    #  Table 2.3 -7 (Power transformer)  # !! Not all substations need power transformers
    #     If we use Table 3.1 - 5 to get number of MVAs,
    #  .. then the costs are much higher than the validation values in Table 4.2-1.
    #  .. For example, Table 3.1 -5  gives 2598 MVA for 500kV/500kV.
    #  .. when multiplied by 13784 $/MVA from Table 2.3 -7,
    #  .. that is already 35 $M, order of magnitude higher than validation value in Table 4.1-1.