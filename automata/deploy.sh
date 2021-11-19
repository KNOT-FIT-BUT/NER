#!/bin/bash

F_PREFIX_FOR_ENTITY_ID=q_

usage()
{
  echo "Usage: ./deploy.sh --lang <language> -u [<login>] [--dev]"
  echo ""
  echo -e "\t-h --help              Show this message and exit"
  echo -e "\t--lang=<language>      Select language version to work with"
  echo -e "  -Q --entity-id       Automata pointer will be entity id (usually wikidata Q-identifier) instead of line number."
  echo -e "\t-u [<login=${USER}>]   Upload (deploy) automata to webstorage via given login (default current user)"
  echo -e "\t--dev                  Development mode (upload to separate space to prevent forming a new production version of automata))"
  echo ""
}

DEPLOY=false
POINTER_AS_ENTITY_ID=false

if test $# -eq 0
then
  usage
  exit
fi

while [ "$1" != "" ]; do
  PARAM=`echo $1 | awk -F= '{print $1}'`
  VALUE=`echo $1 | awk -F= '{print $2}'`
  case $PARAM in
    -h | --help)
      usage
      exit
    ;;
    --lang)
      LANG=$VALUE
    ;;
    -Q | --entity-id)
      POINTER_AS_ENTITY_ID=true
    ;;
    -u)
      DEPLOY=true
      VALUE=`echo $2`
      if test "${VALUE}" != "" -a "${VALUE:0:1}" != "-"
      then
        DEPLOY_USER=$VALUE
        shift
      else
        DEPLOY_USER=$USER
      fi
    ;;
    --dev)
      DEPLOY_DEV_SUBDIR=dev
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
  >&2 echo "ERROR: Unspecified language."
  usage
  exit 2
fi


if $DEPLOY
then  
  # Change directory to outputs
  DIR_LAUNCHED=`dirname "${0}"`
  if test "${DIR_LAUNCHED::1}" != "/"
  then
    DIR_LAUNCHED=`readlink -f "${DIR_LAUNCHED}"`
  fi
  DIR_WORKING="${DIR_LAUNCHED}/outputs/${LANG}"
  cd "${DIR_WORKING}" 2>/dev/null

  if test $? != 0
  then
    >&2 echo "ERROR: Unknown language or missing output files."
    usage
    exit 3
  fi

  DEPLOY_VERSION=`cat VERSIONS.json | grep -Po '"KB":\s*"[^"]*"' | sed -E "s/\"KB\":\s*\"([^\"]+)\"/\1/" | tr -d '\n\r '`
  DEPLOY_CONNECTION="${DEPLOY_USER}@minerva3.fit.vutbr.cz"
  DEPLOY_BASENAME="ATM_${DEPLOY_VERSION}"
  DEPLOY_FOLDER_BASE="/mnt/knot/www/NAKI_CPK/${DEPLOY_DEV_SUBDIR}/NER_ML_inputs/Automata/ATM_${LANG}/${DEPLOY_BASENAME}"
  
  rm -rf deploy 2>/dev/null
  
  echo "Preparing output files to deploy..."
  mkdir -p deploy/automata
  mkdir -p deploy/debug_files
  mkdir -p deploy/tmp

  find * -not -type d -not -path "deploy/*" -execdir cp "{}" ./deploy/tmp ";"

  cd deploy/tmp

  if test "${POINTER_AS_ENTITY_ID}" = true
  then
    ATM_PREFIX=${F_PREFIX_FOR_ENTITY_ID}
  fi

  echo "mv \"${ATM_PREFIX}*automata*.dct\" ../automata/"
  mv ${ATM_PREFIX}*automata*.dct ../automata/
  mv VERSIONS.json ../automata/
  # Remove any remaining automata (existing previous wikidata Q-automata if standard mode was launched or any existing
  # previous standard automata if wikidata Q-automata mode was launched) to avoid upload these files to debug_files.
  rm -f *.dct
  mv * ../debug_files/
  
  cd ..
  
  DEPLOY_FILE_AUTOMATA="${DEPLOY_BASENAME}.tar.gz"
  DEPLOY_FILE_DEBUG_FILES="${DEPLOY_BASENAME}-debug_files.tar.gz"
  echo "Packing automata files to ${DEPLOY_FILE_AUTOMATA}"
  tar -czvf "${DEPLOY_FILE_AUTOMATA}" -C automata . 2>&1 | sed 's/^/  * /'
  echo "Packing automata debug files to ${DEPLOY_FILE_DEBUG_FILES}"
  tar -czvf "${DEPLOY_FILE_DEBUG_FILES}" debug_files 2>&1 | sed 's/^/  * /'
  
  echo "Creating new folder: ${DEPLOY_FOLDER_BASE}"
  ssh "${DEPLOY_CONNECTION}" "mkdir -p \"${DEPLOY_FOLDER_BASE}\""
  echo "Upload automata to ${DEPLOY_FOLDER_BASE}"
  scp "${DEPLOY_FILE_AUTOMATA}" "${DEPLOY_CONNECTION}:${DEPLOY_FOLDER_BASE}"
  echo "Upload automata debug files to ${DEPLOY_FOLDER_BASE}"
  scp "${DEPLOY_FILE_DEBUG_FILES}" "${DEPLOY_CONNECTION}:${DEPLOY_FOLDER_BASE}"
  echo "Unpacking automata in ${DEPLOY_FOLDER_BASE}"
  ssh "${DEPLOY_CONNECTION}" "cd \"${DEPLOY_FOLDER_BASE}\"; tar -xvf \"${DEPLOY_FILE_AUTOMATA}\"" 2>&1 | sed 's/^/  * /'
  echo "Unpacking automata debug files in ${DEPLOY_FOLDER_BASE}"
  ssh "${DEPLOY_CONNECTION}" "cd \"${DEPLOY_FOLDER_BASE}\"; tar -xvf \"${DEPLOY_FILE_DEBUG_FILES}\"" 2>&1 | sed 's/^/  * /'
  echo "Change symlink of \"new\" to this latest version of automata"
  ssh "${DEPLOY_CONNECTION}" "cd \"${DEPLOY_FOLDER_BASE}\"; cd ..; ln -sfT \"${DEPLOY_BASENAME}\" new"

  cd "${DIR_WORKING}"
  rm -rf deploy 2>/dev/null
  cd "${DIR_LAUNCHED}"
fi
