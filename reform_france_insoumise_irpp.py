##########################################################
# Main code with static results and reforms simulation   #
##########################################################

#For EMTR study including PPE and RSA, some variables have been added to the postref scenario
#They are not included yet in the reforms scenarios.

# Steps
# 0 ) Imports, console...
# 1 ) Define variable lists and functions
# 2 ) Generate scenarios and export stats, marginal tax rates, tax amounts...
# 3 ) Inflatio is added step by step (which has allowed to check consistency of the output)
#    - Inflate data 
#    - Inflate the TBS system (inflate IR thresholds for example)
#    - Inflate both (that is the one that matters, the two first steps are muted)


import copy
import matplotlib.pyplot as plt
import pandas as pd

# Output path
import os
current_path = str(os.getcwd())
graphs_path = current_path.replace("reforms_irpp\\reforms_irpp", "reforms_irpp\\graphs_fi\\")
print(current_path)
print(graphs_path)
data_output_path = current_path.replace("reforms_irpp\\reforms_irpp", "reforms_irpp\\data_output_fi\\")
log_path = current_path.replace("reforms_irpp\reforms_irpp", "\logs\\")
# former path : graphs_path = "C:\\Users\\elieg\\reforms_irpp\\graphs\\"

from taxipp.reforms.asof import create_system_asof
from openfisca_france_data import france_data_tax_benefit_system
from openfisca_france_data.erfs_fpr.get_survey_scenario import get_survey_scenario
from openfisca_survey_manager.utils import inflate_parameters

# for FI reform
from openfisca_core.reforms import Reform


# For export to log
import sys
old_stdout = sys.stdout
log_name = log_path + "reform_FI_July21"
log_file = open(log_name + ".log","w")
#sys.stdout = log_file


#variables_mismatch
#{'autonomie_financiere', 'chomage_imposable', 'retraite_imposable',
# 'primes_fonction_publique', 'traitement_indiciaire_brut', 'cotisation_sociale_mode_recouvrement'}

#########################
# Console

# Try again with 2014 2016
reform_year = 2013
pre_reform_year = 2012
data_year = pre_reform_year
tracer_irpp = False

########################
croissance_2013_2019 = 1.09513

# Sources INSEE # Variation annuelle
# https://insee.fr/fr/statistiques/2122401#tableau-figure1
inflation_cpi_by_year = {
    2019:	1.1,
    2018:	1.8,
    2017:	1.0,
    2016:	0.2,
    2015:	0.0,
    2014:	0.5,
    2013:	0.9,
    2012:	2.0,
    2011:	2.1,
    2010:	1.5,
    2009:	0.1,
    2008:	2.8,
    2007:	1.5,
    2006:	1.7,
    2005:	1.7,
    2004:	2.1,
    2003:	2.1,
    2002:	1.9,
    2001:	1.6,
    2000:	1.7,
    1999:	0.5,
    1998:	0.6,
    1997:	1.2,
    1996:	2.0,
    1995:	1.8,
    1994:	1.6,
    1993:	2.1,
    1992:	2.4,
    1991:	3.2,
    }

variables_list_print_aggregates = ["salaire_de_base", "irpp", "retraite_brute", "chomage_brut", "traitement_indiciaire_brut"]

variable_for_mtr = "rni"

variables_of_interest = [
    'irpp',
    'nbptr',
    'weight_foyers',
    'weight_individus',
    'age', 
    'nb_adult', 
    'nb_pac',
    'statut_marital',
    'maries_ou_pacses',
    'celibataire_ou_divorce',
    'rfr',
    # 'revenu_assimile_salaire',
    # 'revenu_assimile_salaire_apres_abattements',
    # 'revenu_assimile_pension',
    # 'revenu_assimile_pension_apres_abattements',
    'ppe', 
    'foyer_impose', 
    'credits_impot',
    'rbg', 
    'rng', 
    'rni',
    'revenus_capitaux_mobiliers_plus_values_bruts_menage',
    'revenus_fonciers_bruts_menage', 
    'revenus_nets_du_capital',
    'revenus_nets_du_travail',
#    'revenus_remplacement_pensions_bruts_menage',
#    'revenus_super_bruts_menage',
#    'revenus_travail_super_bruts_menage',
#    'revenu_categoriel', 
#    'revenu_categoriel_capital',
#    'revenu_categoriel_foncier',
#    'revenu_categoriel_non_salarial',
#    'revenu_categoriel_plus_values',
#    'revenu_categoriel_tspr',
    "revenu_disponible",
    "retraite_brute", 
    "salaire_de_base", 
    "salaire_imposable",
    "chomage_brut", 
    "traitement_indiciaire_brut"]

