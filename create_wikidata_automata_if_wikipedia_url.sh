#!/bin/bash

usage()
{
  echo "Usage: ./create_wikidata_automata_if_wikipedia_url.sh --lang=<language> -k <KB path> [--common-only] [-u [<login>]] [-c | --clean-cached] [--dev] [--log]"
  echo ""
  echo -e "  -h --help"
  echo -e "  --common-only        Create common automata only (otherwise it creates all automatas including autocomplete, lowercase and uri also)"
  echo -e "  --lang=${DEFAULT_LANG}    Create automata for given langueage."
  echo -e "  -u [<login>]         Upload (deploy) automata to webstorage via given login (login \"${USER}\" is used by default)."
  echo -e "  -c --clean-cached    Do not use previously created cached files (usable for same version of KB only)."
  echo -e "  -k <KB path>         Local KB version (do not download it from distribuition storage)"
  echo -e "  --dev                Development mode (upload to separate space to prevent forming a new production version of automata)"
  echo -e "  --log                Log to create_automata.sh.stdout, create_automata.sh.stderr and create_automata.sh.stdmix"
  echo ""
}

DEPLOY=false
ATM_ARGS=()
DEPLOY_ARGS=()

while [ "$1" != "" ]; do
  PARAM=`echo $1 | awk -F= '{print $1}'`
  VALUE=`echo $1 | awk -F= '{print $2}'`
  case $PARAM in
    -h | --help)
      usage
      exit
    ;;
    --lang)
      LANG=${VALUE,,}
      ATM_ARGS+=("${1}")
    ;;
    -k)
      KB_FILE=$2
      shift
    ;;
    -u)
      DEPLOY=true
      LOGIN=$2
      if test "${LOGIN:0:1}" = "-"
      then
        DEPLOY_USER=`whoami`
      else
        DEPLOY_USER="${LOGIN}"
        shift
      fi
    ;;
    --dev)
      DEPLOY_ARGS+=("--dev")
    ;;
    *)
      ATM_ARGS+=("${1}")
    ;;
  esac
  shift
done


if test -z "${LANG}"
then
  if test -z "${DEFAULT_LANG}"
  then
    >&2 echo "ERROR: Unspecified language."
    usage
    exit 2
  else
    LANG=$DEFAULT_LANG
  fi
else
  if test "${LANG}" == "cz"
  then
    LANG=cs
  fi
fi

if test -t "{KB_FILE}"
then
  >&2 echo "ERROR: Unspecified KB file."
  usage
  exit 3
fi

DIR_LAUNCHED=$PWD
DIR_WORKING=`dirname $(readlink -f "${0}")`

cd "${DIR_WORKING}"
KB_FILE="${DIR_WORKING}/${KB_FILE}"
TMP_KB="./.KB_${LANG}.tsv"

KB_HEAD=`sed '/./!Q' "${KB_FILE}"`
N_SKIP_LINES=$((`echo -e "${KB_HEAD}" | wc -l` + 1))
I_COL_WIKIPEDIA_URL=`echo -e "${KB_HEAD}" | grep "<__generic__>" | tr -s '\t' '\n' | nl -nln | grep "WIKIPEDIA URL" | cut -f1`

rm -f "${TMP_KB}"
tail -n +"${N_SKIP_LINES}" "${KB_FILE}" | grep -P "^([^\t]*\t){$((I_COL_WIKIPEDIA_URL-1))}[^\t]+" > "${TMP_KB}"
echo -e "${KB_HEAD}\n\n" | cat - "${TMP_KB}" | sponge "${TMP_KB}"

ATM_ARGS+=("-k" "${TMP_KB}")
./create_automata.sh "${ATM_ARGS[@]}"
mv "${TMP_KB}" "./automata/outputs/${LANG}/KB_${LANG}.tsv"

if test "${DEPLOY}" == "true"
then
    ./automata/deploy.sh -u ${DEPLOY_USER} "${DEPLOY_ARGS[@]}"
fi

cd "${DIR_LAUNCHED}"
