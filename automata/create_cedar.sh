#!/bin/bash

# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vut.cz

export LC_ALL="C.UTF-8"

# saved values
KB_WORKDIR=$PWD
DIR_LAUNCHED=`dirname "${0}"`

# default values
KB="inputs/KB.tsv"
KB_GIVEN=false
ATM_LOWERCASE=false
ATM_URI=false
CEDAR=false
DARTS=false
ATM_ALL=false
ATM_COMMON=true
ATM_AUTOCOMPLETE=false
DIR_INPUTS=inputs
DIR_OUTPUTS=outputs
LANG=
ATM_TYPES_AUTOCOMPLETE=(p l x)
CLEAN_CACHED=false
PROCESSES=`nproc`
POINTER_AS_ENTITY_ID=false
F_PREFIX_FOR_ENTITY_ID=q_

#=====================================================================
# nastavovani parametru prikazove radky

usage()
{
  echo "Usage: ./create_cedar.sh [-h] [--all|--autocomplete|-l|-u] [-c] [-d] [-I ${DIR_INPUTS}] [-O ${DIR_OUTPUTS}] [-p ${PROCESSES}] [-k ${KB}] --lang=<language>"
  echo ""
  echo -e "\t-h --help"
  echo -e "\t-a --all           Create common, autocomplete, lowercase and uri automata (otherwise without any parameters, it creates common automata only)"
  echo -e "\t--lang=<language>"
  echo -e "\t--autocomplete     Create autocomplete automata only"
  echo -e "\t-l --lowercase"
  echo -e "\t-u --uri"
  echo -e "\t-c --cedar"
  echo -e "\t-d --darts (default if none of cedar and darts were specified)"
  echo -e "\t-k --knowledge-base=$KB"
  echo -e "\t--clean-cached     Do not use previously created cached files (usable for same version of KB only)."
  echo -e "\t-p --processes=${PROCESSES}     Numer of processes for multiprocessing pool purposes."
  echo -e "\t-I --indir=${DIR_LAUNCHED}/${DIR_INPUTS}"
  echo -e "\t-O --outdir=${DIR_LAUNCHED}/${DIR_OUTPUTS}"
  echo -e "\t-Q --entity-id     Automata pointer will be entity id (usually wikidata Q-identifier) instead of line number."
  echo ""
}


getGitBasedVersion()
{
  _OLDPWD=$PWD
  cd $1

  VERSION=`git rev-parse --short HEAD 2>/dev/null`
  if test "${?}" -eq 0 && test "$PWD" == "`git rev-parse --show-toplevel`"
  then
    if ! test -z "`git status --short --untracked-files=no`"
    then
      VERSION="${VERSION}_dirty_`date \"+%Y%m%d-%H%M%S\"`"
    fi
  else
    VERSION="nogit_`date \"+%Y%m%d-%H%M%S\"`"
  fi
  cd ${_OLDPWD}

  echo $VERSION
}


run() {
  >&2 echo -e "[`date \+\"%F %T\"`]\tRunning command: ${@}"
  eval "${@}"
}


makeAutomata() {
  F_NAMELIST=$1
  F_AUTOMATA=$2
  F_NAMELIST_FILTERED="${F_NAMELIST}.filtered"
  ./filter_namelist.sh "${KB}" "${F_NAMELIST}" > "${F_NAMELIST_FILTERED}"
  ../figa/figav1.0 -d "${F_NAMELIST_FILTERED}" -n -w "${F_AUTOMATA}"
}


makeCommonAutomata() {
  EXT=$1

  if "${POINTER_AS_ENTITY_ID}" = true
  then
    FILE_PREFIX=${F_PREFIX_FOR_ENTITY_ID}
  fi

  F_NAMELIST_BASE="${DIR_OUTPUTS}/${FILE_PREFIX}namelist"
  F_ATM_BASE="${DIR_OUTPUTS}/${FILE_PREFIX}automata"

  if $ATM_COMMON
  then
    makeAutomata "${F_NAMELIST_BASE}" "${F_ATM_BASE}$EXT"
  fi
  if $ATM_LOWERCASE
  then
    makeAutomata "${F_NAMELIST_BASE}_lower" "${F_ATM_BASE}-lower$EXT"
  fi
  if $ATM_URI
  then
    makeAutomata "${F_NAMELIST_BASE}_uri" "${F_ATM_BASE}-uri$EXT"
  fi
}