variables_of_interest_mtr = [
    'irpp',
    'ir_taux_marginal', 
    'ir_tranche',
    'nbptr',
    'rni',
    'weight_foyers',
#    'weight_individus',
#    'age', 
#    'nb_adult', 
#    'nb_pac',
#    'statut_marital',
#    'maries_ou_pacses',
#    'celibataire_ou_divorce',
#    'rfr',
#    'rbg', 
#    'revenu_categoriel_tspr',
#    "retraite_brute", 
#    "chomage_brut", 
#    "traitement_indiciaire_brut",
]

variables_of_interest_rsa_ppe = [
    'nbptr',
    'rni',
    'weight_foyers',
    'nb_adult', 
    'nb_pac',
    'ppe_brute', 
    'rsa',
    'rsa_activite_individu',
    'rsa_socle', 
    'rsa_activite',
    'prestations_sociales',
    'minima_sociaux',
    'prestations_familiales',
    'reduction_loyer_solidarite',
    'aides_logement',
    'rsa_base_ressources_minima_sociaux',
    'rsa_base_ressources_individu',
]
# rsa_forfait_logement and aides_logement are always 0

if pre_reform_year is None:
    pre_reform_year = reform_year - 1
assert pre_reform_year < reform_year
if data_year is None:
    data_year = pre_reform_year

print("Reform year: ", reform_year, "    Pre-reform year: ", pre_reform_year, "    Data year: ", data_year)

def build_data(data_year, simulation_year):
    """
    To be used as an input for get_survey_scenario to force selection of data
    from a specific year
    data_year: survey wave to select
    simulation_year: year the model will consider
    """
    input_data_table_by_entity = dict(
        individu = "individu_{}".format(data_year),
        menage = "menage_{}".format(data_year),
        )
    input_data_table_by_entity_by_period = dict()
    input_data_table_by_entity_by_period[simulation_year] = input_data_table_by_entity
    data = dict(
        input_data_table_by_entity_by_period = input_data_table_by_entity_by_period,
        input_data_survey_prefix = "openfisca_erfs_fpr_data",
        )
    return data


def export_full_dataframe_by_entity(survey_scenarios_dict, case_name, data_year,
                                    tbs_year, data_output_path, variables_of_interest, baseline_or_not):
    """
    Creates and exports a dataframe in csv format with all variables of interest
    """
    df_by_entity = survey_scenarios_dict[case_name].create_data_frame_by_entity(
        variables = variables_of_interest,
        merge = True,
        index = True,
        use_baseline = baseline_or_not, # default = False
    )
    df_by_entity.to_csv(
        data_output_path + "output_" + case_name + "_TBS" + str(tbs_year)+ "_data" + str(data_year) + "_baseline" + str(baseline_or_not) + ".csv",
        sep = ';'
        )
    return df_by_entity

def export_graph_and_return_zoomdf(dataframe_by_entity, case_name, data_year, year_simulation, data_output_path, baseline_or_not):
    """
    Zoom on a specific population, create graph with bareme IRPP (PIT liability) and export it. Returns df with IRPP and RFR
    """
    dataframe = dataframe_by_entity[case_name][baseline_or_not]
    zoom_df_irpp = dataframe[ dataframe["rfr"] < 100000].copy()
    zoom_df_irpp = zoom_df_irpp[["rfr", "nb_adult", "nb_pac", "irpp"]]
    zoom_df_irpp = zoom_df_irpp[ zoom_df_irpp["nb_adult"] == 2]
    zoom_df_irpp = zoom_df_irpp[ zoom_df_irpp["nb_pac"] == 1]
    fig = plt.figure()
    x = fig.add_subplot()
    x = plt.scatter(zoom_df_irpp["rfr"], zoom_df_irpp["irpp"], s = 3)
    x.axes.set_title('Focus on households with 2 adults, 1 child (pac), rfr < 100000')
    x.axes.set_xlabel("Revenu fiscal de reference")
    x.axes.set_ylabel("IRPP liability")
    fig.suptitle('Bareme IRPP for case ' + str(case_name) + " (year = " + str(year_simulation) + ")", fontsize=16)
    x.figure.savefig(graphs_path + "IRPP_liabilities\\" + case_name + "_TBS" + str(year_simulation) + "_data" + str(data_year) + "_baseline" + str(baseline_or_not) + '.png',
                dpi = 300)
    #x.figure.show()    
    #plt.close()
    return zoom_df_irpp
    

