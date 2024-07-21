#!/usr/bin/env python3

import json
import os

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox, LTTextLineHorizontal

BATTLE_TRAITS = "battle_traits"
BATTLE_FORMATIONS = "battle_formations"
HEROIC_TRAITS = "heroic_traits"
ARTEFACTS = "artefacts"
SPELL_LORE = "spell_lore"
PRAYER_LORE = "prayer_lore"
MANIFESTATION_LORE = "manifestation_lore"
WARSCROLL = "warscroll"
UNKNOWN = "unknown"


def parse_pdf(input_file, output_file):
    pages = extract_pages(input_file)
    output = {}
    parsing_warscrolls = False

    for page in pages:
        pt = page_type(page)
        if pt == WARSCROLL:
            if "warscrolls" not in output:
                output["warscrolls"] = []
            output["warscrolls"].append(parse_warscroll(page))
            parsing_warscrolls = True

        elif parsing_warscrolls:
            # If we've been parsing warscrolls (which are always last), and we hit a non-warscroll page,
            # then we've got to the spearhead stuff and we want to bail out.
            break

        elif pt == BATTLE_TRAITS:
            output["battle_traits"] = parse_battle_traits(page)

        elif pt == BATTLE_FORMATIONS:
            output["battle_formations"] = parse_battle_formations(page)

        elif pt == HEROIC_TRAITS or pt == ARTEFACTS:
            output.update(parse_heroic_traits(page))

        elif pt == SPELL_LORE:
            if "spell_lore" not in output:
                output["spell_lore"] = {}
            output["spell_lore"].update(parse_lore(page, "LORE OF"))

        elif pt == PRAYER_LORE:
            if "prayer_lore" not in output:
                output["prayer_lore"] = {}
            output["prayer_lore"].update(parse_lore(page, "PRAYERS"))

        elif pt == MANIFESTATION_LORE:
            if "manifestation_lore" not in output:
                output["manifestation_lore"] = {}
            output["manifestation_lore"].update(parse_lore(page, "MANIFESTATIONS OF"))


    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)


def page_type(page):
    for element in page:
        if not isinstance(element, LTTextBox):
            continue

        if element.y0 < 350:
            continue

        text = element.get_text()
        if "BATTLE TRAITS" in text:
            return BATTLE_TRAITS
        elif "BATTLE FORMATIONS" in text:
            return BATTLE_FORMATIONS
        elif "HEROIC TRAITS" in text:
            return HEROIC_TRAITS
        elif "ARTEFACTS OF POWER" in text:
            return ARTEFACTS
        elif "SPELL LORE" in text:
            return SPELL_LORE
        elif "PRAYER LORE" in text:
            return PRAYER_LORE
        elif "MANIFESTATION LORE" in text:
            return MANIFESTATION_LORE
        elif "WARSCROLL" in text:
            return WARSCROLL

    return UNKNOWN


def parse_battle_traits(page):
    elements = [element for element in page if isinstance(element, LTTextBox)]
    first_ability = find_first_ability(elements)
    return parse_abilities([e for e in elements if e.y1 <= first_ability and e.y0 > 15])


def parse_battle_formations(page):
    elements = [element for element in page if isinstance(element, LTTextBox) and element.y0 > 15]
    elements.sort(key=lambda e: (e.x0 > 150, -e.y0))
    elements = [e.get_text() for e in elements]

    abilities = {}
    current_ability = None
    formation_name = ""
    previous_line = ""

    for text in elements:
        if text_is_start_of_ability(text):
            if current_ability is not None:
                abilities[formation_name] = parse_ability(current_ability[:-1])

            current_ability = [text]
            formation_name = tidy_string(previous_line).title()
            continue

        if current_ability is not None:
            current_ability.append(text)

        previous_line = text

    if current_ability is not None:
        abilities[formation_name] = parse_ability(current_ability)

    return abilities