cutoutConfidence() {
  F_CONFIDENCE=${1}

  rm -rf "${F_CONFIDENCE}"

  HAS_CONFIDENCE=`cat "${KB}" | grep -P "^<__stats__>.*CONFIDENCE$" | wc -l`
  if test ${HAS_CONFIDENCE} \> 0
  then
    cat "${KB}" | sed '0,/^$/d' | awk -F $'\t' '{print $(NF)}' > "${F_CONFIDENCE}"
  fi
}


clearAtmChoice() {
  ATM_COMMON=false
  ATM_AUTOCOMPLETE=false
  ATM_LOWERCASE=false
  ATM_URI=false
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
            LANG=$VALUE
            ;;
        -a | --all)
            ATM_ALL=true
            ;;
        --autocomplete)
            clearAtmChoice
            ATM_AUTOCOMPLETE=true
            ;;
        -l | --lowercase)
            clearAtmChoice
            ATM_LOWERCASE=true
            ;;
        -u | --uri)
            clearAtmChoice
            ATM_URI=true
            ;;
        -c | --cedar)
            CEDAR=true
            ;;
        -d | --darts)
            DARTS=true
            ;;
        -k | --knowledge-base)
            if [ "$PARAM" = "-k" ]; then
              if [ "$2" = "" ]; then
                usage
                exit 1
              else
                VALUE="$2"
                shift
              fi
            fi

            KB=$VALUE
            KB_GIVEN=true
            ;;
        --clean-cached)
            CLEAN_CACHED=true
            ;;
        -p | --processes)    # -n does not work
            if [ "$PARAM" = "-p" ]; then
              VALUE=$2
              shift
            fi
            PROCESSES=$VALUE
            ;;
        -I | --indir)
            if [ "$PARAM" = "-I" ]; then
              VALUE=$2
              shift
            fi
            DIR_INPUTS=$VALUE
            ;;
        -O | --outdir)
            if [ "$PARAM" = "-O" ]; then
              VALUE=$2
              shift
            fi
            DIR_OUTPUTS=$VALUE
            ;;
        -Q | --entity-id)
            POINTER_AS_ENTITY_ID=true
            ;;
        *)
            echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 2
            ;;
    esac
    shift
done


if $ATM_ALL # Insurance for both --all and --autocomplete parameters are given togerher.
then
  ATM_COMMON=true
  ATM_AUTOCOMPLETE=true
  ATM_URI=true
  ATM_LOWERCASE=true
fi


if ! $CEDAR
then
  DARTS=true
fi

if test "${LANG}" == ""
then
  echo "ERROR: Language was not specified." >&2
  usage
  exit 4
else
  LANG=${LANG,,}
  if test "${LANG}" == "cz"
  then
    LANG=cs
  fi
fi

if [ ! -f "$KB" ]; then
  echo "ERROR: Could not found KB on path: ${KB}" >&2
  if ! $KB_GIVEN ; then
    echo "Did you forget to set the parameter \"-k\"? (Default \"${KB}\" was used.)\n" >&2

    usage
  fi
  exit 3
fi

DIR_OUTPUTS="${DIR_OUTPUTS}/${LANG}"

#=====================================================================
# zmena spousteci cesty na tu, ve ktere se nachazi create_cedar.sh
cd "${DIR_LAUNCHED}"
# ale soucasne je treba zmenit cestu ke KB, jinak bychom problem posunuli jinam
if [[ "${KB:0:1}" != "/" ]]
then
  KB="${KB_WORKDIR}/${KB}"
