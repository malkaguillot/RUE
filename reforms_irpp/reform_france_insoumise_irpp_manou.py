import asyncio

from fastapi import APIRouter, Depends, WebSocket

# import numpy as np
from openfisca_core.errors import SituationParsingError
from openfisca_core.parameters import helpers, ParameterNode, ParameterScaleBracket
from openfisca_core.periods import instant
from openfisca_core.reforms import Reform
from openfisca_core.scripts import build_tax_benefit_system
from openfisca_core.simulation_builder import SimulationBuilder
from openfisca_core.taxbenefitsystems import TaxBenefitSystem

from .. import config


router = APIRouter(
    prefix="/simulations",
    tags=["simulations"],
)
tax_benefit_system_by_name = None


# Caution: This function modify existing parameters instead of duplicating them.
def apply_parametric_reform(parameters, parameter_change_by_name):
    errors = {}
    for name, change in parameter_change_by_name.items():
        ids = name.split(".")
        parameter = parameters
        for id in ids:
            parameter = getattr(parameter, id, None)
            if parameter is None:
                errors[name] = f"Parameter doesn't exist. Missing {id}"
                break
        else:
            changeType = change.get("type")
            if changeType == "parameter":
                parameter.update(
                    start=instant(change.get("start")),
                    stop=instant(change.get("stop")),
                    value=change.get("value"),
                )
            elif changeType == "scale":
                # TODO: handle stop?.
                if change.get("stop") is not None:
                    errors[name] = "Scale change can't contain a 'stop'"
                    break
                # Note: change has the form:
                # {
                #     start: "2021-01-01",
                #     bracket: {
                #         threshold1: amount_or_rate1,
                #         threshold2: amount_or_rate2,
                #         …,
                #         },
                #     }
                # This is not the same structure as OpenFisca
                # brackets => Convert it:
                brackets = parameter.brackets
                value_key = (
                    "amount"
                    if any("amount" in bracket.children for bracket in brackets)
                    else "average_rate"
                    if any("average_rate" in bracket.children for bracket in brackets)
                    else "rate"
                )
                change_brackets = sorted(
                    [
                        (float(threshold), value)
                        for threshold, value in change["bracket"].items()
                    ],
                    key=lambda threshold_value: threshold_value[0],
                )
                start = change["start"]
                for index, (threshold, value) in enumerate(change_brackets):
                    if len(brackets) <= index:
                        brackets.append(
                            ParameterScaleBracket(
                                name=helpers._compose_name(
                                    parameter.name, item_name=index
                                ),
                                data={
                                    "threshold": {start: threshold},
                                    value_key: {start: value},
                                },
                            )
                        )
                    else:
                        bracket_dict = brackets[index].children
                        bracket_dict["threshold"].update(
                            start=instant(start),
                            value=threshold,
                        )
                        bracket_dict[value_key].update(
                            start=instant(start),
                            value=value,
                        )
            else:
                errors[name] = f"Change type {changeType} doesn't exist."
    return errors or None


def get_tax_benefit_system_by_name(
    settings: config.Settings = Depends(config.get_settings),
):
    global tax_benefit_system_by_name
    if tax_benefit_system_by_name is None:
        tax_benefit_system = build_tax_benefit_system(
            settings.country_package,
            None,  # settings.extension,
            None,  # settings.reform,
        )

        def lfi_modifier(parameters: ParameterNode):
            # See:
            # https://www.assemblee-nationale.fr/dyn/15/amendements/2272A/CION_FIN/CF1391
            errors = apply_parametric_reform(
                parameters,
                {
                    "impot_revenu.bareme": dict(
                        bracket={
                            "0": 0.01,
                            "10293": 0.05,
                            "15439": 0.10,
                            "20585": 0.15,
                            "27790": 0.20,
                            "30877": 0.25,
                            "33965": 0.30,
                            "38082": 0.35,
                            "44257": 0.40,
                            "61753": 0.45,
                            "102922": 0.50,
                            "144090": 0.55,
                            "267595": 0.60,
                            "411684": 0.90,
                        },
                        start="2020-01-01",
                        type="scale",
                    ),
                },
            )
            assert errors is None, errors
            return parameters

        class LfiReform(Reform):
            def apply(self):
                self.modify_parameters(modifier_function=lfi_modifier)

        lfi_reform = LfiReform(tax_benefit_system)
        tax_benefit_system_by_name = {
            "": tax_benefit_system,
            "PLF LFI": lfi_reform,
        }
    return tax_benefit_system_by_name