# def export_df_graph_baseline_and_reform(
#     dataframe_by_entity, 
#     survey_scenarios_dict, 
#     case_name, 
#     data_year,
#     tbs_year, 
#     data_output_path, 
#     variables_of_interest, 
#     year_simulation,
#     ):
#     """
#     Export dataframes and create graph with IRPP liability, for both cases: baseline = True and baseline = False
#     """
#     assert case_name in dataframe_by_entity.keys()
    
#     for baseline_or_not in (True, False):
#         dataframe_by_entity[case_name][baseline_or_not] = export_full_dataframe_by_entity(
#             survey_scenarios_dict = survey_scenarios_dict, 
#             case_name = case_name, 
#             data_year = data_year, 
#             tbs_year = tbs_year,
#             data_output_path = data_output_path, 
#             variables_of_interest = variables_of_interest,
#             baseline_or_not = baseline_or_not,
#             )
#         zoomdf[case_name][baseline_or_not] = export_graph_and_return_zoomdf(dataframe_by_entity, case_name, data_year, 
#             year_simulation, data_output_path, baseline_or_not)


def compute_and_print_aggregate(scenario, reform_year, variables_list, no_baseline = False):
    """
    Computes aggregates of "salaire_de_base" and "irpp" in baseline and with reform
    """

    if no_baseline == False:
        print("Baseline (no reform):")
        print("     salaire_de_base {} (Mds): ".format(reform_year), scenario.compute_aggregate("salaire_de_base", period = reform_year, use_baseline = True) / 1e9)
        print("     IRPP {} (Mds): ".format(reform_year), scenario.compute_aggregate("irpp", period = reform_year, use_baseline = True) / 1e9)
    print("With reform (baseline = False):")
    print("     salaire_de_base {} (Mds): ".format(reform_year), scenario.compute_aggregate("salaire_de_base", period = reform_year, use_baseline = False) / 1e9)
    print("     IRPP {} (Mds): ".format(reform_year), scenario.compute_aggregate("irpp", period = reform_year, use_baseline = False) / 1e9)
    return scenario

def print_bracket_most_recent_params(tbs, bracket):
    ir_params = tbs.parameters.impot_revenu
    print("Most recent parameters for the bracket n° ", bracket, " : ")
    print("Threshold : ", ir_params.bareme.brackets[bracket].threshold.values_list[0])
    print("Rate : ", ir_params.bareme.brackets[bracket].rate.values_list[0])


