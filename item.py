import functools
from dataclasses import dataclass
from typing import *


@dataclass
class Scenario:
    # For dps computation.
    fight_length: float
    enemy_prots: int
    spectral_armor: float
    # For item passives.
    enemy_health: int
    approx_aa_cnt: int
    approx_ability_cnt: int
    true_squishy_false_tank: bool


@dataclass
class God:
    # For dps computation.
    aa_stim: float
    aa_stim_length: int
    # For item passives.
    is_failnot_good: bool


ATTACK_SPEED_CAP = 2.5
BASE_CRIT_MULTI = 0.75


@dataclass
class Item:
    basic_attack: int = 0
    physical_power: int = 0
    attack_speed: float = 0
    flat_pen: int = 0
    percent_pen: float = 0
    aa_percent_pen: float = 0
    ability_percent_pen: float = 0
    critical_strike_chance: float = 0
    critical_strike_multiplier: float = 0
    yellow_aa_damage: int = 0
    yellow_ability_damage: int = 0
    basic_attack_multiplier: float = 0
    passive: "Passive | None" = None
    price: int = 0

    def compute_dps(self, fight_length: float, enemy_prots: int) -> float:
        # Auto attacks.
        one_auto_before_crit = self.basic_attack + self.physical_power
        capped_critical_strike_chance = min(self.critical_strike_chance, 1)
        one_auto_after_crit = (
            one_auto_before_crit * (1 - capped_critical_strike_chance)
        ) + (
            one_auto_before_crit
            * capped_critical_strike_chance
            * (1 + BASE_CRIT_MULTI + self.critical_strike_multiplier)
        )
        one_auto = (
            one_auto_after_crit * (1 + self.basic_attack_multiplier)
            + self.yellow_aa_damage
        )
        capped_attack_speed = min(self.attack_speed, ATTACK_SPEED_CAP)
        aa_damage_before_mitigations = one_auto * capped_attack_speed * fight_length
        capped_percent_pen = min(0.4, self.percent_pen)
        enemy_prots_after_pen_against_aa = max(
            0.0,
            enemy_prots * (1 - capped_percent_pen - self.aa_percent_pen)
            - self.flat_pen,
        )
        aa_damage_after_mitigations = aa_damage_before_mitigations * (
            100 / (100 + enemy_prots_after_pen_against_aa)
        )

        # Abilities.
        ability_damage_before_mitigations = self.yellow_ability_damage
        enemy_prots_after_pen_against_abilities = max(
            0.0,
            enemy_prots * (1 - capped_percent_pen - self.ability_percent_pen)
            - self.flat_pen,
        )
        ability_damage_after_mitigations = ability_damage_before_mitigations * (
            100 / (100 + enemy_prots_after_pen_against_abilities)
        )

        # Ta-da.
        dps = (
            aa_damage_after_mitigations + ability_damage_after_mitigations
        ) / fight_length
        return dps

    @classmethod
    def from_item_raw(cls, item_raw: dict, all_items_by_id: dict) -> "Item":
        price = item_raw["Price"]
        child_item_id = item_raw["ChildItemId"]
        while child_item_id != 0:
            child_item = all_items_by_id[child_item_id]
            price += child_item["Price"]
            child_item_id = child_item["ChildItemId"]
        item = cls(passive=passives.get(item_raw["DeviceName"]), price=price)
        for stat in item_raw["ItemDescription"]["Menuitems"]:
            stat_name: str = stat["Description"]
            stat_value: str = stat["Value"]
            match stat_name:
                case "Attack Speed":
                    item.attack_speed += int(stat_value[:-1]) / 100
                case "Basic Attack Damage":
                    item.basic_attack += int(stat_value)
                case "Critical Strike Chance":
                    item.critical_strike_chance += int(stat_value[:-1]) / 100
                case "Physical Critical Strike Chance":
                    item.critical_strike_chance += int(stat_value[:-1]) / 100
                case "Physical Penetration":
                    if stat_value.endswith("%"):
                        item.percent_pen += int(stat_value[:-1]) / 100
                    else:
                        item.flat_pen += int(stat_value)
                case "Physical Power":
                    item.physical_power += int(stat_value)
        return item

    def __iadd__(self, other: "Item"):
        self.basic_attack += other.basic_attack
        self.physical_power += other.physical_power
        self.attack_speed += other.attack_speed
        self.flat_pen += other.flat_pen
        self.percent_pen += other.percent_pen
        self.aa_percent_pen += other.aa_percent_pen
        self.ability_percent_pen += other.ability_percent_pen
        self.critical_strike_chance += other.critical_strike_chance
        self.critical_strike_multiplier += other.critical_strike_multiplier
        self.yellow_aa_damage += other.yellow_aa_damage
        self.yellow_ability_damage += other.yellow_ability_damage
        self.basic_attack_multiplier += other.basic_attack_multiplier
        self.price += other.price
        return self