def parse_heroic_traits(page):
    # These pages may include both heroic traits and artefacts, so we check whether either is included.
    elements = [element for element in page if isinstance(element, LTTextBox) and element.y0 > 15]

    traits, artefacts = None, None
    for e in elements:
        if "HEROIC TRAITS" in e.get_text():
            traits = e.y1
        elif "ARTEFACTS OF POWER" in e.get_text():
            artefacts = e.y1

    if traits is not None and artefacts is None:
        # Whole page is traits
        return {"heroic_traits": parse_abilities(elements)}

    elif artefacts is not None and traits is None:
        # Whole page is artefacts
        return {"artefacts_of_power": parse_abilities(elements)}

    else:
        return {
            "heroic_traits": parse_abilities([e for e in elements if e.y0 > artefacts]),
            "artefacts_of_power": parse_abilities([e for e in elements if e.y1 < artefacts]),
        }


def parse_lore(page, name_str):
    elements = [element for element in page if isinstance(element, LTTextBox) and element.y0 > 15]

    lore_name = ""
    for e in elements:
        if name_str in e.get_text():
            lore_name = tidy_string(e.get_text()).title()
            break

    return {
        lore_name: parse_abilities(elements),
    }


def parse_warscroll(page):
    elements = [element for element in page if isinstance(element, LTTextBox)]

    # We first subdivide the page into the various sections.
    # Characteristics (move, save etc.) are always at the top left of the page
    characteristics = [e for e in elements if e.x1 < 75 and e.y0 > 350]

    # The unit's name is at the top, to the right of the characteristics.
    name = [e for e in elements if (e.x0 + e.x1) > 240 and (e.y0 + e.y1) > 760]

    # Split the rest of the page up accordingly.
    first_ability = find_first_ability(elements, 40) + 3 # Add a little padding to be safe
    weapons = [e for e in elements if e.y1 < 370 and e.y1 > first_ability] 
    abilities = [e for e in elements if e.y0 < first_ability and e.y0 > 40]
    keywords = [e for e in elements if e.y1 < 40]

    move, health, save, control, banishment = parse_characteristics(characteristics)
    warscroll = {
        "name": parse_name(name),
        "move": move,
        "health": health,
        "save": save,
    }
    if control is not None:
        warscroll["control"] = control
    if banishment is not None:
        warscroll["banishment"] = banishment

    warscroll["weapons"] = parse_weapons(weapons)
    warscroll["abilities"] = parse_abilities(abilities),
    warscroll["keywords"] = parse_keywords(keywords)

    return warscroll


Activation_Keywords = [
    "Passive",
    "Once Per Turn",
    "Once Per Battle",
    "Reaction"
]

Phase_Keywords = [
    "Deployment Phase",
    "Start of Battle Round",
    "Start of Any Turn",
    "Start of Your Turn",
    "Start of Enemy Turn",
    "Hero Phase",
    "Movement Phase",
    "Shooting Phase",
    "Charge Phase",
    "Combat Phase",
    "End of Any Turn",
    "End of Your Turn",
    "End of Enemy Turn",
]

def text_is_start_of_ability(text):
    for keyword in Activation_Keywords:
        if keyword in text:
            return True

    for keyword in Phase_Keywords:
        if keyword in text:
            return True

    return False


def find_first_ability(elements, start=0):
    first_ability = start
    for e in elements:
        if text_is_start_of_ability(e.get_text()):
            if e.y1 > first_ability:
                first_ability = e.y1

    return first_ability


def parse_name(elements):
    objs = []
    for e in elements:
        objs.extend([obj for obj in e._objs if isinstance(obj, LTTextLineHorizontal)])

    objs.sort(key=lambda obj: (obj.y0 + obj.y1), reverse=True)
    objs = [obj.get_text().strip() for obj in objs]
    return tidy_string(" ".join([o for o in objs if "WARSCROLL" not in o and "2024" not in o]))


