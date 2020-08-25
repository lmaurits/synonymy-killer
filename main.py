#!/usr/bin/env python3

import argparse
import collections
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

def write_new_dataset(directory, old_dataset, forms_to_keep):
   
    new_dataset = Wordlist.in_dir(directory)
    new_dataset.add_component("LanguageTable")
    new_dataset.add_component("CognateTable")
    new_dataset.write(
            LanguageTable = [row for row in old_dataset["LanguageTable"]],
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
    return forms_to_keep

def kill_minimum_cognates(dataset):
    return _kill_minimax_cognates(dataset, "min")

def kill_maximum_cognates(dataset):
    return _kill_minimax_cognates(dataset, "max")

def _kill_minimax_cognates(dataset, mode="min"):
    languages, meanings, forms, cogmap = parse_form_table(dataset)
    forms_to_keep = set()
    cognates = {}
    for meaning in meanings:
        cognate_class_counts = collections.Counter()
        for lang in languages:
            key = (lang,meaning)
            cognates[key] = [cogmap.get(f, "?") for f in forms.get(key, "?")]
            for c in cognates[key]:
                if c != "?":
                    cognate_class_counts[c] += 1
        # Divide languages into easy and hard cases
        easy_langs = [l for l in languages if len(cognates[(l, meaning)]) < 2]
        hard_langs = [l for l in languages if l not in easy_langs]
        # Make easy assignments
        attested_cognates = set()
        for lang in easy_langs:
            key = (lang,meaning)
            if not cognates[key]:
                cognates[key] = "?"
            elif len(cognates[key]) == 1:
                cognates[key] = cognates[key].pop()
                attested_cognates.add(cognates[key])
        # Make hard assignments
        for lang in hard_langs:
            key = (lang,meaning)
            options = [(cognate_class_counts[c], c) for c in cognates[key]]
            # Sort cognates from rare to common if we want to maximise cognate
            # class count, or from common to rare if we want to minimise it.
            options.sort(reverse = mode == "min")
            # Preferentially assign a cognate which has already been
            # assigned if we're trying to minimise, or one which has
            # not if we're trying to maximise.
            for n, c in options:
                if (mode == "min" and c in attested_cognates) or (mode == "max" and c not in attested_cognates):
                    cognates[key] = c
                    break
            # Otherwise just pick the most/least frequent cognate.
            else:
                cognates[key] = options[0][1]
            attested_cognates.add(cognates[key])
        # Translate the cognate class to keep to a random representative form
        for lang in languages:
            key = (lang,meaning)
            if not key in forms:
                continue
            if cognates[key] == "?":
                synonym_list = forms[key]
                survivor = random.sample(synonym_list, 1)[0]
                forms_to_keep.add(survivor)
            else:
                for f in forms[key]:
                    if cogmap[f] == cognates[key]:
                        forms_to_keep.add(f)
                        break

    return forms_to_keep

def main():

    # Parse arguments
    parser = argparse.ArgumentParser(description='Remove synonyms from a CLDF wordlist.')
    parser.add_argument("metadata", help="CLDF metadata file.")
    parser.add_argument("--maxcog", action="store_true", help="Remove synonyms to maximise cognate class count.")
    parser.add_argument("--mincog", action="store_true", help="Remove synonyms to minimise cognate class count.")
    parser.add_argument("--report", action="store_true", help="Display wordlist statistics.")
    parser.add_argument("--random", action="store_true", help="Remove synonyms at random.")
    args = parser.parse_args()

    actions = [args.maxcog, args.mincog, args.report, args.random]
    if actions.count(True) > 1:
        print("Can only select one action!")
        sys.exit(1)

    # Load data
    dataset = Wordlist.from_metadata(args.metadata)

    # Take action
    if args.report:
        report(dataset)
        return
    elif args.random:
        forms_to_keep = kill_random(dataset)
    elif args.mincog:
        forms_to_keep = kill_minimum_cognates(dataset)
    elif args.maxcog:
        forms_to_keep = kill_maximum_cognates(dataset)
    # Report by default
    else:
        report(dataset)
        return

    # Save results
    write_new_dataset('mydataset', dataset, forms_to_keep)

if __name__ == "__main__":
    main()