# Note: Router prefix is not used for websocket‽
@router.websocket("/simulations/calculate")
async def calculate(
    websocket: WebSocket,
    tax_benefit_system_by_name: TaxBenefitSystem = Depends(
        get_tax_benefit_system_by_name
    ),
):
    await websocket.accept()
    period = None
    reform = None
    simulation_tax_benefit_system = tax_benefit_system_by_name[""]
    situation = None
    token = None
    variables_name = None
    while True:
        data = await websocket.receive_json()
        calculate = False
        errors = {}
        for key, value in data.items():
            if key == "calculate":
                calculate = True
            if key == "period":
                print("Received period.")
                period = value
                continue
            if key == "reform":
                print("Received reform.")
                if type(value) is str:
                    reform_tax_benefit_system = tax_benefit_system_by_name.get(value)
                    if reform_tax_benefit_system is None:
                        errors["reform"] = "Unknown tax benefit system"
                    else:
                        simulation_tax_benefit_system = reform_tax_benefit_system
                else:
                    reform = (
                        None
                        if value is None
                        else {
                            parameter_name: parameter_value
                            for parameter_name, parameter_value in value.items()
                            if parameter_value is not None
                        }
                        or None
                    )
                    if reform:

                        def simulation_modifier(parameters: ParameterNode):
                            reform_errors = apply_parametric_reform(parameters, reform)
                            if reform_errors is not None:
                                errors["reform"] = reform_errors
                            return parameters

                        class SimulationReform(Reform):
                            def apply(self):
                                self.modify_parameters(
                                    modifier_function=simulation_modifier
                                )

                        simulation_tax_benefit_system = SimulationReform(
                            tax_benefit_system_by_name[""]
                        )
                    else:
                        simulation_tax_benefit_system = tax_benefit_system_by_name[""]
                continue
            if key == "situation":
                print("Received situation.")
                situation = value
                continue
            if key == "token":
                print("Received token.")
                token = value
                continue
            if key == "variables":
                print("Received names of variables to calculate.")
                variables_name = value
                continue

        if errors:
            print("Error:", errors)
            await websocket.send_json(dict(errors=errors))
            continue

        if calculate:
            print("Calculating…")

            if not variables_name:
                errors["variables"] = "Missing value"
            if period is None:
                errors["period"] = "Missing value"
            if not situation:
                errors["situation"] = "Missing value"
            simulation_builder = SimulationBuilder()

            if errors:
                print("Error:", errors)
                await websocket.send_json(dict(errors=errors))
                continue

            try:
                simulation = simulation_builder.build_from_entities(
                    simulation_tax_benefit_system, situation
                )
            except SituationParsingError as e:
                errors["build_from_entities"] = e.error
                print("Error:", errors)
                await websocket.send_json(dict(errors=errors))
                continue

            for variable_name in variables_name:
                value = simulation.calculate_add(variable_name, period)
                population = simulation.get_variable_population(variable_name)
                entity = population.entity
                # entity_count = simulation_builder.entity_counts[entity.plural]
                # sum = (
                #     np.sum(
                #         np.split(
                #             value,
                #             population.count // entity_count,
                #         ),
                #         1,
                #     )
                #     if entity_count > 1
                #     else value
                # )
                print(f"Calculated {variable_name} ({entity.key}): {value}")
                await websocket.send_json(
                    dict(
                        entity=entity.key,
                        name=variable_name,
                        token=token,
                        value=value.tolist(),
                    )
                )
                await asyncio.sleep(0)
