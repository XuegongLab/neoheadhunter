import sys
import csv
import getopt
import os
import subprocess
from time import sleep

import logging
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    
logging.basicConfig(format=' bindstab_filter.py %(asctime)s - %(message)s', level=logging.INFO)

cycle = ['|', '/', '-', '\\']
methods = ['cterm', '20s']

def split_file(reader, lines=400):
    from itertools import islice, chain
    tmp = next(reader)
    while tmp!="":
        yield chain([tmp], islice(reader, lines-1))
        try:
            tmp = next(reader)
        except StopIteration:
            return

def write_file(a_list, name):
    textfile = open(name, "w")
    for element in a_list:
        textfile.write(element + "\n")
    textfile.close()
    return

def main(args_input = sys.argv[1:]):
    opts,args=getopt.getopt(args_input,"hi:o:n:b:p:",["input_file","output_folder","netMHCstabpan_path","binding_stability","prefix"])
    input_file =""
    output_folder=""
    netMHCstabpan_path=""
    binding_stability=1
    prefix=""
    USAGE='''
        This script convert annotation result to fasta format file for netMHC
        usage: python bindstab_filter.py -i <input_file> -o <output_folder> -n <netMHCstabpan_path> -b <binding_stability> -p <prefix>
            required argument:
                -i | --input_file : Input file of neoantigens for filter 
                -o | --output_folder : Output folder to store result
                -n | --netMHCstabpan_path : Path to call netMHCstabpan for binding stability (run remote command if begins with ssh:// )
                -b | --binding_stability : Binding stability threshold for neoantigen
                -p | --prefix : Prefix of output file 
    '''
    for opt,value in opts:
        if opt =="h":
            print (USAGE)
            sys.exit(2)
        elif opt in ("-i","--input_file"):
            input_file=value
        elif opt in ("-o","--output_folder"):
            output_folder =value
        elif opt in ("-n","--netMHCstabpan_path"):
            netMHCstabpan_path =value 
        elif opt in ("-b","--binding_stability"):
            binding_stability =value
        elif opt in ("-p","--prefix"):
            prefix =value
    
    logging.info('--binding_stability={}'.format(binding_stability))
    reader = csv.reader(open(input_file), delimiter="\t")
    fields = next(reader)
    #print("Waiting for results from NetMHCStabPan... |", end='')
    sys.stdout.write("Waiting for results from NetMHCStabPan... |")
    binstab_raw_csv = output_folder+"/"+prefix+"_bindstab_raw.csv"
    os.system("rm {}".format(binstab_raw_csv))
    
    if netMHCstabpan_path.startswith("ssh://"):
        netMHCstabpan_parsed_url = urlparse(netMHCstabpan_path)
        logging.info(netMHCstabpan_parsed_url)
        addressport = netMHCstabpan_parsed_url.netloc.split(':')
        assert len(addressport) <= 2
        if len(addressport) == 2:
            address, port = addressport
        else:
            address, port = (addressport[0], 22)
        useraddress = address.split('@')
        assert len(useraddress) <= 2
        if len(useraddress) == 2:
            user, address = useraddress
        else:
            user, address = (netMHCstabpan_parsed_url.username, useraddress[0])
    
    for line in reader:
        print(line)
        hla = line[0]
        hla = hla.replace("*", "")
        
        staging_file =[]
        staging_file.append(line[1])
        stage_pep = output_folder+"/stage.pep"
        write_file(staging_file, stage_pep)
        
        if netMHCstabpan_path.startswith("ssh://"):
            remote_mkdir = " sshpass -p \"$NeohunterRemotePassword\" ssh -p {} {}@{} mkdir -p /tmp/{}/".format(port, user, address, output_folder)
            remote_scp = " sshpass -p \"$NeohunterRemotePassword\" scp -P {} {} {}@{}:/tmp/{}/".format(port, stage_pep, user, address, output_folder)
            remote_argslist = [netMHCstabpan_parsed_url.path, "-ia", "-p", "/tmp/" + stage_pep, "-a", hla]
            remote_exe = " sshpass -p \"$NeohunterRemotePassword\" ssh -p {} {}@{} {} >> {}".format(port, user, address, " ".join(remote_argslist), binstab_raw_csv)
            logging.info(remote_mkdir)
            subprocess.call(remote_mkdir, shell=True)
            logging.info(remote_scp)
            subprocess.call(remote_scp, shell=True)
            logging.info(remote_exe)
            subprocess.call(remote_exe, shell=True)
        else:
            local_argslist = [netMHCstabpan_path, "-ia", "-p", stage_pep, "-a", hla] #, " > ", output_folder+"/"+prefix+"_bindstab_raw.csv"
            local_exe = "{} >> {}".format(" ".join(local_argslist), binstab_raw_csv)
            logging.info(local_exe)
            subprocess.call(local_exe, shell=True)
            
    #args1 = netMHCstabpan_path+" -ia -p "+output_folder+"/stage.pep -a "+ hla+" > "+output_folder+"/"+prefix+"_bindstab_raw.csv"
    # subprocess.call(args1, shell=True)
    
    os.remove(stage_pep)
    sys.stdout.write('\b\b')
    print("OK")

    bind_stab = []
    # stab_reader = csv.reader(open(output_folder+"/bindstab.csv"), delimiter=",")
    with open(output_folder+"/"+prefix+"_bindstab_raw.csv") as f:
        data = f.read()
    nw_data = data.split('-----------------------------------------------------------------------------------------------------\n')
    WT_header = []
    WT_neo = []
    for i in range(len(nw_data)):
        if i%4 == 3:
            wt_pro_name = nw_data[i].strip('\n').split('.')[0]
            WT_header.append(wt_pro_name)
        elif i%4 == 2:
            wt_neo_data = nw_data[i].strip().split('\n')
            # for row in wt_neo_data:
            WT_neo.append(wt_neo_data)
    for i in range(len(WT_neo)):
        for j in range(len(WT_neo[i])):
            # if (WT_neo[i][j].strip().split()[2] == "KAWENFPNV"):
            #     print(WT_neo[i][j].strip().split()[5])
            bind_stab.append(WT_neo[i][j].strip().split()[5])
    fields.append("BindStab")
    with open(output_folder+"/"+prefix+"_candidate_pmhc.csv","w") as f:
        write = csv.writer(f)
        write.writerow(fields)
        i=0
        reader = csv.reader(open(input_file), delimiter="\t")
        next(reader,None)
        for line in reader:
            if (float(bind_stab[i])>=float(binding_stability)):
                line.append(bind_stab[i])
                write.writerow(line)
            else:
                logging.info('The peptide {} has binding_stability={} and is filtered out. '.format(line, bind_stab[i]))
            i+=1
    

if __name__ == '__main__':
    main()