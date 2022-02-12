import datetime
import hashlib
import itertools
import json
import os
from typing import *

import requests


class Smite:
    base_url = "https://api.smitegame.com/smiteapi.svc"

    def __init__(self):
        # Smite API stuff.
        self.dev_id = None
        self.auth_key = None
        self.session = None
        # Builds stuff.
        self.all_items = None
        self.starter_items = None
        self.normal_items = None
        self.items = None
        self.all_gods = None

    def get_credentials(self):
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

    def get_items(self):
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
        self.items = self.starter_items | self.normal_items

    def print_passives(self):
        for item_name, item in self.items.items():
            passive = item["ItemDescription"]["SecondaryDescription"]
            if passive:
                print(item_name)
                print(passive)
                print("---")

    def print_stat_descs(self):
        all_stat_descs = set()
        for item in self.items.values():
            stats = item["ItemDescription"]["Menuitems"]
            for stat in stats:
                all_stat_descs.add(stat["Description"])
        for stat_desc in sorted(all_stat_descs):
            print(stat_desc)

    def gen_combinations(
        self, must_include_item_names: List[str] = [], build_size: int = 6
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
                yield must_include_item_names + list(p)
