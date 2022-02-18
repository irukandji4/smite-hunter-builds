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
    def from_item_raw(cls, item_raw: dict) -> "Item":
        item = cls(passive=passives.get(item_raw["DeviceName"]))
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
        return self


def bluestone_brooch(scenario: Scenario, god: God, build_item: Item):
    pass


def corrupted_bluestone(scenario: Scenario, god: God, build_item: Item):
    pass


def deaths_temper(scenario: Scenario, god: God, build_item: Item):
    pass


def diamond_arrow(scenario: Scenario, god: God, build_item: Item):
    pass


def hunters_cowl(scenario: Scenario, god: God, build_item: Item):
    pass


def leaders_cowl(scenario: Scenario, god: God, build_item: Item):
    pass


def manikin_hidden_blade(scenario: Scenario, god: God, build_item: Item):
    pass


def manikin_mace(scenario: Scenario, god: God, build_item: Item):
    pass


def ornate_arrow(scenario: Scenario, god: God, build_item: Item):
    pass


def atalantas_bow(scenario: Scenario, god: God, build_item: Item):
    pass


def deathbringer(scenario: Scenario, god: God, build_item: Item):
    pass


def dominance(scenario: Scenario, god: God, build_item: Item):
    pass


def evolved_rage(scenario: Scenario, god: God, build_item: Item):
    pass


def evolved_transcendence(scenario: Scenario, god: God, build_item: Item):
    pass


def failnot(scenario: Scenario, god: God, build_item: Item):
    pass


def heartseeker(scenario: Scenario, god: God, build_item: Item):
    pass


def hydras_lament(scenario: Scenario, god: God, build_item: Item):
    pass


def ichaival(scenario: Scenario, god: God, build_item: Item):
    pass


def odysseus_bow(scenario: Scenario, god: God, build_item: Item):
    pass


def qins_sais(scenario: Scenario, god: God, build_item: Item):
    pass


def silverbranch_bow(scenario: Scenario, god: God, build_item: Item):
    pass


def the_crusher(scenario: Scenario, god: God, build_item: Item):
    pass


def the_executioner(scenario: Scenario, god: God, build_item: Item):
    pass


def titans_bane(scenario: Scenario, god: God, build_item: Item):
    pass


def wind_demon(scenario: Scenario, god: God, build_item: Item):
    pass


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
    "Leader's Cowl": Passive(leaders_cowl, 1),
    "Manikin Hidden Blade": Passive(manikin_hidden_blade, 1),
    "Manikin Mace": Passive(manikin_mace, 1),
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
    "Heartseeker": Passive(heartseeker, 1),
    "Hydra's Lament": Passive(hydras_lament, 1),
    "Ichaival": Passive(ichaival, 1),
    "Odysseus' Bow": Passive(odysseus_bow, 1),
    "Qin's Sais": Passive(qins_sais, 1),
    "Shadowsteel Shuriken": None,
    "Silverbranch Bow": Passive(silverbranch_bow, 1),
    "The Crusher": Passive(the_crusher, 1),
    "The Executioner": Passive(the_executioner, 1),
    "Titan's Bane": Passive(titans_bane, 1),
    "Wind Demon": Passive(wind_demon, 1),
}
