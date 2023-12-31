#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import argparse,collections,csv,getopt,json,logging,math,os,sys
import pandas as pd 

from Bio.SubsMat import MatrixInfo

NA_REP = 'N/A'
#NAN_REP = 'nan' # https://en.wikipedia.org/wiki/NaN#Display
NUM_INFO_INDEXES = 4
INFO_WT_IDX, INFO_MT_IDX, INFO_ET_IDX, INFO_TPM_IDX = tuple(range(NUM_INFO_INDEXES))

#          '12345678901234567890'
ALPHABET = 'ARNDCQEGHILKMFPSTWYV'

# def aaseq2canonical(aaseq): return aaseq.upper().replace('U', 'X').replace('O', 'X')

def col2last(df, colname): return (df.insert(len(df.columns)-1, colname, df.pop(colname)) if colname in df.columns else -1)

def str2str_show_empty(s, empty_str = NA_REP): return (s if s else empty_str)
def str2str_hide_empty(s, empty_str = NA_REP): return (s if (s != empty_str) else '')

def pep_norm(pep):
    ret = []
    for aa in pep:
        #assert aa in ALPHABET, (F'The amino-acid sequence ({toks[2]}) from ({toks}) does not use the alphabet ({ALPHABET})')
        if aa in ALPHABET: ret.append(aa)
        else: ret.append('X')
    if 'X' in ret: logging.warning(F'{pep} contains non-standard amino acid and is replaced by {ret}')
    return ''.join(ret)
    
def alnscore_penalty(sequence, neighbour):
    assert len(sequence) == len(neighbour)
    ret = 0
    for i in range(len(sequence)):
        if sequence[i] != neighbour[i]:
            scoremax = MatrixInfo.blosum62[(sequence[i], sequence[i])]
            ab = (sequence[i], neighbour[i])
            ba = (neighbour[i], sequence[i])
            if ab in MatrixInfo.blosum62:
                score = MatrixInfo.blosum62[ab]
            else:
                score = MatrixInfo.blosum62[ba]
            ret += scoremax - score
    return ret
    
def build_pep_ID_to_seq_info_TPM_dic(fasta_filename):
    """ This function assumes that there is a one-to-one correspondence between peptide and RNA transcript in fasta_filename. """
    etpep_to_mtpep_list_dic = collections.defaultdict(list)
    mtpep_to_wtpep_list_dic = collections.defaultdict(list)
    
    wtpep_to_fpep_list = collections.defaultdict(list)
    mtpep_to_fpep_list = collections.defaultdict(list)
    etpep_to_fpep_list = collections.defaultdict(list)

    fpep_to_fid_list = collections.defaultdict(list)
    fid_to_seqs = {}
    
    with open(fasta_filename) as file:
        for line in file:
            line = line.strip()
            if line.startswith('>'):
                fid = line.split()[0][1:]
                wt_fpep, mt_fpep, tpm = '', '', 0
                for i, tok in enumerate(line.split()):
                    if i > 0 and len(tok.split('=')) == 2:
                        #print(tok)
                        key, val = tok.split('=')
                        if key == 'WT':
                            wt_fpep = val # aaseq2canonical(val)
                        if key == 'MT':
                            mt_fpep = val # aaseq2canonical(val)
                        if key == 'TPM': 
                            tpm = float(val)
                # assert len(wt_fpep) == len(mt_fpep), F'{wt_fpep} == {mt_fpep} failed'
                if len(wt_fpep) != len(mt_fpep) and wt_fpep != '':
                    logging.warning(F'{wt_fpep} and {mt_fpep} (wt and mt fasta peptides) have different lengths, so set wt to empty string. ')
                    wt_fpep = ''
                if '*' in wt_fpep:
                    logging.warning(F'{wt_fpep} (wt fasta peptide) has stop codon (*) in it, so set wt to empty string. ')
                    wt_fpep = ''
            else:
                et_fpep = line # aaseq2canonical(line)
                wt_fpep = pep_norm(wt_fpep)
                mt_fpep = pep_norm(mt_fpep)
                et_fpep = pep_norm(et_fpep)
                assert len(wt_fpep) == 0 or len(wt_fpep) == len(et_fpep)
                assert len(et_fpep) == len(mt_fpep), F'len({et_fpep}) == len({mt_fpep}) failed'
                logging.debug(F'ET={et_fpep} MT={mt_fpep} WT={wt_fpep}')
                for peplen in [7,8,9,10,11,12]:
                    for pepbeg in range(len(et_fpep)):
                        pepend = pepbeg + peplen
                        if pepend <= len(et_fpep):
                            wt_pep = (wt_fpep[pepbeg:pepend] if (len(wt_fpep) > 0) else '')
                            mt_pep = mt_fpep[pepbeg:pepend]
                            et_pep = et_fpep[pepbeg:pepend]
                            etpep_to_mtpep_list_dic[et_pep].append(mt_pep)
                            mtpep_to_wtpep_list_dic[mt_pep].append(wt_pep)
                            if wt_fpep != '': wtpep_to_fpep_list[wt_pep].append(wt_fpep)
                            mtpep_to_fpep_list[mt_pep].append(mt_fpep)
                            etpep_to_fpep_list[et_pep].append(et_fpep)
                fpep_to_fid_list[et_fpep].append(fid)
                assert fid not in fid_to_seqs, F'{fid} is duplicated in {fasta_filename}. '
                # INFO_WT_IDX, INFO_MT_IDX, INFO_ET_IDX, INFO_TPM_IDX (NUM_INFO_INDEXES)
                fid_to_seqs[fid] = (wt_fpep, mt_fpep, et_fpep, tpm) # {'WT': wt_fpep, 'MT': mt_fpep, 'ET': et_fpep, 'TPM': tpm}
    logging.debug(etpep_to_mtpep_list_dic)
    logging.debug(mtpep_to_wtpep_list_dic)
    def dedup_vals(key2vals): return {k : sorted(set(vs)) for (k, vs) in key2vals.items()} # removed duplicated values
    etpep_to_mtpep_list_dic = dedup_vals(etpep_to_mtpep_list_dic)
    mtpep_to_wtpep_list_dic = dedup_vals(mtpep_to_wtpep_list_dic)
    etpep_to_fpep_list = dedup_vals(etpep_to_fpep_list)
    mtpep_to_fpep_list = dedup_vals(mtpep_to_fpep_list)
    wtpep_to_fpep_list = dedup_vals(wtpep_to_fpep_list)
    fpep_to_fid_list = dedup_vals(fpep_to_fid_list)

    return ((etpep_to_mtpep_list_dic, mtpep_to_wtpep_list_dic), # mutation tracing
            (etpep_to_fpep_list, mtpep_to_fpep_list, wtpep_to_fpep_list), # superstring tracing
            (fpep_to_fid_list, fid_to_seqs)) # ID-TPM tracing