def generate_scenario_and_results(
    case_name = str,
    baseline_tbs = None,
    tbs = None,
    year_simulation = reform_year,
    data_year = data_year,
    inflator_small_dict = None,
    data_output_path = data_output_path,
    variables_of_interest = variables_of_interest,
    varying_variable = variable_for_mtr,
    survey_scenarios_dict = dict(),
    dataframe_by_entity = dict(),
    zoomdf = dict(),
    save_memory = True,
    export = True,
    ):
    """
    Generate scenario, exports dataframe, IRPP liability graph, and prints agregates and bracket first threshold value
    For preref and postref: specific treatment without baseline case
    """

    print("Case name : ", case_name)
    if case_name not in dataframe_by_entity.keys():
        dataframe_by_entity[case_name] = dict()
    if case_name not in zoomdf.keys():
        zoomdf[case_name] = dict()

    if case_name in ["preref", "postref"]:

        survey_scenarios_dict[case_name] = get_survey_scenario(
        tax_benefit_system = tbs,
        year = year_simulation,
        rebuild_input_data = False,
        data = build_data(data_year = data_year, simulation_year = year_simulation),
        varying_variable = variable_for_mtr,
        use_marginal_tax_rate = True,
        )
        if inflator_small_dict != None:
            survey_scenarios_dict[case_name].inflate(inflator_by_variable= inflator_small_dict,
                period = reform_year)
        if export == True:
            baseline_or_not = False
            dataframe_by_entity[case_name][baseline_or_not] = export_full_dataframe_by_entity(
            survey_scenarios_dict = survey_scenarios_dict, 
            case_name = case_name, 
            data_year = data_year, 
            tbs_year = year_simulation,
            data_output_path = data_output_path, 
            variables_of_interest = variables_of_interest,
            baseline_or_not = baseline_or_not,
            )    
            zoomdf[case_name][baseline_or_not] = export_graph_and_return_zoomdf(dataframe_by_entity, case_name, data_year, year_simulation, data_output_path, baseline_or_not)

            # For the effective marginal tax rate
            df = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                    target_variable= 'irpp', 
                    period = reform_year, 
                    use_baseline = baseline_or_not,
                    )            
            irpp = survey_scenarios_dict[case_name].calculate_variable("irpp", period = reform_year, 
                                    use_baseline = baseline_or_not)
            
            df_pd = pd.DataFrame([df, irpp]).transpose()
            df_pd.columns = ["MTR_IRPP_" + str(variable_for_mtr), "irpp_from_mtr"]
            df_by_entity = survey_scenarios_dict[case_name].create_data_frame_by_entity(
                    variables = variables_of_interest_mtr,
                    merge = True,
                    index = True,
                    use_baseline = baseline_or_not, # default = False
                    )
            df_merged = pd.merge(df_pd, df_by_entity, 
                    left_index = True, right_on = "foyer_fiscal_id")
            df_merged.to_csv(
                data_output_path + "output_MTR_" + case_name 
                + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                + "_baseline" + str(baseline_or_not) + ".csv",
                sep = ';'
                )

            # Compute MTR on PPE
            dfppe = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                    target_variable= 'ppe', 
                    period = reform_year, 
                    use_baseline = baseline_or_not,
                    )            
            dfppe_pd = pd.DataFrame([dfppe]).transpose()
            dfppe_pd.columns = ['MTR_PPE_RNI']
            df_by_entity_ppe = survey_scenarios_dict[case_name].create_data_frame_by_entity(
                    variables = variables_of_interest_rsa_ppe,
                    merge = True,
                    index = True,
                    use_baseline = baseline_or_not, # default = False
                    )
            dfppe_merged = pd.merge(dfppe_pd, df_by_entity_ppe, 
                    left_index = True, right_on = "foyer_fiscal_id")
            dfppe_merged.to_csv(
                data_output_path + "output_MTRppe_" + case_name 
                + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                + "_baseline" + str(baseline_or_not) + ".csv",
                sep = ';'
                )
            
            # Compute MTR on RSA
            dfrsa_act = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                    target_variable= 'rsa_activite', 
                    period = reform_year, 
                    use_baseline = baseline_or_not)
            dfrsa_act_pd = pd.DataFrame([dfrsa_act]).transpose()
            dfrsa_act_merged = pd.merge(dfrsa_act_pd, df_by_entity_ppe, 
                    left_index = True, right_on = "foyer_fiscal_id")
            dfrsa_act_merged.to_csv(
                data_output_path + "output_MTRrsa_act_" + case_name 
                + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                + "_baseline" + str(baseline_or_not) + ".csv",
                sep = ';'
                )            
            dfrsa_socle = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                    target_variable= 'rsa_socle', 
                    period = reform_year, 
                    use_baseline = baseline_or_not)
            dfrsa_socle_pd = pd.DataFrame([dfrsa_socle]).transpose()
            dfrsa_socle_merged = pd.merge(dfrsa_socle_pd, df_by_entity_ppe, 
                    left_index = True, right_on = "foyer_fiscal_id")
            dfrsa_socle_merged.to_csv(
                data_output_path + "output_MTRrsa_socle_" + case_name 
                + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                + "_baseline" + str(baseline_or_not) + ".csv",
                sep = ';'
                )            
            dfrsa_montant = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                    target_variable= 'rsa_montant', 
                    period = reform_year, 
                    use_baseline = baseline_or_not)
            dfrsa_montant_pd = pd.DataFrame([dfrsa_montant]).transpose()
            dfrsa_montant_merged = pd.merge(dfrsa_montant_pd, df_by_entity_ppe, 
                    left_index = True, right_on = "foyer_fiscal_id")
            dfrsa_montant_merged.to_csv(
                data_output_path + "output_MTRrsa_montant_" + case_name 
                + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                + "_baseline" + str(baseline_or_not) + ".csv",
                sep = ';'
                )                    
        # Print in any case        
        print_bracket_most_recent_params(tbs, 1)
        compute_and_print_aggregate(survey_scenarios_dict[case_name], year_simulation, variables_list = variables_list_print_aggregates, no_baseline=True)

    else:
        survey_scenarios_dict[case_name] = get_survey_scenario(
        baseline_tax_benefit_system = baseline_tbs,
        tax_benefit_system = tbs,
        year = year_simulation,
        rebuild_input_data = False,
        data = build_data(data_year = data_year, simulation_year = year_simulation),
        varying_variable = variable_for_mtr,
        use_marginal_tax_rate = True,
        )
        if inflator_small_dict != None:
            survey_scenarios_dict[case_name].inflate(inflator_by_variable= inflator_small_dict,
                period = reform_year)
        if export == True:
            for baseline_or_not in [True, False] : 
                dataframe_by_entity[case_name][baseline_or_not] = export_full_dataframe_by_entity(
                survey_scenarios_dict = survey_scenarios_dict, 
                case_name = case_name, 
                data_year = data_year, 
                tbs_year = year_simulation,
                data_output_path = data_output_path, 
                variables_of_interest = variables_of_interest,
                baseline_or_not = baseline_or_not,
                )    
                zoomdf[case_name][baseline_or_not] = export_graph_and_return_zoomdf(dataframe_by_entity, case_name, data_year, year_simulation, data_output_path, baseline_or_not)
                
                # For the effective marginal tax rate
                df = survey_scenarios_dict[case_name].compute_marginal_tax_rate(
                        target_variable= 'irpp', 
                        period = reform_year, 
                        use_baseline = baseline_or_not,
                        )
                irpp = survey_scenarios_dict[case_name].calculate_variable("irpp", period = reform_year, 
                                       use_baseline = baseline_or_not)
                df_pd = pd.DataFrame([df, irpp]).transpose()
                df_pd.columns = ["MTR_IRPP_" + str(variable_for_mtr), "irpp_from_mtr"]
                df_by_entity = survey_scenarios_dict[case_name].create_data_frame_by_entity(
                        variables = variables_of_interest_mtr,
                        merge = True,
                        index = True,
                        use_baseline = baseline_or_not, # default = False
                        )
                df_merged = pd.merge(df_pd, df_by_entity, 
                     left_index = True, right_on = "foyer_fiscal_id")
                df_merged.to_csv(
                    data_output_path + "output_MTR_" + case_name 
                    + "_TBS" + str(reform_year)+ "_data" + str(data_year) 
                    + "_baseline" + str(baseline_or_not) + ".csv",
                    sep = ';'
                    )


        # Following two functions not tested here:
        print('\n Baseline TBS : ')
        print_bracket_most_recent_params(baseline_tbs, 1)
        print('\n Reformed TBS : ')
        print_bracket_most_recent_params(tbs, 1)
        compute_and_print_aggregate(survey_scenarios_dict[case_name], year_simulation, variables_list = variables_list_print_aggregates, no_baseline=False)

    # Save memory
    if save_memory == True:
        dataframe_by_entity[case_name] = dict()
        survey_scenarios_dict[case_name] = None

    print("\n", "********************")
    return dataframe_by_entity, zoomdf, survey_scenarios_dict

