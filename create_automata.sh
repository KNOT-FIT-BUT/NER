#!/bin/bash

ATM_BASEDIR="./automata"
DIR_KB="${ATM_BASEDIR}/inputs"

DEFAULT_LANG=cs
LANG=
LOG=false
POINTER_AS_ENTITY_ID=false
ATM_COMMON_ONLY=false

DEPLOY_ARGS=()
ATM_ARGS=()

usage() {
  echo "Usage: ./create_automata.sh --lang=<language> [--common-only] [-c | --clean-cached] [-Q | --entity-id] [-k <KB path>] [-u [<login>]] [--dev] [--log]"
  echo ""
  echo -e "  -h --help"
  echo -e "  --common-only        Create common automata only (otherwise it creates all automatas including autocomplete, lowercase and uri also)"
  echo -e "  --lang=${DEFAULT_LANG}    Create automata for given langueage."
  echo -e "  -u [<login>]         Upload (deploy) automata to webstorage via given login (login \"${USER}\" is used by default)."
  echo -e "  -c --clean-cached    Do not use previously created cached files (usable for same version of KB only)."
  echo -e "  -k <KB path>         Local KB version (do not download it from distribuition storage)"
  echo -e "  -Q --entity-id       Automata pointer will be entity id (usually wikidata Q-identifier) instead of line number."
  echo -e "  --dev                Development mode (upload to separate space to prevent forming a new production version of automata)"
  echo -e "  --log                Log to create_automata.sh.stdout, create_automata.sh.stderr and create_automata.sh.stdmix"
  echo ""
}

download_file() {
  INPUT_SRC=$1
  INPUT_TARGET=$2
  FILE_IS_REQUIRED=$3

  TARGET_DIR=`dirname ${INPUT_TARGET}`
  TARGET_FILE=`basename ${INPUT_TARGET}`

  mkdir -p "${TARGET_DIR}"

  INPUT_SRC="http://knot.fit.vutbr.cz/NER/${INPUT_SRC}"
  ETAG_INPUT_TARGET="${TARGET_DIR}/.${TARGET_FILE}.etag"

  echo "CHECKING of newer version of \"${TARGET_FILE}\"..."
  INPUT_ETAG_REMOTE=`wget -qS --spider --timeout=1 "${INPUT_SRC}" 2>&1 | grep -P "(?s)^\s+ETag" | grep -oP "(?<=\").*(?=\")"`
  INPUT_ETAG_LOCAL=`cat "${ETAG_INPUT_TARGET}" 2>/dev/null`

  if test -z "${INPUT_ETAG_REMOTE}"
  then
    >&2 echo "ERROR while updating \"${TARGET_FILE}\": Network connection problem or unavailable NER storage; or file is not available for selected language (at ${INPUT_SRC})."
    if test "${FILE_IS_REQUIRED}" == false
    then
      return 0
    else
      exit 11
    fi
  fi

  if test "${INPUT_ETAG_REMOTE}" != "${INPUT_ETAG_LOCAL}" || ! test -s "${INPUT_TARGET}"
  then
    echo "DOWNLOADING new version of \"${TARGET_FILE}\"..."
    wget "${INPUT_SRC}" -O "${INPUT_TARGET}" 2>/dev/null
    if test ! $?
    then
      >&2 "ERROR while downloading new version of \"${TARGET_FILE}\""
      exit 12
    fi

    echo -n "${INPUT_ETAG_REMOTE}" > "${ETAG_INPUT_TARGET}"
    echo "Updating of \"${TARGET_FILE}\" WAS SUCCESSFULLY FINISHED"
  else
    echo "File \"${TARGET_FILE}\" IS UP TO DATE"
  fi
  echo
}


while [ "$1" != "" ]; do
  PARAM=`echo $1 | awk -F= '{print $1}'`
  VALUE=`echo $1 | awk -F= '{print $2}'`
  case $PARAM in
    -h | --help)
      usage
      exit
    ;;
    --common-only)
      ATM_COMMON_ONLY=true
    ;;
    --lang)
      LANG=${VALUE,,}
    ;;
    -c | --clean-cached)
      CLEAN_CACHED=true
    ;;
    -k)
      KB_FILE=$2
      shift
    ;;
    -Q | --entity-id)
      POINTER_AS_ENTITY_ID=true
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
    --log)
      LOG=true
    ;;
    *)
      >&2 echo "ERROR: unknown parameter \"$PARAM\""
      usage
      exit 1
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


if $LOG; then
  rm -f create_automata.sh.fifo.stdout create_automata.sh.fifo.stderr create_automata.sh.fifo.stdmix
  mkfifo create_automata.sh.fifo.stdout create_automata.sh.fifo.stderr create_automata.sh.fifo.stdmix

  cat create_automata.sh.fifo.stdout | tee create_automata.sh.stdout > create_automata.sh.fifo.stdmix &
  cat create_automata.sh.fifo.stderr | tee create_automata.sh.stderr > create_automata.sh.fifo.stdmix &
  cat create_automata.sh.fifo.stdmix > create_automata.sh.stdmix &
  exec > create_automata.sh.fifo.stdout 2> create_automata.sh.fifo.stderr
fi

DIR_LAUNCHED=$PWD
DIR_WORKING=`dirname $(readlink -f "${0}")`

cd "${DIR_WORKING}"

DIR_INPUTS="${DIR_KB}/${LANG}"

if test "${ATM_BASEDIR::1}" != "/"
then
  ATM_BASEDIR="${DIR_WORKING}/${ATM_BASEDIR}"
fi

if test "${KB_FILE}" != ""
then
  KB_FILE_GIVEN="${KB_FILE}"
  if test "${KB_FILE::1}" != "/"
  then
    KB_FILE="${DIR_LAUNCHED}/${KB_FILE}"
  fi

  if ! test -f "${KB_FILE}"
  then
    >&2 echo "ERROR: KB file \"${KB_FILE_GIVEN}\" (\"${KB_FILE}\") does not exist - please check given path."
    exit 10
  fi
else
  if test "${DIR_KB::1}" != "/"
  then
    DIR_KB="${DIR_WORKING}/${DIR_KB}"
  fi

  download_file "stable/${LANG}/latest/KB.tsv" "${DIR_KB}/KB.tsv" true
fi

echo "DOWNLOADING other input files..."
mkdir -p "${DIR_INPUTS}"

FILES_TO_DOWNLOAD="${LANG}_media.wc ${LANG}_stop_list.lst ${LANG}_allow_list.lst ${LANG}_freq_terms.lst"
for INFILE in $FILES_TO_DOWNLOAD
do
  FILE_PATH="${DIR_INPUTS}/${INFILE}"
  download_file "inputs/automata/${LANG}/${INFILE}" "${FILE_PATH}" false
done

if test "${CLEAN_CACHED}" = true
then
  ATM_ARGS+=("--clean-cached")
fi

if test "${POINTER_AS_ENTITY_ID}" = true
then
  ATM_ARGS+=("--entity-id")
  DEPLOY_ARGS+=("--entity-id")
fi

if test "${ATM_COMMON_ONLY}" != true
then
  ATM_ARGS+=("-a")
fi

echo "LAUNCHING automata creation"

${ATM_BASEDIR}/create_cedar.sh --lang=${LANG} -k "${KB_FILE}" "${ATM_ARGS[@]}"

if test "${DEPLOY}" == "true"
then
  ${ATM_BASEDIR}/deploy.sh -u ${DEPLOY_USER} "${DEPLOY_ARGS[@]}"
fi

cd "${DIR_LAUNCHED}"

echo "===== FINISHED ====="
