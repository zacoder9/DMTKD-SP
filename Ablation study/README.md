
We provide the baseline Bart model as well as the code for our approach. Implementation of other baseline models can be referenced [here](https://github.com/shijx12/KQAPro_Baselines). 

Here, we offer the checkpoint for both the baseline Bart model and our approach, which can be accessed by clicking [here](https://pan.baidu.com/s/1I1XWRNJKmsFn0IwvzcSc5A).
提取码: i77b

Please click the link below to download several checkpoints involved in the train.py file.

[teacher-ckpt-sparql](https://pan.baidu.com/s/14OFcJMKmExUEZJdzzDYDuA)
提取码: y3xr

[teacher-ckpt-dcs](https://pan.baidu.com/s/1QWOrpJetEj73QywBa4qUFg)
提取码: 4n6a

[teacher-ckpt-kopl](https://pan.baidu.com/s/1zTesiNCRAHkrMgpsI0aoNw)
提取码: 8xr6

[transfer-ckpt-sparql](https://pan.baidu.com/s/14onAoT8JeoVB0ooFK9uNZA)
提取码: 5248

[transfer-ckpt-dcs](https://pan.baidu.com/s/1f-_BPWNqlL7xSRn-Ecp4Zw)
提取码: cjk2

We describe the training files for different ablation experiments and offer the checkpoint for ablation studies.

train_single_teacher_sparql.py: only single sparql teacher.

[BART KoPL(single SPARQL teacher) ckpt](https://pan.baidu.com/s/1tAcjGbmXGCtzJCT3eoyEPw?pwd=hyve)
提取码：hyve 


train_single_teacher_dcs.py: only single dcs teacher.   

[BART KoPL(single 𝜆-DCS teacher) ckpt](https://pan.baidu.com/s/1M91ytObWvfVqeRvMkbNPEA?pwd=isr0)
提取码：isr0


train_only_feature.py: only single kopl teacher.

[BART KoPL(Feature-Based Distillation) ckpt](https://pan.baidu.com/s/1o6rIXNbKfILJPp_Ulrf0ZQ?pwd=b424)
提取码：b424 

train_without_kopl.py: only use a SPARQL model and a 𝜆-DCS model as our teacher and delete the teacher model for encoder based guidance self-distillation.

[w/o 𝑇_𝑠𝑒𝑙𝑓 ckpt](https://pan.baidu.com/s/1Fk6YLBkqnB3cx4VAnmfLvQ?pwd=aya7)
提取码：aya7 


train_without_confidence.py: no confidence module.

[w/o 𝐴_𝑐𝑜𝑛𝑓𝑖𝑑𝑒𝑛𝑐𝑒 ckpt](https://pan.baidu.com/s/1_pDbu5_vG27jxWvbb7mz-w?pwd=yfkl)
提取码：yfkl 