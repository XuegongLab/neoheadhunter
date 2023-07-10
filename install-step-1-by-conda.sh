#sudo apt install tcsh # is required by netMHCpan-4 /usr/bin/tcsh
# sshpass is required if we want to run netMHC command on a remote server

# note: you can use these mirror channels (i.e., with "-c $conda-forge -c $bioconda -c $pytorch") to speed up installation in China
condaforge="-c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/" # -c conda-forge
bioconda="-c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda/" # -c bioconda
pytorch="-c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/" # -c pytorch

conda=mamba
neoheadhunter=nhh # neoheadhunter

conda install -y mamba -n base
conda create -y -n $neoheadhunter

# Order of packages: common bin, common lib, machine-learning lib, bioinformatics bin, bioinformatics lib 
# note: 
#   pyfasta is replaced by pyfaidx
#   ASNEO requires 'biopython<=1.79' (ASNEO code can be refactored to upgrade biopython)
#   ERGO-II requires pytorch-lightning=0.8, but we will change a few lines of source code in ERGO-II 
#     in the next installation step to make it work with higher versions of pytorch-lightning
#   podman will be used to provide a work-around for https://github.com/FRED-2/OptiType/issues/125
$conda install -y -n $neoheadhunter python=3.10 \
    gcc openjdk parallel perl podman sshpass tcsh \
    perl-carp-assert psutil pyyaml requests-cache zlib \
    pandas pytorch pytorch-lightning scikit-learn xgboost \
    bcftools blast bwa ensembl-vep gatk kallisto mosdepth optitype samtools snakemake star 'star-fusion>=1.11' \
    'biopython<=1.79' pybiomart pyfaidx pysam

conda run -n $neoheadhunter pip install sj2psi # for ASNEO.py
conda run -n $neoheadhunter podman pull quay.io/biocontainers/optitype:1.3.2--py27_3 # work-around for https://github.com/FRED-2/OptiType/issues/125

# The optitype environment should be able to provide a work-around for https://github.com/FRED-2/OptiType/issues/125
# However, it seems that conda and mamba cannot install the obsolete python versions that the previous versions of optitype depend on
# Therefore, we commented out the following 3-4 lines of code
# optitype=optitype_env
# conda create -y -n $optitype
# $conda install -y -n $optitype optitype=1.3.2
# conda env export -n ${optitype} > ${optitype}.freeze.yml &&  conda list -e -n ${optitype} > ${optitype}.requirements.txt

# The following command can be run to generate the freeze and requirement files
# conda env export -n ${neoheadhunter} > freeze.yml &&  conda list -e -n ${neoheadhunter} > requirements.txt