# We need (et_subseq -> mt_subseq) (mt_subseq -> wt_subseq) (subseq -> listof_seqs) (seq -> listof_fastaID) (fastaID -> TPM)
# OUT_CSV_HEADER = ['HLA_type', 'MT_pep', 'WT_pep', 'BindAff', 'WT_BindAff', 'BindLevel', 'Identity', 'Quantification']
OUT_HEADER = ['HLA_type', 'ET_pep', 'MT_pep', 'WT_pep', 'ET_BindAff', 'MT_BindAff', 'WT_BindAff', 'BindLevel', 'Identity', 'Quantification', 'PepTrace', 'BIT_DIST']

def netmhcpan_result_to_df(infilename, et2mt_mt2wt_2tup_pep2pep, et_mt_wt_3tup_pep2fpep, fpep2fid_fid2finfo_3tup): 
    # https://stackoverflow.com/questions/35514214/create-nested-dictionary-on-the-fly-in-python
    def fix(f): return lambda *args, **kwargs: f(fix(f), *args, **kwargs)
    etpep_to_mtpep_list_dic, mtpep_to_wtpep_list_dic = et2mt_mt2wt_2tup_pep2pep
    etpep_to_fpep_list, mtpep_to_fpep_list, wtpep_to_fpep_list = et_mt_wt_3tup_pep2fpep
    fpep_to_fid_list, fid2finfo = fpep2fid_fid2finfo_3tup
    #pep_to_fpep_list, fpep_to_fid_list, fid_to_tpm = pep_fpep_fid_tpm_dic_3tup 
    inheader = None
    rows = []
    with open(infilename) as file:
        for line in file:
            if not line.startswith(' '): continue
            # print(line)
            toks = line.strip().split()
            if toks[0] == 'Pos': 
                assert inheader == None or inheader == toks
                inheader = toks
                assert len(inheader) == 17 or len(inheader) == 15, F'The header-line {line} is invalid.'
            else:
                assert (len(toks) == (len(inheader) - 1) or len(toks) == (len(inheader) + 1)), F'The content-line {line} is invalid'
                if len(toks) == (len(inheader) - 1): row = toks + ['NB'] # no-binding
                if len(toks) == (len(inheader) + 1): row = toks[0:(len(inheader) - 1)] + [toks[(len(inheader))]]
                row[2] = pep_norm(row[2])
                rows.append(row)
    print(F'File={infilename} inheader={inheader}')
    df = pd.DataFrame(rows, columns = inheader)
    df.columns = df.columns.str.replace('HLA', 'MHC')
    mtpep_wtpep_fpep_fid_tpm_ddic_json_dflist = []
    mtpep_pipesep_dflist = []
    wtpep_pipesep_dflist = []
    etpep_tpm_dflist = []
    etpep_mhc_to_aff = {}
    #def fid_convert(fid, type1 = 'R', type2 = 'D'):
    #    ts = fid.split('_')
    #    if len(ts) >= 2:
    #        if ts[1].startswith(type1):
    #            ts[1] = type2 + ts[1:]
    #    return '_'.join(ts)
    def fid_is_moltype(fid, moltype):
        ts = fid.split('_')
        return len(ts) >= 2 and ts[1].startswith(moltype)
    
    # def fid_to_dna_rna_equiv_fid(fid): return fid.replace('SNV_R','SNV_D').replace('INS_R', 'INS_D').replace('DEL_R', 'DEL_D').replace('FSV_R', 'FSV_D')
    for identity, etpep, mhc, aff in zip(df['Identity'], df['Peptide'], df['MHC'], df['Aff(nM)']):
        aff = float(aff)
        fids = set(fid for mtpep in etpep_to_mtpep_list_dic[etpep] for fpep in mtpep_to_fpep_list[mtpep] for fid in fpep_to_fid_list[fpep])
        #fids= set(fid for                                             fpep in etpep_to_fpep_list[etpep] for fid in fpep_to_fid_list[fpep])
        not_dna_fids = set(fid for fid in fids if not fid_is_moltype(fid, 'D'))
        not_rna_fids = set(fid for fid in fids if not fid_is_moltype(fid, 'R'))
        # dna_rna_equiv_fids = set(fid_to_dna_rna_equiv_fid(fid) for fpep in etpep_to_fpep_list[etpep] for fid in fpep_to_fid_list[fpep])
        #etpep_tpm = sum(fid_to_tpm[fid] for fid in dna_rna_equiv_fids)
        not_dna_etpep_tpm = sum(fid2finfo[fid][INFO_TPM_IDX] for fid in not_dna_fids) # (if fid2finfo[fid][INFO_MT_IDX] == fid2finfo[fid][INFO_ET_IDX])
        not_rna_etpep_tpm = sum(fid2finfo[fid][INFO_TPM_IDX] for fid in not_rna_fids) # (if fid2finfo[fid][INFO_MT_IDX] == fid2finfo[fid][INFO_ET_IDX])
        etpep_tpm = max((not_dna_etpep_tpm, not_rna_etpep_tpm))
        mtpep_list = []
        wtpep_list = []
        mtpep2wtpeplist = {}
        pep2fidlist = {}
        for mtpep in etpep_to_mtpep_list_dic[etpep]:
            mtpep_list.append(mtpep)
            mtpep2wtpeplist[mtpep] = []
            for wtpep in mtpep_to_wtpep_list_dic[mtpep]:
                wtpep_list.append(wtpep)
                mtpep2wtpeplist[mtpep].append(wtpep)
        for pep in sorted(set([etpep] + mtpep_list + wtpep_list)):
            pep2fidlist[pep] = []
            fpep_list = (etpep_to_fpep_list.get(pep, []) + mtpep_to_fpep_list.get(pep, []) + wtpep_to_fpep_list.get(pep, []))
            # logging.warning(fpep_list)
            for fpep in fpep_list:
                for fid in fpep_to_fid_list[fpep]:
                    pep2fidlist[pep].append(fid)
        mtpep_pipesep_dflist.append(str2str_show_empty('|'.join(sorted(list(set(mtpep_list))))))
        wtpep_pipesep_dflist.append(str2str_show_empty('|'.join(sorted(list(set(wtpep_list))))))
        etpep_tpm_dflist.append(etpep_tpm)
        mtpep_wtpep_fpep_fid_tpm_ddic_json = json.dumps((mtpep2wtpeplist,pep2fidlist), separators=(',', ':'), sort_keys=True).replace('"', "'")
        mtpep_wtpep_fpep_fid_tpm_ddic_json_dflist.append(mtpep_wtpep_fpep_fid_tpm_ddic_json)
        etpep_mhc_to_aff[(etpep, mhc)] = aff
    wtpep_aff_dflist = []
    mtpep_aff_dflist = []
    bit_dist_dflist = []
    for identity, etpep, mhc, aff in zip(df['Identity'], df['Peptide'], df['MHC'], df['Aff(nM)']):
        min_wt_aff = 2**30
        min_mt_aff = 2**30
        min_bit_dist = 2**30
        for mtpep in etpep_to_mtpep_list_dic[etpep]:
            mt_aff = float(etpep_mhc_to_aff.get((mtpep, mhc), 2**30))
            min_mt_aff = min((min_mt_aff, mt_aff))
            bit_dist = alnscore_penalty(mtpep, etpep) * 0.5
            min_bit_dist = min((min_bit_dist, bit_dist))
            for wtpep in mtpep_to_wtpep_list_dic[mtpep]:
                wt_aff = float(etpep_mhc_to_aff.get((wtpep, mhc), 2**30))
                min_wt_aff = min((min_wt_aff, wt_aff))
        if min_wt_aff == 2**30: min_wt_aff = math.nan
        if min_mt_aff == 2**30: min_mt_aff = math.nan
        if min_bit_dist == 2**30: min_bit_dist = math.nan
        wtpep_aff_dflist.append(min_wt_aff)
        mtpep_aff_dflist.append(min_mt_aff)
        bit_dist_dflist.append(min_bit_dist)
    df['ET_pep'] = df['Peptide']
    df['MT_pep'] = mtpep_pipesep_dflist
    df['WT_pep'] = wtpep_pipesep_dflist
    df['ET_BindAff'] = df['Aff(nM)'].astype(float)
    df['MT_BindAff'] = mtpep_aff_dflist
    df['WT_BindAff'] = wtpep_aff_dflist
    df['BIT_DIST'] = bit_dist_dflist
    df['Quantification'] = etpep_tpm_dflist
    df['PepTrace'] = mtpep_wtpep_fpep_fid_tpm_ddic_json_dflist
    df['HLA_type'] = df['MHC']
    df['BindAff'] = df['Aff(nM)'].astype(float)
    # 'BindLevel', 'Identity' are kept as they are
    return df[OUT_HEADER]

