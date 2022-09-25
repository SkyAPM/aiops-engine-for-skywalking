# GAIA Dataset

**Sample dataset can be downloaded from**

https://github.com/CloudWise-OpenSource/GAIA-DataSet

**We don't host dataset in this repo because of its size and GPL2.0 license.**

**To get the data from source, simply run `make get-data` in the root directory.**

To evaluate the models, the above command will download the dataset and populate each subset of
`Companion_Data` into this directory.

After that, this folder should be the following exact structure:

- sample_data_gaia
  - log
    - log
    - log parsing
    - log semantics anomaly detection
    - named entity recognition (NER)
  - metric_detection
    - ...
  - metric_forcast
    - ...
  - README.md

