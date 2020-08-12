#!/usr/bin/env python3

import argparse
import random
import statistics
import sys

from pycldf.dataset import Wordlist

def parse_form_table(dataset):
    """
    Convert the representation of a wordlist returned by pycldf
    into a more convenient form for our purposes - a tuple containing
    a set of languages, a set of meanings and a dictionary mapping
    (language, meaning) pairs to form IDs.
    """
    languages = set()
    meanings = set()
    forms = {}
    cognate_map = {}

    for form in dataset["FormTable"]:
        language = form["Language_ID"]
        languages.add(language)
        meaning = form["Parameter_ID"]
        meanings.add(meaning)
        key = (language,meaning)
        if key not in forms:
            forms[key] = []
        forms[key].append(form["ID"])

    for form in dataset["CognateTable"]:
        form_id = form["Form_ID"]
        cogset_id = form["Cognateset_ID"]
        cognate_map[form_id] = cogset_id

    return languages, meanings, forms, cognate_map

def report(dataset):
    """    
    Print synonymy statistics for a wordlist.
    """    
    languages, meanings, forms, cogmap = parse_form_table(dataset)

    n_langs = len(languages)
    n_meanings = len(meanings)
    n_forms = sum((len(x) for x in forms.values()))
    max_forms = max((len(x) for x in forms.values()))
    synonymy_ratio = n_forms / (n_langs*n_meanings) 

    print("{} languages.".format(n_langs))
    print("{} meanings.".format(n_meanings))
    print("{} forms.".format(n_forms))
    print("{:.4f} synonymy ratio (n_forms / nlangs*n_meanings).".format(synonymy_ratio))
    print("maximum {} forms per language-meaning pair.".format(max_forms))

def _write_new_dataset(directory, old_dataset, forms_to_keep):
   
    new_dataset = Wordlist.in_dir(directory)
    new_dataset.add_component("CognateTable")
    new_dataset.write(
            FormTable = [row for row in old_dataset["FormTable"] if row["ID"] in forms_to_keep],
            CognateTable = [row for row in old_dataset["CognateTable"] if row["Form_ID"] in forms_to_keep],
            )

def kill_random(dataset):
    """
    Remove synonyms from a wordlist entire at random.
    """
    languges, meanings, forms, cogmap = parse_form_table(dataset)
    forms_to_keep = set()
    for synonym_list in forms.values():
        survivor = random.sample(synonym_list, 1)[0]
        forms_to_keep.add(survivor)
    _write_new_dataset('mydataset', dataset, forms_to_keep)

def main():

    # Parse arguments
    parser = argparse.ArgumentParser(description='Remove synonyms from a CLDF wordlist.')
    parser.add_argument("metadata", help="CLDF metadata file.")
    parser.add_argument("--report", action="store_true", help="Display wordlist statistics.")
    parser.add_argument("--random", action="store_true", help="Remove synonyms at random.")
    args = parser.parse_args()

    actions = [args.report, args.random]
    if actions.count(True) > 1:
        print("Can only select one action!")
        sys.exit(1)

    # Load data
    dataset = Wordlist.from_metadata(args.metadata)

    # Take action
    if args.report:
        report(dataset)
    elif args.random:
        kill_random(dataset)
    # Report by default
    else:
        report(dataset)

if __name__ == "__main__":
    main()
