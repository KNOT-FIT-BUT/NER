#!/bin/bash 

PWD_COPY=$PWD
SCRIPT_DIR=$(dirname $0)

echo $SCRIPT_DIR

INPUTS_DIR=$SCRIPT_DIR/ner/inputs
INPUTS_BACKUP_DIR=$(dirname $INPUTS_DIR)/inputs_backup

TMP_FILE=NER_ML_inputs.tgz

rm -rf $INPUTS_BACKUP_DIR
mv $INPUTS_DIR $INPUTS_BACKUP_DIR

mkdir $INPUTS_DIR
cd $INPUTS_DIR

wget http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/NER_ML_inputs-KB_latest-dct.tgz -O $TMP_FILE
tar -xvf $TMP_FILE 

rm -f $TMP_FILE

cd ..
mv ner_namedict.pkl ner_namedict.pkl.bak 2>/dev/null

cd $PWD_COPY
