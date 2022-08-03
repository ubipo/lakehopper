## TPU

Creating:

EU, vm:
```
gcloud alpha compute tpus tpu-vm create lakehopper-semseg-eu-vm --zone=europe-west4-a --accelerator-type='v3-8' --version='tpu-vm-tf-2.9.1-v4'
```

EU, node:
```
gcloud compute tpus create lakehopper-semseg-eu-node --zone=europe-west4-a --accelerator-type='v3-8' --version='2.9.1'
```

US
```
gcloud alpha compute tpus tpu-vm create lakehopper-semseg-us --zone=us-central1-f --accelerator-type='v2-8' --version='tpu-vm-tf-2.9.1-v4'
```

US, node:
```
gcloud compute tpus create lakehopper-semseg-us-node --zone=us-central1-f --accelerator-type='v2-8' --version='2.9.1'
```


Starting:
EU
```
gcloud alpha compute tpus tpu-vm start lakehopper-semseg-eu
```

US
```
gcloud alpha compute tpus tpu-vm start lakehopper-semseg-us
```

