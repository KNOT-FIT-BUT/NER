#!/bin/bash

DICTS_BASEDIR="./dictionaries"
DIR_KB="${DICTS_BASEDIR}/inputs"
KB_ETAG_FILE=.KB.etag

DEFAULT_LANG=cs
LANG=
LOG=false

usage()
{
  echo "Usage: create_dicts.sh --lang=<language> [-u [<login>]] [-c | --clean-cached]"
  echo ""
  echo -e "  -h --help"
  echo -e "  --lang=${DEFAULT_LANG}    Create dictionaries / automatas for given langueage."
  echo -e "  -u [<login>]         Upload (deploy) KB to webstorage via given login (login \"${USER}\" is used by default)."
  echo -e "  -c --clean-cached    Do not use previously created cached files (usable for same version of KB only)."
  echo -e "  --dev                Development mode (upload to separate space to prevent forming a new production version of automata)"
  echo -e "  --log                Log to create_dicts.sh.stdout, create_dicts.sh.stderr and create_dicts.sh.stdmix"
  echo ""
}


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
    ;;
    -c | --clean-cached)
      CLEAN_CACHED=false
    ;;
    -u)
      DEPLOY=true
      LOGIN=$2
      if test "${LOGIN:0:1}" = "-"
      then
        DEPLOY_USER=`whoami`
      else
        DEPLOY_USER=$2
        shift
      fi
    ;;
    --dev)
      DEPLOY_ARGS="--dev"
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
  rm -f create_dicts.sh.fifo.stdout create_dicts.sh.fifo.stderr create_dicts.sh.fifo.stdmix
  mkfifo create_dicts.sh.fifo.stdout create_dicts.sh.fifo.stderr create_dicts.sh.fifo.stdmix

  cat create_dicts.sh.fifo.stdout | tee create_dicts.sh.stdout > create_dicts.sh.fifo.stdmix &
  cat create_dicts.sh.fifo.stderr | tee create_dicts.sh.stderr > create_dicts.sh.fifo.stdmix &
  cat create_dicts.sh.fifo.stdmix > create_dicts.sh.stdmix &
  exec > create_dicts.sh.fifo.stdout 2> create_dicts.sh.fifo.stderr
fi

DIR_LAUNCHED=$PWD
DIR_WORKING=`dirname $(readlink -f "${0}")`

cd "${DIR_WORKING}"

if test "${DICTS_BASEDIR::1}" != "/"
then
  DICTS_BASEDIR="${DIR_WORKING}/${DICTS_BASEDIR}"
fi

if test "${DIR_KB::1}" != "/"
then
  DIR_KB="${DIR_WORKING}/${DIR_KB}"
fi


mkdir -p "${DIR_KB}"


KB_SRC="http://knot.fit.vutbr.cz/NAKI_CPK/NER_ML_inputs/KB/KB_${LANG}/new/KB.tsv"
KB_FILE="${DIR_KB}/KB.tsv"
KB_ETAG_FILE="${DIR_KB}/${KB_ETAG_FILE}"
echo "CHECKING of newer version of KB..."
KB_ETAG_REMOTE=`wget -qS --spider ${KB_SRC} 2>&1 | grep -P "(?s)^\s+ETag" | grep -oP "(?<=\").*(?=\")"`
KB_ETAG_LOCAL=`cat "${KB_ETAG_FILE}" 2>/dev/null`

if ! $_ETAG_REMOTE
then
  >&2 echo "ERROR: Network connection problem or unavailable CPK storage."
  exit 10
fi

if test "$KB_ETAG_REMOTE" != "$KB_ETAG_LOCAL" || ! test -s "${KB_FILE}"
then
  echo "DOWNLOADING new version of KB..."
  wget "${KB_SRC}" -O "${KB_FILE}" 2>/dev/null
  if test ! $?
  then
    >&2 "ERROR while downloading new version of KB"
    exit 11
  fi

  echo -n "${KB_ETAG_REMOTE}" > ${KB_ETAG_FILE}
  echo "KB UPDATE WAS SUCCESSFULLY FINISHED"
else
  echo "KB IS UP TO DATE"
fi
echo

echo "LAUNCHING dictionaries creation"

${DICTS_BASEDIR}/create_cedar.sh -a --lang=${LANG} -k "${KB_FILE}"

if $DEPLOY
then
  ${DICTS_BASEDIR}/deploy.sh -u ${DEPLOY_USER} ${DEPLOY_ARGS}
fi

cd "${DIR_LAUNCHED}"