fi

# cesta pro import modulů do Python skriptů
export PYTHONPATH=../../:$PYTHONPATH

make -C ..

mkdir -p "${DIR_OUTPUTS}"

VERSION_FILE="${DIR_OUTPUTS}/VERSIONS.json"
KB_VERSION=`head -n 1 "${KB}" | sed -E 's/^VERSION=//' | tr -d '\n\r '`
echo "---------------------------------"
echo "KB version: ${KB_VERSION}"

if test "${LANG}" == "cs"
then
  NAMEGEN_VERSION=`getGitBasedVersion "../libs/namegen/"`
  echo "NAMEGEN version: ${NAMEGEN_VERSION}"
fi

ATM_VERSION=`getGitBasedVersion ".."`
echo "AUTOMATA version: ${ATM_VERSION}"
echo "---------------------------------"

cat > "${VERSION_FILE}" << EOF
{
  "KB": "${KB_VERSION}",
  "CZECH NAMEGEN": "${NAMEGEN_VERSION}",
  "AUTOMATA": "${ATM_VERSION}"
}
EOF


#=====================================================================
F_ENTITIES_WITH_TYPEFLAGS="entities_with_typeflags_${KB_VERSION}.tsv"
F_ENTITIES_TAGGED_INFLECTIONS="entities_tagged_inflections_${KB_VERSION}.tsv"
# temporary files to avoid skipping of generating target files, when generating failed or aborted
F_TMP_ENTITIES_WITH_TYPEFLAGS="_${F_ENTITIES_WITH_TYPEFLAGS}"
F_TMP_ENTITIES_TAGGED_INFLECTIONS="_${F_ENTITIES_TAGGED_INFLECTIONS}"

F_ENTITIES_WITH_TYPEFLAGS="${DIR_OUTPUTS}/${F_ENTITIES_WITH_TYPEFLAGS}"
F_ENTITIES_TAGGED_INFLECTIONS="${DIR_OUTPUTS}/${F_ENTITIES_TAGGED_INFLECTIONS}"
F_ENTITIES_TAGGED_INFLECTIONS_INVALID="${F_ENTITIES_TAGGED_INFLECTIONS}.invalid"
F_TMP_ENTITIES_WITH_TYPEFLAGS="${DIR_OUTPUTS}/${F_TMP_ENTITIES_WITH_TYPEFLAGS}"
F_TMP_ENTITIES_TAGGED_INFLECTIONS="${DIR_OUTPUTS}/${F_TMP_ENTITIES_TAGGED_INFLECTIONS}"

# Skip generating some files if exist, because they are very time consumed
if test "${CLEAN_CACHED}" = "true" || ! test -s "${F_ENTITIES_WITH_TYPEFLAGS}"; then
  python3 get_entities_with_typeflags.py -k "$KB" --lang ${LANG} | awk -F"\t" 'NF>2{key = $1 "\t" $2 "\t" $3; a[key] = a[key] (a[key] ? " " : "") $4;};END{for(i in a) print i "\t" a[i]}' > "${F_TMP_ENTITIES_WITH_TYPEFLAGS}"
  RETVAL_ENTITIES_WITH_TYPEFLAGS="${PIPESTATUS[0]}"
  if test "${RETVAL_ENTITIES_WITH_TYPEFLAGS}" -gt 0
  then
    >&2 echo "STOPPED due to some error occurs while getting entities with typeflags."
    exit 10
  fi
  mv "${F_TMP_ENTITIES_WITH_TYPEFLAGS}" "${F_ENTITIES_WITH_TYPEFLAGS}" 2>/dev/null
fi

if ! test -s "${F_ENTITIES_WITH_TYPEFLAGS}"
then
  >&2 echo "STOPPED due to missing output file or empty output file of getting entities with typeflags."
  exit 11
fi

