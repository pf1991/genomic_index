# bloom_genomic_index
Project to test bloom filters

# Run

```
docker-compose up
```

The web interface can be accessed at http://localhost:8000


# Generate the index

docker-compose up exec index bash

python command_line.py --generate

python command_line.py --index_files



# Notes

Understanding VCF file format:
https://gatkforums.broadinstitute.org/gatk/discussion/1268/what-is-a-vcf-and-how-should-i-interpret-it

Data repository:
ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/

A subset can be created with:
```sh
tabix -h ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr1.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz 1:1-1000000 | vcf-subset  -c HG03279,HG02353,HG00560,HG00657,HG02652,HG02275,HG01432,HG02819,NA19657,HG01676 > out.vcf
```

The url for the ref genome on vcf file can be found at its headers. In our case we used:
ftp://ftp.1000genomes.ebi.ac.uk//vol1/ftp/technical/reference/phase2_reference_assembly_sequence/hs37d5.fa.gz



