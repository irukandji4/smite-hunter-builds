import itertools
import json
from dataclasses import dataclass
from typing import *

import charybdis as charybdis_
from tqdm import tqdm

from item import God, Item, Scenario, passives_map

squishy = Scenario(
    fight_length=2,
    enemy_prots=100,
    spectral_armor=0,
    enemy_health=2000,
    approx_aa_cnt=4,
    approx_ability_cnt=1,
    true_squishy_false_tank=True,
)

tank = Scenario(
    fight_length=4,
    enemy_prots=300,
    spectral_armor=0.40,
    enemy_health=3000,
    approx_aa_cnt=8,
    approx_ability_cnt=2,
    true_squishy_false_tank=False,
)

amc = God(aa_stim=0, aa_stim_length=0, is_failnot_good=True)
anhur = God(aa_stim=0, aa_stim_length=0, is_failnot_good=False)
apollo = God(aa_stim=1, aa_stim_length=-5, is_failnot_good=True)
artemis = God(aa_stim=0.8, aa_stim_length=5, is_failnot_good=True)
cern = amc
charybdis = God(aa_stim=0.25, aa_stim_length=0, is_failnot_good=True)
chernobog = God(aa_stim=0.6, aa_stim_length=5, is_failnot_good=True)
chiron = anhur
cupid = God(aa_stim=0.2, aa_stim_length=0, is_failnot_good=True)
danza = amc
hachiman = God(aa_stim=0.4, aa_stim_length=6, is_failnot_good=True)
heimdallr = amc
hou_yi = amc
izanami = God(aa_stim=0.75, aa_stim_length=6, is_failnot_good=True)
jing_wei = anhur
medusa = God(aa_stim=0.8, aa_stim_length=-4, is_failnot_good=True)
neith = amc
rama = God(aa_stim=0.5, aa_stim_length=5, is_failnot_good=False)
skadi = amc
ullr = God(aa_stim=0.3, aa_stim_length=0, is_failnot_good=False)
xbalanque = amc


@dataclass
class BuildResult:
    build: list[str]
    build_item: Item
    dps: float | None = None
    dps_percent: float | None = None
    dpspg: float | None = None
    dpspg_percent: float | None = None
    parent_results: list["BuildResult"] | None = None

    def __repr__(self):
        item_rows = []
        item_row_length = 2
        item_i = 0
        while item_i < len(self.build):
            item_rows.append(self.build[item_i : item_i + item_row_length])
            item_i += item_row_length
        build = "\n".join("  " + ", ".join(item_row) for item_row in item_rows)
        dps = f"{self.dps_percent:.2%}" + (
            f" ({self.dps:.2f})" if self.dps is not None else ""
        )
        dpspg = f"{self.dpspg_percent:.2%}" + (
            f" ({self.dpspg:.4f})" if self.dpspg is not None else ""
        )
        parent_results = ""
        for i, parent_result in enumerate(self.parent_results, 1):
            parent_results += (
                f"\nScenario #{i}\n"
                f"  DPS:"
                f" {parent_result.dps_percent:.2%} ({parent_result.dps:.2f})\n"
                f"  DPSPG:"
                f" {parent_result.dpspg_percent:.2%} ({parent_result.dpspg:.4f})"
            )
        return (
            f"Items:\n"
            f"{build}\n"
            f"Price: {self.build_item.price}\n"
            f"PWR: {self.build_item.physical_power}"
            f" AS: {self.build_item.attack_speed:.2f}\n"
            f"CRIT: {self.build_item.critical_strike_chance:.0%}"
            f" PEN: {self.build_item.percent_pen:.0%}\n"
            f"DPS: {dps}\n"
            f"DPSPG: {dpspg}"
            f"{parent_results}\n"
            "-----------------------------"
        )


@dataclass
class Experiment:
    dps_squishy: List[BuildResult]
    dpspg_squishy: List[BuildResult]
    dps_tank: List[BuildResult]
    dpspg_tank: List[BuildResult]
    dps_both: List[BuildResult]
    dpspg_both: List[BuildResult]