if ! test -s "${F_ENTITIES_TAGGED_INFLECTIONS}" || test `stat -c %Y "${F_ENTITIES_TAGGED_INFLECTIONS}"` -lt `stat -c %Y "${F_ENTITIES_WITH_TYPEFLAGS}"` || test "${CLEAN_CACHED}" = true; then
  python3 get_entities_tagged_inflections.py -l ${LANG} -o "${F_TMP_ENTITIES_TAGGED_INFLECTIONS}" -i "${F_ENTITIES_WITH_TYPEFLAGS}"
  if test $? != 0
  then
    >&2 echo "STOPPED due to some error occurs while getting tagged inflections of entities."
    exit 20
  fi
  if test -f "${F_TMP_ENTITIES_TAGGED_INFLECTIONS}"
  then
    mv "${F_TMP_ENTITIES_TAGGED_INFLECTIONS}" "${F_ENTITIES_TAGGED_INFLECTIONS}"
  fi
fi

if ! test -s "${F_ENTITIES_TAGGED_INFLECTIONS}"
then
  if test "${LANG}" == "en" && ! test -f "${F_ENTITIES_TAGGED_INFLECTIONS}"
  then
    >&2 echo "WARNING: Missing output file or empty output file of getting tagged inflections of entities - skipping for language \"${LANG}\" (entities tagged inflection was not implemented for language \"${LANG}\")."
  else
    >&2 echo "STOPPED due to missing output file or empty output file of getting tagged inflections of entities."
    exit 21
  fi
fi

KB2NAMELIST_ARGS=()
if test "${CLEAN_CACHED}" = true
then
  KB2NAMELIST_ARGS+=("--clean-cached")
fi

if test "${POINTER_AS_ENTITY_ID}" = true
then
  KB2NAMELIST_ARGS+=("--entity-id")
fi

SCRIPT_KB2NAMELIST="python3 KB2namelist.py -l ${LANG} -k ${KB} -t \"${F_ENTITIES_TAGGED_INFLECTIONS}\" -I \"${DIR_INPUTS}\" -O \"${DIR_OUTPUTS}\" -n ${PROCESSES} ${KB2NAMELIST_ARGS[@]}"
F_CONFIDENCE="${DIR_OUTPUTS}/KB_confidence"

EXTS=()
if $CEDAR
then
  EXTS+=(".ct")
fi
if $DARTS
then
  EXTS+=(".dct")
fi

#=====================================================================
# uprava stoplistu (kapitalizace a razeni)
F_STOPLIST_BASE="${DIR_OUTPUTS}/stop_list"
FOUT_STOPLIST="${F_STOPLIST_BASE}.all.sorted"
if $ATM_ALL || ! $ATM_URI
then
  FIN_STOPLIST="${DIR_INPUTS}/${LANG}/${LANG}_stop_list.lst"
  if test -f "${FIN_STOPLIST}"
  then
    python3 get_morphological_forms.py < "${FIN_STOPLIST}" | sort -u > "${F_STOPLIST_BASE}.var"
    cp "${F_STOPLIST_BASE}.var" "${F_STOPLIST_BASE}.all"
    sed -e 's/\b\(.\)/\u\1/g' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
    tr 'a-z' 'A-Z' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
    tr 'A-Z' 'a-z' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
    sort -u "${F_STOPLIST_BASE}.all" > "${FOUT_STOPLIST}"
  else
    >&2 echo "WARNING: Input stoplist file \"${FIN_STOPLIST}\" was not found => continue without stoplist."
  fi
fi


if test "${POINTER_AS_ENTITY_ID}" = true
then
  F_INTEXT_NAMELIST_BASE_PREFIX="${F_PREFIX_FOR_ENTITY_ID}"
fi

# parsovanie confidence hodnot do samostatneho suboru
cutoutConfidence "${F_CONFIDENCE}"