def parse_characteristics(elements):
    """
    Returns a tuple of (Move, Health, Save, Control, Banishment)
    """

    move, health, save, control, banishment = "", "", "", None, None
    
    for element in elements:
        text = "".join(element.get_text().strip().split())
        if "MOVE" in text:
            move = text.removeprefix("MOVE").removesuffix("\"")
            continue

        if "CONTROL" in text:
            control = text.removesuffix("CONTROL")
            continue

        if "NISH" in text:
            banishment = text[:text.index("+")+1]
            continue

        if "+" in text:
            save = text
            continue

        if text.isnumeric():
            health = text
            continue
            
    return move, health, save, control, banishment


def parse_weapons(elements):
    # pdfminer will jumble a load of stuff together if we let it, so we need to drop down to the individual line components.
    all_elements = []
    for e in elements:
        all_elements.extend([obj for obj in e._objs if isinstance(obj, LTTextLineHorizontal)])

    # Try and group the elements into rows. The names can span multiple rows, so we start by looking at the elements in the Hit column
    to_hit = [e for e in all_elements if e.x0 < 140 and e.x1 > 140]
    to_hit.sort(key=lambda e: e.y0, reverse=True)

    weapons = []
    for x in to_hit:
        weapon = [e for e in all_elements if e.y1 > x.y0 and e.y0 < x.y1]
        weapon.sort(key=lambda w: w.x0)
        weapons.append(" ".join([w.get_text() for w in weapon]).replace("\n", ""))

    parsed_weapons = {}
    type = ""
    for line in weapons:
        if "RANGED WEAPONS" in line:
            type = "ranged"
            parsed_weapons["ranged"] = []
            continue
        elif "MELEE WEAPONS" in line:
            type = "melee"
            parsed_weapons["melee"] = []
            continue
        elif type == "":
            # Probably some flavour text at the top of the warscroll, we just ignore
            continue

        # First put the name together
        weapon = {}
        name = []
        ability = []
        stage = "name"
        for word in line.split(" "):
            # Check whether we're moving on to the next step
            if word == "":
                continue

            if stage == "name":
                if type == "ranged" and word.endswith("\""):
                    stage = "attacks"
                    weapon["name"] = tidy_string(" ".join(name))
                    weapon["range"] = word

                elif type == "melee" and word.strip()[-1].isnumeric(): # Just check the last digit for the D6 case
                    stage = "hit"
                    weapon["name"] = tidy_string(" ".join(name))
                    weapon["attacks"] = word

                else:
                    name.append(word)

            elif word.startswith("Anti") or word.startswith("Charge") or word.startswith("Companion") or word.startswith("Crit") or word.startswith("Shoot"):
                ability.append(word)
                stage = "ability"

            elif stage == "attacks":
                weapon["attacks"] = word
                stage = "hit"

            elif stage == "hit":
                weapon["hit"] = word
                stage = "wound"

            elif stage == "wound":
                weapon["wound"] = word
                stage = "rend"

            elif stage == "rend":
                weapon["rend"] = word
                stage = "damage"

            elif stage == "damage":
                weapon["damage"] = word
                stage = "ability"

            elif stage == "ability":
                ability.append(word)

        weapon["ability"] = " ".join(ability)
        parsed_weapons[type].append(weapon)

    return parsed_weapons


def parse_abilities(elements):
    elements.sort(key=lambda e: (e.x0 > 150, -e.y1))
    elements = [e.get_text() for e in elements]

    abilities = []
    current_ability = None
    previous_line = ""

    for text in elements:
        if text_is_start_of_ability(text):
            if current_ability is not None:
                abilities.append(current_ability)

            current_ability = [text]
            if previous_line.strip().isnumeric():
                # We may have missed the command point cost/casting value/chanting value if that was higher than the text.
                current_ability.append(previous_line)

            continue

        if current_ability is not None:
            current_ability.append(text)

        previous_line = text

    if current_ability is not None:
        abilities.append(current_ability)

    return [parse_ability(a) for a in abilities]