def calculate_variable_vectors(scenario, variable, xaxis_vector, 
                               truncated_at, export = False, 
                               year_simulation = reform_year, 
                               graphs_path = graphs_path, 
                               data_year = data_year, 
                               ):
    var_ref = scenario.calculate_variable(variable, 
                                          period = reform_year, 
                                          use_baseline = False)
    var = scenario.calculate_variable(variable, 
                                      period = reform_year, 
                                      use_baseline = True)
    df = pd.DataFrame(xaxis_vector)
    df.columns = ["xaxis_variable"]
    df["var_ref"] = var_ref
    df["var"] = var
    df["diff"] = df["var_ref"] - var
    upper_threshold = df["xaxis_variable"].quantile(q = truncated_at)
    df = df[ df['xaxis_variable'] < upper_threshold ]
    fig = plt.figure()
    x = fig.add_subplot()
    x = plt.scatter(df["xaxis_variable"], df["var"]) # s = 3
    x.axes.set_title('Excluding top ' + str(round(100 * (1 - truncated_at), 1)) +
                     '%, variable = ' + str(variable))
    fig2 = plt.figure()
    y = fig2.add_subplot()
    y = plt.scatter(df["xaxis_variable"], df["diff"])
    y.axes.set_title('Excluding top ' + str(round(100 * (1 - truncated_at), 1)) +
                     '%, reform of ' + str(variable))
    y.axes.set_xlabel('Index variable is RBG (by foyer) or TSPR (by individu)')
    print("Mean delta for ", variable, " : ", df["diff"].mean())
    if export == True: 
        y.figure.savefig(graphs_path + "TBS" + str(year_simulation) + 
                         "_data" + str(data_year) + "\\TBS" + str(year_simulation) + 
                         "_data" + str(data_year)
                         + "_variable_" + str(variable) + '.png',
                         dpi = 300)
        print("graph exported")