class Smite:
    def __init__(self):
        self.api = charybdis_.Api()
        self.all_gods: list | None = None
        self.avg_hunter_basic_attack: int | None = None
        self.avg_hunter_attack_speed: float | None = None
        self.avg_hunter_mana: int | None = None
        self.all_items: list | None = None
        self.all_items_by_id: dict | None = None
        self.starter_items: dict | None = None
        self.normal_items: dict | None = None
        self.items_raw: dict | None = None
        self.items: dict[str, Item] | None = None

    def save_items_to_file(self, filename: str = "items.json"):
        self.all_items = self.api.call_method("getitems", "1")
        with open(filename, "w") as f:
            f.write(json.dumps(self.all_items, indent=2))

    def read_items_from_file(self, filename: str = "items.json"):
        with open(filename, "r") as f:
            self.all_items = json.load(f)

    def save_gods_to_file(self, filename: str = "gods.json"):
        self.all_gods = self.api.call_method("getgods", "1")
        with open(filename, "w") as f:
            f.write(json.dumps(self.all_gods, indent=2))

    def read_gods_from_file(self, filename: str = "gods.json"):
        with open(filename, "r") as f:
            self.all_gods = json.load(f)

    def prepare_items_raw(self):
        self.all_items_by_id = {x["ItemId"]: x for x in self.all_items}
        self.starter_items = []
        self.normal_items = []
        for item in self.all_items:
            if item["ActiveFlag"] == "n":
                continue
            if item["ItemTier"] == 2 and item["StartingItem"]:
                self.starter_items.append(item)
                continue
            if "hunter" in item["RestrictedRoles"]:
                continue
            if not (
                item["ItemTier"] == 3
                or item["ItemTier"] == 4
                and item["DeviceName"].startswith("Evolved")
            ):
                continue
            if item["DeviceName"].endswith("Acorn"):
                continue
            stats = item["ItemDescription"]["Menuitems"]
            has_phys_power_or_as = False
            has_prots_or_health_or_mag_power = False
            for stat in stats:
                desc = stat["Description"]
                match desc:
                    case "Physical Power":
                        has_phys_power_or_as = True
                    case "Attack Speed":
                        has_phys_power_or_as = True
                    case "Physical Protection":
                        has_prots_or_health_or_mag_power = True
                    case "Magical Protection":
                        has_prots_or_health_or_mag_power = True
                    case "Health":
                        has_prots_or_health_or_mag_power = True
                    case "Magical Power":
                        has_prots_or_health_or_mag_power = True
            if has_prots_or_health_or_mag_power:
                continue
            elif has_phys_power_or_as:
                self.normal_items.append(item)

        starter_item_names = ["Death", "Cowl", "Arrow", "Manikin", "Bluestone"]
        self.starter_items = [
            x
            for x in self.starter_items
            if any(y in x["DeviceName"] for y in starter_item_names)
        ]
        self.starter_items = {
            x["DeviceName"]: x
            for x in sorted(self.starter_items, key=lambda x: x["DeviceName"])
        }
        unevolved_item_names = [
            x["DeviceName"][len("Evolved ") :]
            for x in self.normal_items
            if x["DeviceName"].startswith("Evolved")
        ]
        self.normal_items = [
            x for x in self.normal_items if x["DeviceName"] not in unevolved_item_names
        ]
        self.normal_items = {
            x["DeviceName"]: x
            for x in sorted(self.normal_items, key=lambda x: x["DeviceName"])
        }
        self.items_raw = self.starter_items | self.normal_items

    def print_passives(self):
        for item_name, item in self.items_raw.items():
            passive = item["ItemDescription"]["SecondaryDescription"]
            if passive:
                print(item_name)
                print(passive)
                print("---")

    def print_stat_descs(self):
        all_stat_descs = set()
        for item in self.items_raw.values():
            stats = item["ItemDescription"]["Menuitems"]
            for stat in stats:
                all_stat_descs.add(stat["Description"])
        for stat_desc in sorted(all_stat_descs):
            print(stat_desc)

    def prepare_avg_hunter_stats(self):
        hunters = [x for x in self.all_gods if x["Roles"] == "Hunter"]
        basic_attack_sum = sum(
            x["PhysicalPower"] + 20 * x["PhysicalPowerPerLevel"] for x in hunters
        )
        attack_speed_sum = sum(
            x["AttackSpeed"] + 20 * x["AttackSpeedPerLevel"] for x in hunters
        )
        mana_sum = sum(x["Mana"] + 20 * x["ManaPerLevel"] for x in hunters)
        self.avg_hunter_basic_attack = basic_attack_sum / len(hunters)
        self.avg_hunter_attack_speed = attack_speed_sum / len(hunters)
        self.avg_hunter_mana = mana_sum / len(hunters)

    def prepare_items(self):
        self.items = {}
        passives_check = set(passives_map.keys())
        for item_name, item_raw in self.items_raw.items():
            self.items[item_name] = Item.from_item_raw(item_raw, self.all_items_by_id)
            if (
                item_name not in passives_check
                and item_raw["ItemDescription"]["SecondaryDescription"]
            ):
                print(f"[WARNING] Unrecognized passive: {item_name}")
            passives_check.discard(item_name)
        for item_name in passives_check:
            print(f"[WARNING] Unused passive: {item_name}")

    def generate_builds(self, must_include_item_names: list[str], build_size: int):
        if len(must_include_item_names) > build_size:
            raise ValueError("Too many must include items")
        starter_item_names = list(self.starter_items.keys())
        normal_item_names = list(self.normal_items.keys())
        for item_name in must_include_item_names:
            if item_name in starter_item_names:
                starter_item_names.remove(item_name)
            elif item_name in normal_item_names:
                normal_item_names.remove(item_name)
            else:
                raise ValueError(f"Could not find item by name {item_name}")
        # https://stackoverflow.com/a/48619647
        nested_item_names = [[x] for x in normal_item_names]
        nested_item_names = [starter_item_names] + nested_item_names
        for c in itertools.combinations(
            nested_item_names, build_size - len(must_include_item_names)
        ):
            for p in itertools.product(*c):
                yield must_include_item_names + list(p)

    def get_build_results(
        self,
        scenario: Scenario,
        god: God,
        must_include_item_names: list[str],
        build_size: int = 6,
    ) -> list[BuildResult]:
        build_results = []
        max_dps = 0.0
        max_dpspg = 0.0
        for build in tqdm(
            list(self.generate_builds(must_include_item_names, build_size))
        ):
            build_item = Item(
                basic_attack=self.avg_hunter_basic_attack,
                attack_speed=self.avg_hunter_attack_speed
                + god.aa_stim / (1 if god.aa_stim_length == 0 else 2),
                critical_strike_multiplier=-scenario.spectral_armor,
            )

            passives = []
            for item_name in build:
                item = self.items[item_name]
                build_item += item
                if item.passive is not None:
                    passives.append(item.passive)
            for passive in sorted(passives, key=lambda x: x.phase):
                passive.compute(scenario, god, build_item)

            dps = build_item.compute_dps(
                fight_length=scenario.fight_length, enemy_prots=scenario.enemy_prots
            )
            max_dps = max(max_dps, dps)
            dpspg = dps / build_item.price
            max_dpspg = max(max_dpspg, dpspg)
            build_results.append(
                BuildResult(
                    build=build,
                    build_item=build_item,
                    dps=dps,
                    dpspg=dpspg,
                    parent_results=[],
                )
            )

        for build_result in build_results:
            build_result.dps_percent = build_result.dps / max_dps
            build_result.dpspg_percent = build_result.dpspg / max_dpspg
        return build_results

    @staticmethod
    def average_build_results(
        list_of_build_results: Sequence[list[BuildResult]],
        weights: Sequence[float] = None,
    ) -> list[BuildResult]:
        if weights is None:
            weights = [1] * len(list_of_build_results)
        assert len(list_of_build_results) == len(weights)
        total_weight = sum(weights)
        avg_build_results = [
            BuildResult(
                build=build_result.build,
                build_item=build_result.build_item,
                dps_percent=0,
                dpspg_percent=0,
                parent_results=[],
            )
            for build_result in list_of_build_results[0]
        ]
        for build_results, weight in zip(list_of_build_results, weights):
            for avg_build_result, build_result in zip(avg_build_results, build_results):
                avg_build_result.dps_percent += weight * build_result.dps_percent
                avg_build_result.dpspg_percent += weight * build_result.dpspg_percent
                avg_build_result.parent_results.append(build_result)

        for avg_build_result in avg_build_results:
            avg_build_result.dps_percent /= total_weight
            avg_build_result.dpspg_percent /= total_weight
        return avg_build_results

    def run_experiment(
        self,
        god: God,
        must_include_item_names: list[str],
        build_size: int = 6,
    ):
        build_results_squishy = self.get_build_results(
            scenario=squishy,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )
        build_results_tank = self.get_build_results(
            scenario=tank,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )
        build_results_both = self.average_build_results(
            [build_results_squishy, build_results_tank],
        )
        return Experiment(
            dps_squishy=self.sort_build_results(build_results_squishy, True),
            dpspg_squishy=self.sort_build_results(build_results_squishy, False),
            dps_tank=self.sort_build_results(build_results_tank, True),
            dpspg_tank=self.sort_build_results(build_results_tank, False),
            dps_both=self.sort_build_results(build_results_both, True),
            dpspg_both=self.sort_build_results(build_results_both, False),
        )

    @staticmethod
    def sort_build_results(
        build_results: Iterable[BuildResult], true_dps_false_dpspg: bool
    ):
        comparator = (
            (lambda x: x.dps_percent)
            if true_dps_false_dpspg
            else (lambda x: x.dpspg_percent)
        )
        return sorted(build_results, key=comparator, reverse=True)