def bluestone_brooch(scenario: Scenario, god: God, build: Item):
    if scenario.approx_ability_cnt > 0:
        build.yellow_ability_damage += 50 + 0.075 * scenario.enemy_health
        if scenario.approx_ability_cnt > 1:
            build.yellow_ability_damage += 50 + 0.0375 * scenario.enemy_health


def corrupted_bluestone(scenario: Scenario, god: God, build: Item):
    build.yellow_ability_damage += 75 * scenario.approx_ability_cnt
    build.attack_speed += 0.1 * scenario.approx_ability_cnt


def deaths_temper(scenario: Scenario, god: God, build: Item):
    if scenario.true_squishy_false_tank:
        build.basic_attack_multiplier += 0.175


def diamond_arrow(scenario: Scenario, god: God, build: Item):
    if scenario.true_squishy_false_tank:
        build.attack_speed += 0.6


def hunters_cowl(scenario: Scenario, god: God, build: Item):
    build.attack_speed += 0.2


def leaders_cowl(scenario: Scenario, god: God, build: Item):
    build.physical_power = round(build.physical_power * 1.05)


def manikin_hidden_blade(scenario: Scenario, god: God, build: Item):
    if scenario.approx_ability_cnt > 0:
        build.yellow_ability_damage += 0.2 * scenario.enemy_health


def manikin_mace(scenario: Scenario, god: God, build: Item):
    capped_attack_speed = min(build.attack_speed, 2)
    build.yellow_ability_damage += capped_attack_speed * 60


def ornate_arrow(scenario: Scenario, god: God, build: Item):
    stacks = 10 if scenario.true_squishy_false_tank else 5
    build.attack_speed += stacks * 0.0125
    build.critical_strike_chance += stacks * 0.01


def atalantas_bow(scenario: Scenario, god: God, build: Item):
    if scenario.true_squishy_false_tank:
        build.attack_speed += 0.2


def deathbringer(scenario: Scenario, god: God, build: Item):
    build.critical_strike_multiplier += 0.3


def dominance(scenario: Scenario, god: God, build: Item):
    build.aa_percent_pen += 0.15


def evolved_rage(scenario: Scenario, god: God, build: Item):
    build.critical_strike_chance -= 0.06 if scenario.true_squishy_false_tank else 0.09


def evolved_transcendence(scenario: Scenario, god: God, build: Item):
    build.physical_power += 0.03 * 2000


def failnot(scenario: Scenario, god: God, build: Item):
    if god.is_failnot_good:
        build.critical_strike_chance += 0.2


def heartseeker(scenario: Scenario, god: God, build: Item):
    if scenario.approx_ability_cnt == 0:
        return
    capped_power = min(400, build.physical_power)
    scaling_power = max(0, capped_power - 200)
    scaled_percent = 0.03 + 0.03 * (scaling_power / 200)
    build.yellow_ability_damage += scaled_percent * scenario.enemy_health
    for i in range(1, scenario.approx_ability_cnt):
        build.yellow_ability_damage += 0.75 * scaled_percent * scenario.enemy_health


def hydras_lament(scenario: Scenario, god: God, build: Item):
    if scenario.approx_aa_cnt > 0:
        uptime = min(scenario.approx_ability_cnt / scenario.approx_aa_cnt, 1)
        build.basic_attack_multiplier += 0.4 * uptime


def ichaival(scenario: Scenario, god: God, build: Item):
    build.physical_power += ichaival_inner(scenario.approx_aa_cnt)


@functools.lru_cache
def ichaival_inner(approx_aa_cnt: int):
    power_on_each_auto = [0]
    power = 0
    for i in range(1, approx_aa_cnt):
        power = min(30, power + 10)
        power_on_each_auto.append(power)
    return sum(power_on_each_auto) / len(power_on_each_auto)