def main():
    description = 'This script parses the output of netMHCpan into a tsv file'
    epilog = 'Abbreviations: WT for wild-type, MT for mutant-type, ET for experimental-type (please just ignore ET for now)'
    parser = argparse.ArgumentParser(description = description, epilog = epilog) # formatter_class = argparse.ArgumentDefaultsHelpFormatter is not used    
    parser.add_argument('-f', '--fasta-file',     help = 'fasta file that netMHCpan took as input to generate the netmhcpan-file', required = True)
    parser.add_argument('-n', '--netmhcpan-file', help = 'file containing the output of netMHCpan', required = True)
    parser.add_argument('-o', '--out-tsv-file',   help = F'''output TSV file with the following columns: {', '.join(OUT_HEADER)}''', required = True)
    parser.add_argument('-a', '--binding-affinity-thres', help = F'binding affinity threshold in nanoMolar above which the peptide-MHC is filtered out '
            F'(higher nanoMolar value means lower binding affinity)', required = True, type = float)
    parser.add_argument('-l', '--bind-levels', help = F'comma-separated tokens describing bind levels '
            F'(a combination of SB/WB/NB denoting strong/weak/no binding)', required = False, default = 'SB,WB,NB')
    
    args = parser.parse_args()
    
    et2mt_mt2wt_2tup_pep2pep, et_mt_wt_3tup_pep2fpep, fpep2fid_fid2finfo_3tup = build_pep_ID_to_seq_info_TPM_dic(args.fasta_file) 
    df1 = netmhcpan_result_to_df(args.netmhcpan_file, et2mt_mt2wt_2tup_pep2pep, et_mt_wt_3tup_pep2fpep, fpep2fid_fid2finfo_3tup)
    df2 = df1[(df1['ET_BindAff'] <= args.binding_affinity_thres) 
            & (df1['BindLevel'].isin(args.bind_levels.split(',')))
            & (df1['MT_pep'] != df1['WT_pep']) 
            & (df1['ET_pep'] != df1['WT_pep'])]
    df3 = df2.drop_duplicates(subset=['HLA_type','ET_pep'])
    df3['Agretopicity'] = df3['ET_BindAff'] / df3['WT_BindAff']
    col2last(df3, 'PepTrace')
    df3.to_csv(args.out_tsv_file, header = 1, sep = '\t', index = 0, na_rep = NA_REP) # not NAN_REP # used tsv instead of csv to prevent conflict with min-json encoding
    
if __name__ == '__main__': main()

