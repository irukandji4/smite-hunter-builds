import datetime
import hashlib
import itertools
import json
import operator
import os
from typing import *

import requests
from tqdm import tqdm

import item as ITEM
from item import God, Item, Scenario

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
    spectral_armor=0.30,
    enemy_health=3000,
    approx_aa_cnt=8,
    approx_ability_cnt=2,
    true_squishy_false_tank=False,
)

chiron = God(aa_stim=0, aa_stim_length=0, is_failnot_good=False)


class Smite:
    base_url = "https://api.smitegame.com/smiteapi.svc"

    def __init__(self):
        # Smite API stuff.
        self.dev_id: str | None = None
        self.auth_key: str | None = None
        self.session: str | None = None
        # Builds stuff.
        self.all_gods: list | None = None
        self.avg_hunter_basic_attack: int | None = None
        self.avg_hunter_attack_speed: float | None = None
        self.all_items: list | None = None
        self.starter_items: dict | None = None
        self.normal_items: dict | None = None
        self.items_raw: dict | None = None
        self.items: dict[str, Item] | None = None

    def read_credentials(self):
        self.dev_id = os.getenv("SMITE_DEV_ID")
        if self.dev_id is None:
            raise RuntimeError("SMITE_DEV_ID unset")
        self.auth_key = os.getenv("SMITE_AUTH_KEY")
        if self.auth_key is None:
            raise RuntimeError("SMITE_AUTH_KEY unset")

    @staticmethod
    def ping():
        return requests.get(Smite.base_url + "/pingjson")

    def create_session(self):
        self.session = None
        self.session = self.call_method("createsession").json()["session_id"]

    def create_signature(self, method_name: str, timestamp: str):
        return hashlib.md5(
            f"{self.dev_id}{method_name}{self.auth_key}{timestamp}".encode("utf8")
        ).hexdigest()

    def call_method(self, method_name: str, *args):
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )
        signature = self.create_signature(method_name, timestamp)
        if self.session is None:
            url = f"{Smite.base_url}/{method_name}json/{self.dev_id}/{signature}/{timestamp}"
        else:
            url = f"{Smite.base_url}/{method_name}json/{self.dev_id}/{signature}/{self.session}/{timestamp}"
        for arg in args:
            url += f"/{arg}"
        return requests.get(url)

    def save_items_to_file(self, filename: str = "items.json"):
        self.all_items = self.call_method("getitems", "1").json()
        with open(filename, "w") as f:
            f.write(json.dumps(self.all_items, indent=2))

    def read_items_from_file(self, filename: str = "items.json"):
        with open(filename, "r") as f:
            self.all_items = json.load(f)

    def save_gods_to_file(self, filename: str = "gods.json"):
        self.all_gods = self.call_method("getgods", "1").json()
        with open(filename, "w") as f:
            f.write(json.dumps(self.all_gods, indent=2))

    def read_gods_from_file(self, filename: str = "gods.json"):
        with open(filename, "r") as f:
            self.all_gods = json.load(f)

    def prepare_items_raw(self):
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
        self.avg_hunter_basic_attack = basic_attack_sum / len(hunters)
        self.avg_hunter_attack_speed = attack_speed_sum / len(hunters)

    def prepare_items(self):
        self.items = {}
        passives_check = set(ITEM.passives.keys())
        for item_name, item_raw in self.items_raw.items():
            self.items[item_name] = Item.from_item_raw(item_raw)
            if (
                item_name not in passives_check
                and item_raw["ItemDescription"]["SecondaryDescription"]
            ):
                print(f"[WARNING] Unrecognized passive: {item_name}")
            passives_check.discard(item_name)
        for item_name in passives_check:
            print(f"[WARNING] Unused passive: {item_name}")

    def generate_combinations(
        self, must_include_item_names: List[str], build_size: int
    ):
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
        nested_item_names = [[x] for x in normal_item_names]
        nested_item_names = [starter_item_names] + nested_item_names
        for c in itertools.combinations(
            nested_item_names, build_size - len(must_include_item_names)
        ):
            for p in itertools.product(*c):
                yield tuple(must_include_item_names + list(p))

    def get_builds(
        self,
        scenario: Scenario,
        god: God,
        must_include_item_names: List[str],
        build_size: int = 6,
    ):
        builds = {}
        for build in tqdm(
            list(self.generate_combinations(must_include_item_names, build_size))
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
            builds[build] = dps

        builds_sorted_by_dps = sorted(
            builds.items(), key=operator.itemgetter(1), reverse=True
        )
        builds_sorted_by_dps = {build: dps for build, dps in builds_sorted_by_dps}
        max_dps = next(iter(builds_sorted_by_dps.values()))
        builds_sorted_by_dps = {
            build: (round(dps), f"{dps / max_dps:.1%}")
            for build, dps in builds_sorted_by_dps.items()
        }
        return builds_sorted_by_dps

    def get_builds_against_squishies(
        self,
        god: God,
        must_include_item_names: List[str],
        build_size: int = 6,
    ):
        return self.get_builds(
            scenario=squishy,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )

    def get_builds_against_tanks(
        self,
        god: God,
        must_include_item_names: List[str],
        build_size: int = 6,
    ):
        return self.get_builds(
            scenario=tank,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )

    def get_builds_against_two_scenarios(
        self,
        scenario1: Scenario,
        scenario2: Scenario,
        god: God,
        must_include_item_names: List[str],
        build_size: int = 6,
    ):
        builds1 = self.get_builds(
            scenario=scenario1,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )
        builds2 = self.get_builds(
            scenario=scenario2,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )

        builds = {}
        for build, (dps2, percentile2) in builds2.items():
            dps1, percentile1 = builds1[build]
            avg_percentile = (
                float(percentile1[:-1]) / 100 + float(percentile2[:-1]) / 100
            ) / 2
            builds[build] = (avg_percentile, percentile1, dps1, percentile2, dps2)

        builds_sorted_by_percentile = sorted(
            builds.items(), key=lambda x: x[1][0], reverse=True
        )
        builds_sorted_by_percentile = {
            build: (f"{avg_percentile:.1%}", percentile1, dps1, percentile2, dps2)
            for build, (
                avg_percentile,
                percentile1,
                dps1,
                percentile2,
                dps2,
            ) in builds_sorted_by_percentile
        }
        return builds_sorted_by_percentile

    def get_builds_against_squishies_and_tanks(
        self, god: God, must_include_item_names: List[str], build_size: int = 6
    ):
        return self.get_builds_against_two_scenarios(
            scenario1=squishy,
            scenario2=tank,
            god=god,
            must_include_item_names=must_include_item_names,
            build_size=build_size,
        )