############################
# Create main dictionaries
############################

dataframe_by_entity = dict()
survey_scenarios_dict = dict()
tax_benefit_systems_dict = dict()
tbs_copy_dict = dict()
zoomdf = dict()

################################################
# Create TBS in status before reform
################################################

tax_benefit_system = france_data_tax_benefit_system
tbs_copy = copy.deepcopy(tax_benefit_system)
tbs_copy.entities = tax_benefit_system.entities
#tbs_copy2 = copy.deepcopy(tax_benefit_system)
#tbs_copy2.entities = tax_benefit_system.entities
tbs_copy3 = copy.deepcopy(tax_benefit_system)
tbs_copy3.entities = tax_benefit_system.entities

noreform = create_system_asof('{}-12-31'.format(pre_reform_year))
tax_benefit_systems_dict[pre_reform_year] = noreform(tax_benefit_system)
# Create TBS in status post reform 
reform_fullsystem = create_system_asof('{}-12-31'.format(pre_reform_year))
tax_benefit_systems_dict[reform_year] = reform_fullsystem(tbs_copy)
# Create a third TBS to which parameters inflation will be applied
tax_benefit_systems_dict["copy_for_inflation"] = noreform(tbs_copy3)

# Instance of the system to which the reform will be applied
#reform_fullsystem = create_system_asof('{}-12-31'.format(reform_year))
#tbs_copy_dict[reform_year] = reform_fullsystem(tbs_copy)

#################################################
# Coding the reform of FI
##################################################

#reform_fullsystem
#########################

class modif_taux_irpp(Reform):
    name = u"Modification du barème de l'impôt"

    def apply(self):

        def reform_modify_parameters(baseline_parameters_copy):
            reform_parameters = baseline_parameters_copy
            reform_parameters.impot_revenu.bareme.brackets[tranche].rate.update(
                    period = periods.period('year:{}'.format(year)),
                    value = new_taux,
                    )
            return reform_parameters

        self.modify_parameters(modifier_function = reform_modify_parameters)

#tax_benefit_system_reforme = mute_aides_logement(tbs_copy)





# Then use preref and simul


################################################
# Scenario of pre-reform tax system applied to pre-reform data
################################################

