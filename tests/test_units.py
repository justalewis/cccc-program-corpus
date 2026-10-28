"""Unit tests for the parsing and matching helpers."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "reader"))

def test_split_merged_two_presenters():
    from parse_pdf import split_merged
    out = split_merged("Morgan Gresham", "University of South Florida, St. Petersburg, Jill McCracken, University of South Florida, St. Petersburg", None)
    assert [o[0] for o in out] == ["Morgan Gresham", "Jill McCracken"]

def test_split_merged_leaves_single_entries_alone():
    from parse_pdf import split_merged
    out = split_merged("Jane Doe", "Ohio State University, Columbus, OH", "A Title")
    assert out == [("Jane Doe", "Ohio State University, Columbus, OH", "A Title", None)]

def test_near_name_kinds():
    from near_names import kind
    assert kind("Carrie Leverenz", "Carrie Shively Leverenz") == "middle"
    assert kind("Jim Brown", "James Brown") == "nickname"
    assert kind("Brenda Brueggeman", "Brenda Brueggemann") == "spelling"
    assert kind("Kellie Sharp", "Kellie Sharp-Hoskins") == "surname"
    assert kind("Susan Miller", "Joan Miller") is None

def test_group_names_join_suffix_variants():
    from build_groups import key
    assert key("Black Caucus") == key("Black Caucus Business Meeting")
    assert key("Medical Rhetoric Standing Group (MRSG)") == key("Medical Rhetoric")
    assert key("Council on Basic Writing SIG") != key("Writing Centers")

def test_role_groups():
    from enrich_more import role_group
    assert role_group("Co-Chairs") == "chair" and role_group("Respondents") == "respondent"
    assert role_group("Workshop Facilitators") == "facilitator" and role_group("Speaker(s)") == "speaker"

def test_area_label_cleaning():
    from parse_areas import clean_labels
    areas = {f"A.{i}": "Theory" for i in range(5)}
    areas.update({"B.1": "Thory", "B.2": "Some Book Title", "B.3": "#Pedagogy, #Tech"})
    out = clean_labels(areas)
    assert out["B.1"] == "Theory" and out["B.2"] is None and out["B.3"] is None

def test_pinakes_author_key():
    from link_pinakes import names, printed
    assert printed("Janine Solberg") in names("Janine Solberg; Jane Roe")
    assert printed("Robert J. Topinka") in names("Robert Topinka")

def test_classify_formats():
    from analytics import classify
    assert classify("B.12", None) == "concurrent session" and classify("MW.3", None) == "workshop"
    assert classify("FSIG.4", None) == "group meeting" and classify(None, "Poster") == "poster"
    assert classify(None, "Registration/Exhibit Hall Hours") is None

def test_no_backspace_characters_in_source():
    # a backslash-b typed into a Python string through a shell heredoc becomes a backspace character
    bad = chr(8)
    for folder in ("src", "reader", "tests"):
        for name in os.listdir(os.path.join(ROOT, folder)):
            if name.endswith(".py"):
                assert bad not in open(os.path.join(ROOT, folder, name), encoding="utf-8").read(), name