def parse_ability(text):
    ability = {}
    stage = "Activation"

    text = "\n".join(text)
    cost = 0

    for line in text.splitlines():
        line = tidy_string(line)

        # Check whether we've moved onto a new stage first
        if "name" not in ability and line.isupper():
            ability["name"] = line
            stage = "Name"
            continue
            
        if ":" in line and line.split(":")[0].isupper():
            split = line.split(":")
            ability["name"] = split[0].title()
            if len(split) > 0:
                ability["description"] = split[1]

            stage = "Name"
            continue

        if line.startswith("Declare:"):
            ability["declare"] = line.removeprefix("Declare: ").replace("\n", "")
            stage = "Declare"
            continue

        if line.startswith("Effect"):
            ability["effect"] = line.removeprefix("Effect: ").replace("\n", "")
            stage = "Effect"
            continue

        if "Keywords" in line:
            ability["keywords"] = []
            stage = "Keywords"
            continue
        
        if stage == "Activation":
            # Check the activation of the ability
            for keyword in Activation_Keywords:
                if keyword in line:
                    ability["activation"] = keyword
                    if "(Army)" in text:
                        ability["once_per_army"] = True
                    break

                    if keyword == "Passive":
                        ability["phases"] = []
    
            # Check the phase of the ability
            for keyword in Phase_Keywords:
                if keyword in line:
                    ability["phases"] = [keyword.replace(" Enemy", "").replace(" Your", "").replace(" Any", "")]
                    if "Your" in line:
                        ability["your_turn_only"] = True
                    elif "Enemy" in line:
                        ability["enemy_turn_only"] = True

            if line.isnumeric():
                cost = int(line)

            if "Reaction" in line:
                # If this is a reaction we check whether there's any more text.
                reaction_to = line.split("Reaction:")
                if len(reaction_to) > 1:
                    ability["reaction_condition"] = reaction_to[1]

                # There may be more on a subsequent line, so we move into reaction mode to capture the code from the next line.
                stage = "Reaction"
                continue

        if stage == "Reaction":
            if "reaction_condition" in ability:
                ability["reaction_condition"] = " ".join([ability["reaction_condition"], line])
            else:
                ability["reaction_condition"] = text

        if stage == "Name":
            if "description" in ability:
                ability["description"] = " ".join([ability["description"], line])
            else:
                ability["description"] = line

        if stage == "Declare":
            ability["declare"] = " ".join([ability["declare"], line])

        if stage == "Effect":
            ability["effect"] = " ".join([ability["effect"], line])

        if stage == "Keywords":
            ability["keywords"].extend(line.split(", "))

    if "keywords" in ability and len(ability["keywords"]) == 0:
        # Sometimes the keywords can be higher than the word Keywords, so we need to extract them from the effect
        idx = ability["effect"].rindex(".")   # We rely on the fact that all effects are sentences. Keywords don't have a . after them.
        ability["keywords"] = [k.strip() for k in ability["effect"][idx+1:].split(",")]
        ability["effect"] = ability["effect"][:idx+1]

    if cost > 0:
        if "keywords" not in ability:
            ability["command_point_cost"] = cost
        elif "Spell" in ability["keywords"]:
            ability["casting_value"] = cost
        elif "Prayer" in ability["keywords"]:
            ability["chanting_value"] = cost
        else:
            ability["command_point_cost"] = cost

    for key in ["name", "description", "declare", "effect", "reaction_condtion"]:
        if key in ability:
            ability[key] = tidy_string(ability[key])

    if "keywords" in ability:
        ability["keywords"] = [k for k in ability["keywords"] if k != ""]

    return ability


def parse_keywords(elements):
    keywords = []

    for element in elements:
        text = element.get_text()
        if "KEYWORDS" in text:
            continue

        keywords.extend(text.strip().split(", "))

    return keywords


def tidy_string(s):
    return s.replace("  ", " "). \
       replace("\u2018", "'"). \
       replace("\u2019", "'"). \
       replace("\u2022", "\n*"). \
       replace("\u00a0", " "). \
       replace("\u2013", "-"). \
       strip()


if __name__ == "__main__":
    input_files = os.listdir("input")
    input_files.sort()
    for input_file in input_files:
        print("Processing", input_file)
        output_file = "output/" + input_file.removesuffix(".pdf") + ".json"
        parse_pdf("input/" + input_file, output_file)