dataframe_by_entity, zoomdf, survey_scenarios_dict = generate_scenario_and_results(
    case_name = "preref",
    baseline_tbs = None,
    tbs = tax_benefit_systems_dict[pre_reform_year],
    year_simulation = pre_reform_year,
    data_year = pre_reform_year,
    inflator_small_dict = None,
    data_output_path = data_output_path,
    variables_of_interest = variables_of_interest,
    varying_variable = variable_for_mtr,
    survey_scenarios_dict = survey_scenarios_dict,
    dataframe_by_entity = dataframe_by_entity,
    zoomdf = zoomdf, 
    save_memory= True,
    export = True,
    )


stop 

################################################
# Scenario of post-reform tax system applied to post-reform data
################################################

#dataframe_by_entity, zoomdf, survey_scenarios_dict = generate_scenario_and_results(
#    case_name = "postref",
#    baseline_tbs = None,
#    tbs = tax_benefit_systems_dict[reform_year],
#    year_simulation = reform_year,
#    data_year = reform_year,
#    inflator_small_dict = None,
#    data_output_path = data_output_path,
#    variables_of_interest = variables_of_interest,
#    varying_variable = variable_for_mtr,
#    survey_scenarios_dict = survey_scenarios_dict,
#    dataframe_by_entity = dataframe_by_entity,
#    zoomdf = zoomdf,
#    save_memory= False,
#    export = True,
#    )


################################################
# Apply all reforms to data of pre-reform year
################################################

# Baseline and reform
dataframe_by_entity, zoomdf, survey_scenarios_dict = generate_scenario_and_results(
    case_name = "simul",
    baseline_tbs = tax_benefit_systems_dict[pre_reform_year],
    tbs = tax_benefit_systems_dict[reform_year],
    year_simulation = reform_year,
    data_year = pre_reform_year,
    inflator_small_dict = None,
    data_output_path = data_output_path,
    variables_of_interest = variables_of_interest,
    varying_variable = variable_for_mtr,
    survey_scenarios_dict = survey_scenarios_dict,
    dataframe_by_entity = dataframe_by_entity,
    zoomdf = zoomdf,
    save_memory= True,
    export = True,
    )

##### Compute IRPP with tracer and export result

if tracer_irpp == True:
    case_name = "simul"
    #old_stdout = sys.stdout
    log_file = open(log_name + "_irpp_trace" + ".log","w")
    sys.stdout = log_file
    survey_scenarios_dict[case_name].simulation.trace = True
    print("Test")
    survey_scenarios_dict[case_name].simulation.calculate("irpp", period = reform_year)
    survey_scenarios_dict[case_name].simulation.tracer.print_computation_log()
    log_file.close()
    sys.stdout = old_stdout

## Revert to usual log
##log_file = open(log_name + ".log","w")
##sys.stdout = log_file


#############################################################
# Inflate data
#############################################################

#print("\n", "********************")
##print("Attempt to simulate inflation on salaire_de_base")
#inflation_rate = 1 + inflation_cpi_by_year[reform_year] / 100
#inflator_small_dict = {'salaire_de_base': inflation_rate,
#                       'retraite_brute': inflation_rate,
#                       'traitement_indiciaire_brut': inflation_rate,
#                       'chomage_brut': inflation_rate
#                       }

#case_name = "simul_infdata"
#data_year = pre_reform_year
#year_simulation = reform_year
#dataframe_by_entity[case_name] = dict()
#zoomdf[case_name] = dict()
#
#data = build_data(data_year = data_year, simulation_year = year_simulation)
#
#survey_scenarios_dict[case_name] = get_survey_scenario(
#    baseline_tax_benefit_system = tax_benefit_systems_dict[pre_reform_year],
#    tax_benefit_system = tax_benefit_systems_dict[reform_year],
#    year = reform_year,
#    rebuild_input_data = False,
#    data = data,
#    )
#survey_scenarios_dict["simul_infdata"].inflate(inflator_by_variable= inflator_small_dict,
#                 period = reform_year)
#    
#
## Post inflation value
#print("\n", "********************")
#print(" Post inflation aggregate ")
#compute_and_print_aggregate(survey_scenarios_dict["simul_infdata"], reform_year, variables_list = variables_list_print_aggregates)
#
#print_bracket_most_recent_params(tax_benefit_systems_dict[reform_year], 1)
#
#export_df_graph_baseline_and_reform(
#    dataframe_by_entity = dataframe_by_entity, 
#    survey_scenarios_dict = survey_scenarios_dict, 
#    case_name = case_name, 
#    data_year = data_year, 
#    tbs_year = year_simulation,
#    data_output_path = data_output_path, 
#    variables_of_interest = variables_of_interest,
#    year_simulation = year_simulation,
#)


