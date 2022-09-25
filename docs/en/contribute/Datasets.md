# Get a range of common datasets for testing and development

At the root of project, run `make get-dataset name=<name>` to get them,
the datasets will be extracted to the `assets/datasets` folder.

Use the following `names` to download the batch of the datasets you need:

1. `gaia`: the [GAIA](https://github.com/CloudWise-OpenSource/GAIA-DataSet) dataset.
   - 4+ GB with log, trace and metric data.
2. `log_s`: small [LogHub](https://github.com/logpai/loghub) datasets.
   1. SSH.tar.gz: (Server)
   2. Hadoop.tar.gz: (Distributed system)
   3. Apache.tar.gz: (Server)
   4. HealthApp.tar.gz: (Mobile application)
   5. Zookeeper.tar.gz: (Distributed system)
   6. HPC.tar.gz: (Supercomputer)
3. `log_m`: medium [LogHub](https://github.com/logpai/loghub) datasets.
   1. Android.tar.gz = 1,555,005 logs (183MB Mobile system)
   2. BGL.tar.gz = 4,747,963 logs (700MB Supercomputer)
   3. Spark.tar.gz = 33,236,604 logs (2.7GB Distributed system)
4. `log_l`: large [LogHub](https://github.com/logpai/loghub) datasets.
   1. HDFS_2.tar.gz = 71,118,073 logs (16GB Distributed system)
   2. Thunderbird.tar.gz = 211,212,192 logs (30GB Supercomputer)

**Note large dataset require substantial disk space and memory to extract**

## To remove the datasets/zip/tar files

If you want to keep all zip/tar files after extracting, pass additional `save=True`
to `make get-dataset name=log_m save=True` .

If you want to remove all datasets, run `make prune-dataset`

