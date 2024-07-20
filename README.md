# AOS Parser

This repo contains:

- A parser for the Age of Sigmar 4 faction packs found [here](https://www.warhammer-community.com/warhammer-age-of-sigmar-downloads/)
- The parsed data from each of those PDFs.

The json file for each faction contains almost everything in the PDFs:

- Battle Traits
- Battle Formations
- Heroic Traits
- Artefacts of Power
- Spell/Prayer/Manifestation Lore
- Warscrolls including weapon profiles and abilities.

What is not included:

- The phase that passive abilities activate in (I need to look at parsing the images to get this to work, it's not in the text).
- Anything related to spearhead.

There will undoubtedly be errors where things are a little different, or haven't parsed correctly. I'll be checking over manually
and correcting anything where this is the case. Any improvements/contributions are more than welcome.

License: Feel free to do what you will with this data. I'm not attempting to profit from it, and would love someone to build some
sweet tools so we can all see what we can do in each phase!

Note: Ironjawz/Kruleboyz are combined in the Orruk Warclans faction pack. I just separated these using pdf tools before parsing.
