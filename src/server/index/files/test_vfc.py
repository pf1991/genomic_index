import vcf
from pyfaidx import FastaVariant

samples = vcf.Reader(filename='to_index/ALL.chr1.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz').samples
print(samples)
print(len(samples))

consensus = FastaVariant('hs37d5.fa', 'to_index/ALL.chr1.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz', sample='NA06984', het=True, hom=True)
print(consensus['1'][1:100000])