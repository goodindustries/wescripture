#!/usr/bin/env python3
"""
Expand things.json from 36 to 60+ scripture objects/symbols.
Adds entries with stub data; christ_connection will be generated separately.
"""

import json
from pathlib import Path

THINGS_PATH = Path(__file__).resolve().parent.parent / "library" / "entities" / "things.json"

NEW_THINGS = [
    {
        "id": "thing:title_of_liberty",
        "name": "Title of Liberty",
        "variants": ["captain moroni's flag", "torn coat", "in memory of our God"],
        "wikipedia_title": "Title of Liberty",
        "desc": "Banner raised by Captain Moroni inscribed with a covenant to defend freedom and faith",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:jaredite_barges",
        "name": "Jaredite barges",
        "variants": ["barges of the Jaredites", "tight like unto a dish"],
        "wikipedia_title": "Jaredite",
        "desc": "Eight sealed vessels built by the Jaredites to cross the great waters to the promised land",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:plates_of_ether",
        "name": "Plates of Ether",
        "variants": ["Jaredite record", "twenty-four gold plates"],
        "wikipedia_title": "Book of Ether",
        "desc": "Twenty-four gold plates containing the record of the Jaredite civilization found by the people of Limhi",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:brazen_serpent",
        "name": "Brazen serpent",
        "variants": ["bronze serpent", "Nehushtan", "serpent of brass"],
        "wikipedia_title": "Nehushtan",
        "desc": "Bronze serpent on a pole raised by Moses in the wilderness; looking upon it healed the Israelites of snakebite",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:noahs_ark",
        "name": "Noah's ark",
        "variants": ["the ark", "ark of Noah"],
        "wikipedia_title": "Noah's Ark",
        "desc": "Vessel built by Noah to preserve life through the great flood; a type of salvation through covenant",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:rainbow",
        "name": "Rainbow",
        "variants": ["bow in the cloud", "sign of the covenant"],
        "wikipedia_title": "Rainbow in the Bible",
        "desc": "Sign of the Noahic covenant placed in the cloud as God's promise to never again destroy the earth by flood",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:coat_of_many_colors",
        "name": "Coat of many colors",
        "variants": ["Joseph's coat", "ornamented robe", "coat of many pieces"],
        "wikipedia_title": "Coat of many colours",
        "desc": "Robe given to Joseph by his father Jacob, symbolizing favor and foreshadowing Christ's rejected but exalted servant",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:paschal_lamb",
        "name": "Paschal lamb",
        "variants": ["passover lamb", "lamb without blemish", "passover sacrifice"],
        "wikipedia_title": "Korban Pesach",
        "desc": "The unblemished lamb slain at Passover whose blood protected Israel; the central type of Christ as the Lamb of God",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:burning_incense",
        "name": "Incense altar",
        "variants": ["golden altar", "altar of incense", "sweet incense"],
        "wikipedia_title": "Altar of incense",
        "desc": "The golden altar in the tabernacle where incense was offered morning and evening, typifying intercessory prayer",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:living_water",
        "name": "Living water",
        "variants": ["water of life", "fountain of living waters", "river of life"],
        "wikipedia_title": "Living water",
        "desc": "Symbol used by Christ in John 4 for the Holy Spirit and eternal life; rooted in Ezekiel's temple vision",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:bread_of_life",
        "name": "Bread of life",
        "variants": ["manna from heaven", "true bread", "I am the bread of life"],
        "wikipedia_title": "Bread of Life Discourse",
        "desc": "Christ's declaration in John 6 identifying himself as the true manna, the bread that gives eternal life",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:oil_lamps",
        "name": "Oil and lamps",
        "variants": ["ten virgins", "wise and foolish virgins", "lamp trimmed and burning"],
        "wikipedia_title": "Parable of the Ten Virgins",
        "desc": "Parable of the ten virgins whose lamps and oil typify readiness for Christ's coming and the Holy Spirit",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:talents",
        "name": "Talents",
        "variants": ["parable of the talents", "the five talents"],
        "wikipedia_title": "Parable of the talents",
        "desc": "Parable in which servants are given varying sums to invest, teaching stewardship and accountability before Christ",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:birthright_blessing",
        "name": "Birthright blessing",
        "variants": ["patriarchal blessing", "first-born right", "double portion"],
        "wikipedia_title": "Birthright (Judaism)",
        "desc": "The covenant inheritance passed to the firstborn son, typifying Christ's role as the firstborn of every creature",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:pillar_of_cloud",
        "name": "Pillar of cloud",
        "variants": ["cloud of glory", "cloud by day fire by night", "shekinah"],
        "wikipedia_title": "Pillar of cloud and fire",
        "desc": "Divine presence that guided Israel as a cloud by day and fire by night, typifying the Holy Ghost as guide",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:baptismal_font",
        "name": "Baptismal font",
        "variants": ["font", "oxen font", "molten sea", "laver of brass"],
        "wikipedia_title": "Baptismal font",
        "desc": "Basin of water used for baptism; in temples, stands on twelve oxen representing the twelve tribes",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:endowment",
        "name": "Temple endowment",
        "variants": ["endowment", "garment of the holy priesthood", "initiatory"],
        "wikipedia_title": "Temple endowment",
        "desc": "Sacred ordinance received in LDS temples that clothes the recipient in priestly garments and instructs in the plan of salvation",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:abrahamic_covenant",
        "name": "Abrahamic covenant",
        "variants": ["Abrahamic covenant", "covenant of Abraham", "promise to Abraham"],
        "wikipedia_title": "Abrahamic covenant",
        "desc": "God's covenant with Abraham promising posterity, land, and that all nations would be blessed through his seed — fulfilled in Christ",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:sealing_ordinance",
        "name": "Sealing ordinance",
        "variants": ["eternal marriage", "sealing", "bound in heaven", "celestial marriage"],
        "wikipedia_title": "Sealing (Mormonism)",
        "desc": "Temple ordinance that binds families for eternity through the sealing power of the Melchizedek Priesthood",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:still_small_voice",
        "name": "Still small voice",
        "variants": ["still small voice", "the voice of the Spirit", "a gentle whisper"],
        "wikipedia_title": "Still small voice",
        "desc": "The manner in which the Lord spoke to Elijah after earthquake and fire at Horeb; a type of the Spirit's quiet witness",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:dove",
        "name": "Dove",
        "variants": ["dove of peace", "Holy Ghost as dove", "dove descending"],
        "wikipedia_title": "Dove as symbol",
        "desc": "At Christ's baptism the Holy Ghost descended in the form of a dove; also Noah's dove signaling the end of the flood",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:scepter",
        "name": "Scepter",
        "variants": ["rod of iron as scepter", "the scepter shall not depart from Judah"],
        "wikipedia_title": "Sceptre",
        "desc": "Symbol of royal authority; in Genesis 49:10 the scepter shall not depart from Judah until Shiloh (Christ) come",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:scroll",
        "name": "Scroll",
        "variants": ["sealed book", "book of the lamb", "little book"],
        "wikipedia_title": "Scroll",
        "desc": "In Revelation 5 only the Lamb was found worthy to open the seven-sealed scroll — typifying Christ's exclusive authority over history",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:prodigal_son",
        "name": "Prodigal son",
        "variants": ["lost son", "parable of the prodigal son"],
        "wikipedia_title": "Parable of the Prodigal Son",
        "desc": "Parable in Luke 15 portraying God as the waiting father who runs to embrace the returning sinner — type of Atonement mercy",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
    {
        "id": "thing:brother_of_jared_stones",
        "name": "Stones of the Brother of Jared",
        "variants": ["sixteen small stones", "touched by the finger of God", "transparent stones"],
        "wikipedia_title": "Brother of Jared",
        "desc": "Sixteen molten transparent stones brought to the Lord by the Brother of Jared; the Lord touched them to provide light — type of faith bringing light from Christ",
        "related_people": [], "related_places": [], "related_scriptures": [], "doc_ids": [],
        "excerpts": []
    },
]


def main():
    things = json.loads(THINGS_PATH.read_text(encoding="utf-8"))
    existing_ids = {t["id"] for t in things}

    added = 0
    for new_thing in NEW_THINGS:
        if new_thing["id"] not in existing_ids:
            things.append(new_thing)
            added += 1
            print(f"  + {new_thing['name']}")
        else:
            print(f"  = already exists: {new_thing['name']}")

    THINGS_PATH.write_text(
        json.dumps(things, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nTotal things: {len(things)} (+{added} new)")


if __name__ == "__main__":
    main()
