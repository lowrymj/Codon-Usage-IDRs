from bioservices import Panther
import re
import os
import argparse


# command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("target_dir", help="directory to store output file(s). Outfile name produced automatically.")
prot_info = parser.add_mutually_exclusive_group(required=True)
prot_info.add_argument("-p", "--prot_info", nargs=3, help="One protein's UniProt ID, PANTHER Family ID, and Taxonomy ID, in that order")
prot_info.add_argument("-i", "--infile", type=argparse.FileType('r'),
                       help="CSV file with one or more sets of UniProt IDs, PANTHER Family IDs, and Taxonomy IDs, in that order")

args = parser.parse_args()
base_dir = args.target_dir
prot_ids = args.prot_info
in_fh = args.infile

# if in_fh wasn't passed, then gene_info was
if in_fh:
    proteins = [line.strip().split(',') for line in in_fh]
else:
    proteins = [prot_ids]


p = Panther()
for prot_list in proteins:
    prot = prot_list[0]
    family = prot_list[1]
    tax_id = prot_list[2]

    # list of dicts; get persistent_ids for alignments we want to keep
    family_msa = p.get_family_msa(family)
    # orthologs of given prot in given org
    ortho = p.get_ortholog(prot, tax_id)

    # if multiple prots from same org used, unmapped might be populated
    if ortho['unmapped']:
        print(f"Unmapped proteins for {prot}: {ortho['unmapped']} \n")
    else:
        print(f"All proteins mapped for {prot}.\n")

    uniprotKB_id = re.compile(r".*?\|UniProtKB=(.*)")
    ortho_mapping = {}  # maps ortholog persistent ids to its respective uid
    # print(len(family_msa))

    # if only one ortholog exists, only a dict is returned; wrap it in list to make it work in loop
    if isinstance(ortho['mapped'], dict):
        ortho['mapped'] = [ortho['mapped']]

    missing_target_persis_id = []
    for x in ortho['mapped']:
        match = re.search(uniprotKB_id, x['target_gene'])
        uid = match.group(1)

        # can be obtained by searching target_gene manually in Panther db... go to end of tree msa
        # make error out if exceeding certain number of errors?
        try:
            pid = x['target_persistent_id']
        except KeyError:
            # pid = input("\nSearch " + uid + " in Panther db and enter Persistent ID from end of Tree: ")
            missing_target_persis_id.append(uid)
            continue

        ortho_mapping[pid] = uid

    # adds the prot of interest to ortho_mapping so its information is included in later analysis and processing
    else:
        uid = x['id']
        pid = x['persistent_id']
        ortho_mapping[pid] = uid

    if missing_target_persis_id:
        print('{} Ortholog(s) Removed Due To Missing Target Persistent ID: '.format(len(missing_target_persis_id))
              + ', '.join(missing_target_persis_id), '\n')

    # get alignments for all orthologs in family (all orthologs in family, but not all prots in family are orthologs)
    orthos_msa = [alignment for alignment in family_msa if alignment['persistent_id'] in ortho_mapping.keys()]
    # print(len(orthos_msa), len(ortho_mapping))

    # write alignment to file; placed in Panther family folder
    fn_base = "_ortholog_msa.txt"
    dir_name = os.path.join(base_dir, family)
    try:
        os.mkdir(dir_name)
    except OSError:
        pass

    file_name = os.path.join(dir_name, prot) + fn_base
    with open(file_name, 'w') as fh:
        for alignment in orthos_msa:
            seq, pid = alignment.items()
            fh.write(">" + ortho_mapping[pid[1]] + "\n")
            fh.write(seq[1] + "\n")

