from dataclasses import dataclass

ATTACK_SPEED_CAP = 2.5
BASE_CRIT_MULTI = 0.75


@dataclass
class Item:
    basic_attack: int = 0
    physical_power: int = 0
    attack_speed: float = 0
    flat_pen: int = 0
    percent_pen: float = 0
    critical_strike_chance: float = 0
    critical_strike_multiplier: float = 0
    yellow_aa_damage: int = 0
    yellow_damage: int = 0
    basic_attack_multiplier: float = 0

    def compute_dps(self, fight_length: float, enemy_prots: int) -> float:
        one_auto_before_crit = self.basic_attack + self.physical_power
        one_auto_after_crit = (
            one_auto_before_crit * (1 - self.critical_strike_chance)
        ) + (
            one_auto_before_crit
            * self.critical_strike_chance
            * (1 + BASE_CRIT_MULTI + self.critical_strike_multiplier)
        )
        one_auto = (
            one_auto_after_crit * (1 + self.basic_attack_multiplier)
            + self.yellow_aa_damage
        )
        capped_attack_speed = max(self.attack_speed, ATTACK_SPEED_CAP)
        damage_before_mitigations = (
            one_auto * capped_attack_speed * fight_length + self.yellow_damage
        )
        enemy_prot_after_pen = max(
            0.0, enemy_prots * (1 - self.percent_pen) - self.flat_pen
        )
        damage_after_mitigations = damage_before_mitigations * (
            100 / (100 + enemy_prot_after_pen)
        )
        dps = damage_after_mitigations / fight_length
        return dps

    @classmethod
    def from_item_raw(cls, item_raw: dict) -> "Item":
        item = cls()
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
        self.critical_strike_chance += other.critical_strike_chance
        self.critical_strike_multiplier += other.critical_strike_multiplier
        self.yellow_aa_damage += other.yellow_aa_damage
        self.yellow_damage += other.yellow_damage
        return self
