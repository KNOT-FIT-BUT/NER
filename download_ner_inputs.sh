#!/bin/bash

set -e

PWD_COPY=$PWD
SCRIPT_DIR=$(dirname $0)

echo $SCRIPT_DIR

INPUTS_DIR=$SCRIPT_DIR/ner_lib/inputs
INPUTS_BACKUP_DIR=$(dirname $INPUTS_DIR)/inputs_backup

TMP_FILE=NER_ML_inputs.tgz

[ -d "$INPUTS_BACKUP_DIR" ] && rm -r "$INPUTS_BACKUP_DIR"
[ -d "$INPUTS_DIR" ] && mv "$INPUTS_DIR" "$INPUTS_BACKUP_DIR"

# <languages>
downloadNerInputs() {
	local language="${1?}"
	local url="${2?}"
	
	mkdir -p "${INPUTS_DIR}/${language}"
	pushd "${INPUTS_DIR}/${language}"
	wget -c "${url}" -O "${TMP_FILE}"
	tar -xvf "${TMP_FILE}"
	rm -f "${TMP_FILE}"
	popd
	
	echo
}

downloadNerInputs 'cz' 'http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/NER_ML_inputs-KB_latest-dct.tgz'
downloadNerInputs 'en' 'http://athena3.fit.vutbr.cz/kb/latest/NAKI_CPK/ner_inputs.tgz'
# </languages>

cd $PWD_COPY
