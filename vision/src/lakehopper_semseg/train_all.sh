#!/bin/bash

DECODERS="${DECODERS:=UNet FCN FPN}"
DECODERS_ARR=($DECODERS)
ENCODERS="${ENCODERS:=MobileNetV2 EfficientNetB3 InceptionResNetV2}"
ENCODERS_ARR=($ENCODERS)

echo "Decoders: ${DECODERS_ARR[*]}"
echo "Encoders: ${ENCODERS_ARR[*]}"

for DECODER in "${DECODERS_ARR[@]}"; do
  for ENCODER in "${ENCODERS_ARR[@]}"; do
    echo "Training with $DECODER and $ENCODER..."
    USE_TPU=True DECODER=$DECODER ENCODER=$ENCODER python3 train.py
    echo "Training with $DECODER and $ENCODER - done."
  done
done