########### Inflate parameters

#print("\n", "********************", "Inflate parameters", "\n")
#
#
#case_name = "simul_infIRpar"
#data_year = pre_reform_year
#year_simulation = reform_year
##base_year_counterfactual = pre_reform_year
##year = reform_year
#inflator_impots = inflation_rate - 1
#
#tax_benefit_system_testinflation = tbs_copy2
#inflate_parameters(
#    tax_benefit_system_testinflation.parameters.impot_revenu,
#    inflator = inflator_impots,
#    base_year = pre_reform_year,
#    last_year = reform_year,
#    ignore_missing_units = True,
#    )
#
#data = build_data(data_year = data_year, simulation_year = year_simulation)
#
#survey_scenarios_dict[case_name] = get_survey_scenario(
#    baseline_tax_benefit_system = tax_benefit_system_testinflation,
#    tax_benefit_system = tax_benefit_systems_dict[reform_year],
#    year = reform_year,
#    rebuild_input_data = False,
#    data = data,
#    )
#survey_scenarios_dict[case_name] = survey_scenarios_dict["simul_infIRpar"]
#survey_scenarios_dict[case_name].inflate(inflator_by_variable= inflator_small_dict,
#                 period = reform_year)
#
#survey_scenarios_dict[case_name] = compute_and_print_aggregate(survey_scenarios_dict[case_name], reform_year, variables_list = variables_list_print_aggregates)
#
#export_df_graph_baseline_and_reform(
#    dataframe_by_entity = dataframe_by_entity, 
#    survey_scenarios_dict = survey_scenarios_dict, 
#    case_name = case_name, 
#    data_year = data_year, 
#    tbs_year = year_simulation,
#    data_output_path = data_output_path, 
#    variables_of_interest = variables_of_interest,
#    year_simulation = year_simulation,
#)


####################################
# Inflate the full TBS
####################################
#
#print("\n", "********************", "Inflate all TBS parameters", "\n")
#
#inflator_impots = inflation_rate - 1
#inflate_parameters(
#    tax_benefit_systems_dict["copy_for_inflation"].parameters,
#    inflator = inflator_impots,
#    base_year = pre_reform_year,
#    last_year = reform_year,
#    ignore_missing_units = True,
#    )
#
## Baseline and reform
#dataframe_by_entity, zoomdf, survey_scenarios_dict = generate_scenario_and_results(
#    case_name = "simul_inf_datapar",
#    baseline_tbs = tax_benefit_systems_dict["copy_for_inflation"],
#    tbs = tax_benefit_systems_dict[reform_year],
#    year_simulation = reform_year,
#    data_year = pre_reform_year,
#    inflator_small_dict = inflator_small_dict,
#    data_output_path = data_output_path,
#    variables_of_interest = variables_of_interest,
#    varying_variable = variable_for_mtr,
#    survey_scenarios_dict = survey_scenarios_dict,
#    dataframe_by_entity = dataframe_by_entity,
#    zoomdf = zoomdf,
#    save_memory= False,
#    export = True,
#    )
#
#case_name = "simul_inf_datapar"
#compute_and_print_aggregate(survey_scenarios_dict[case_name], reform_year, variables_list = variables_list_print_aggregates)
#print_bracket_most_recent_params(tax_benefit_systems_dict["copy_for_inflation"], 1)
#print_bracket_most_recent_params(tax_benefit_systems_dict[reform_year], 1)
#
#
###############################
## Study the reform step by step
#
#scenario = survey_scenarios_dict["simul_inf_datapar"]
#rbg = scenario.calculate_variable("rbg", period = reform_year, use_baseline = True)
#tspr_i = scenario.calculate_variable("traitements_salaires_pensions_rentes", period = reform_year, use_baseline = True)
#
## Example
#calculate_variable_vectors(scenario, "irpp", rbg, 0.99, export = False, year_simulation = reform_year, graphs_path = graphs_path, 
#data_year = data_year)