def odysseus_bow(scenario: Scenario, god: God, build: Item):
    stacks = 1 if scenario.true_squishy_false_tank else 2
    build.yellow_ability_damage += (
        stacks * 2 * (15 + 0.6 * build.basic_attack + build.physical_power)
    )


def qins_sais(scenario: Scenario, god: God, build: Item):
    capped_health = min(2750, scenario.enemy_health)
    scaling_health = max(0, capped_health - 2000)
    scaled_percent = 0.03 + 0.02 * (scaling_health / 750)
    build.yellow_aa_damage += scaled_percent * scenario.enemy_health


def silverbranch_bow(scenario: Scenario, god: God, build: Item):
    overcapped_attack_speed = max(0.0, build.attack_speed - ATTACK_SPEED_CAP)
    build.physical_power += 2 * int(overcapped_attack_speed / 0.02)


def the_crusher(scenario: Scenario, god: God, build: Item):
    build.yellow_ability_damage += scenario.approx_ability_cnt * (
        20 + 0.15 * build.physical_power
    )


def the_executioner(scenario: Scenario, god: God, build: Item):
    build.aa_percent_pen += the_executioner_inner(scenario.approx_aa_cnt)


@functools.lru_cache
def the_executioner_inner(approx_aa_cnt: int):
    pen_on_each_auto = [0]
    pen = 0
    for i in range(1, approx_aa_cnt):
        pen = min(0.28, pen + 0.07)
        pen_on_each_auto.append(pen)
    return sum(pen_on_each_auto) / len(pen_on_each_auto)


def titans_bane(scenario: Scenario, god: God, build: Item):
    build.ability_percent_pen += 0.2


def wind_demon(scenario: Scenario, god: God, build: Item):
    if build.critical_strike_chance == 0 or scenario.approx_aa_cnt == 0:
        return
    aa_cnt_before_crit = round(1 / build.critical_strike_chance)
    aa_cnt_after_crit = max(0, scenario.approx_aa_cnt - aa_cnt_before_crit)
    uptime = aa_cnt_after_crit / scenario.approx_aa_cnt
    build.percent_pen += 0.1 * uptime
    build.attack_speed += 0.1 * uptime


@dataclass
class Passive:
    compute: Callable[[Scenario, God, Item], None]
    phase: int


passives = {
    "Bluestone Brooch": Passive(bluestone_brooch, 1),
    "Corrupted Bluestone": Passive(corrupted_bluestone, 1),
    "Death's Embrace": None,
    "Death's Temper": Passive(deaths_temper, 1),
    "Diamond Arrow": Passive(diamond_arrow, 1),
    "Hunter's Cowl": Passive(hunters_cowl, 1),
    "Leader's Cowl": Passive(leaders_cowl, 40),  # POWER > POWER
    "Manikin Hidden Blade": Passive(manikin_hidden_blade, 1),
    "Manikin Mace": Passive(manikin_mace, 50),  # AS > DMG
    "Ornate Arrow": Passive(ornate_arrow, 1),
    "Asi": None,
    "Atalanta's Bow": Passive(atalantas_bow, 1),
    "Bloodforge": None,
    "Deathbringer": Passive(deathbringer, 1),
    "Brawler's Beat Stick": None,
    "Dominance": Passive(dominance, 1),
    "Evolved Rage": Passive(evolved_rage, 1),
    "Evolved Soul Eater": None,
    "Evolved Transcendence": Passive(evolved_transcendence, 1),
    "Fail-not": Passive(failnot, 1),
    "Heartseeker": Passive(heartseeker, 50),  # POWER > DMG
    "Hydra's Lament": Passive(hydras_lament, 1),
    "Ichaival": Passive(ichaival, 1),
    "Odysseus' Bow": Passive(odysseus_bow, 50),  # POWER > DMG
    "Qin's Sais": Passive(qins_sais, 1),
    "Shadowsteel Shuriken": None,
    "Silverbranch Bow": Passive(silverbranch_bow, 30),  # AS > POWER
    "The Crusher": Passive(the_crusher, 50),  # POWER > DMG
    "The Executioner": Passive(the_executioner, 1),
    "Titan's Bane": Passive(titans_bane, 1),
    "Wind Demon": Passive(wind_demon, 20),  # CRIT > AS, PEN
}