if $ATM_COMMON || $ATM_LOWERCASE || $ATM_URI
then
  #=====================================================================
  # vytvoreni seznamu klicu entit v KB, pridani fragmentu jmen a prijmeni entit a zajmen
  F_INTEXT_BASE="${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}intext"
  if $ATM_COMMON
  then
    run "${SCRIPT_KB2NAMELIST} | tr -s ' ' > \"${F_INTEXT_BASE}\""
  fi
  if $ATM_LOWERCASE
  then
    run "${SCRIPT_KB2NAMELIST} -d | tr -s ' ' > \"${F_INTEXT_BASE}_lower\""
  fi
  if $ATM_URI
  then
    run "${SCRIPT_KB2NAMELIST} -u > \"${F_INTEXT_BASE}_uri\""
  fi

  #=====================================================================
  # redukcia duplicit, abecedne zoradenie entit
  # odstranovani slov ze stop listu
  F_NAMELIST_BASE="${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}namelist"
  if $ATM_ALL || ! $ATM_URI
  then
    fname_suffixes=()

    if $ATM_COMMON
    then
      fname_suffixes+=("")
    fi
    if $ATM_LOWERCASE
    then
      fname_suffixes+=("_lower")
    fi

    for fname_suffix in "${fname_suffixes[@]}"
    do
      CMD="python3 uniq_namelist.py -s \"${FOUT_STOPLIST}\""
      if test -f "${F_CONFIDENCE}"
      then
        CMD+=" -c ${F_CONFIDENCE}"
      fi
      run "${CMD} < \"${F_INTEXT_BASE}${fname_suffix}\" > \"${F_NAMELIST_BASE}${fname_suffix}\""
    done
  fi
  if $ATM_URI
  then
    python3 uniq_namelist.py -s "${FOUT_STOPLIST}" < "${F_INTEXT_BASE}_uri" > "${F_NAMELIST_BASE}_uri"
  fi

  #=====================================================================
  # vytvoreni konecneho automatu
  for ext in "${EXTS[@]}"
  do
    makeCommonAutomata "${ext}"
  done

  #=====================================================================
  # smazani pomocnych souboru

  #rm -f names
  #rm -f fragments
  #rm -f intext intext_lower intext_uri
  #rm -f stop_list.all stop_list.var stop_list.all.sorted
  #rm -f namelist namelist_lower namelist_uri
  #rm -f KB_confidence
fi


if ${ATM_AUTOCOMPLETE}
then
  F_INTEXT_AUTO="${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}intext_auto"
  run "${SCRIPT_KB2NAMELIST} -a | tr -s ' ' | grep -v -e \"[^;]N\" > \"${F_INTEXT_AUTO}\""
  cat "${F_INTEXT_AUTO}" | grep -P "^person:" | sed -r 's/^person:\t//' > "${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}p_intext"
  cat "${F_INTEXT_AUTO}" | grep -P "^geographical:" | sed -r 's/^geographical:\t//' > "${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}l_intext"
  cut -f2- "${F_INTEXT_AUTO}" > "${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}x_intext"

  #======================================================================
  # cp stop_list stop_list.all.sorted # TODO: is there needed some special version of stoplist for autocomplete?

  #======================================================================
  # skript, ktery slouci duplicty (cisla radku do jednoho) a vytvori pro prislusny soubor konecny automat
  for atm_type in "${ATM_TYPES_AUTOCOMPLETE[@]}"
  do
    CMD="python3 uniq_namelist.py -s \"${FOUT_STOPLIST}\""
    if test -f "${F_CONFIDENCE}"
    then
      CMD+=" -c ${F_CONFIDENCE}"
    fi
    run "${CMD} < \"${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}${atm_type}_intext\" > \"${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}${atm_type}_namelist\""
    for ext in "${EXTS[@]}"
    do
      makeAutomata "${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}${atm_type}_namelist" "${DIR_OUTPUTS}/${F_INTEXT_NAMELIST_BASE_PREFIX}${atm_type}_automata${ext}"
    done
  done

  #=====================================================================
  # smazani mezivysledku
  #rm -f intext_auto *_intext
  #rm -f *_namelist
  #rm -f KB_confidence
fi
