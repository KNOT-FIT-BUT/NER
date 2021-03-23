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

#=====================================================================
# nastavovani parametru prikazove radky

usage()
{
  echo "Usage: create_cedar.sh [-h] [--all|--autocomplete|-l|-u] [-c] [-d] [-I ${DIR_INPUTS}] [-O ${DIR_OUTPUTS}] [-p ${PROCESSES}] [-k ${KB}] --lang=<language>"
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
  echo ""
}


getGitBasedVersion()
{
  _OLDPWD=$PWD
  cd $1

  VERSION=`git rev-parse --short HEAD 2>/dev/null`
  if test "${?}" -eq 0 && test "$PWD" == "`git rev-parse --show-toplevel`"
  then
    if ! test -z "`git status --short`"
    then
      VERSION="${VERSION}_dirty_`date \"+%Y%m%d-%H%M%S\"`"
    fi
  else
    VERSION="nogit_`date \"+%Y%m%d-%H%M%S\"`"
  fi
  cd ${_OLDPWD}
  
  echo $VERSION
}


makeAutomata() {
  F_NAMELIST=$1
  F_AUTOMATA=$2
  ../figa/figav1.0 -d "${F_NAMELIST}" -n -w "${F_AUTOMATA}"
}


makeCommonAutomata() {
  EXT=$1

  F_NAMELIST_BASE="${DIR_OUTPUTS}/namelist"
  F_ATM_BASE="${DIR_OUTPUTS}/automata"

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
  cat "${KB}" | sed '0,/^$/d' | awk '{print $(NF)}' > "${1}"
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
                exit
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
        *)
            echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 1
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
  exit 2
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
  NAMEGEN_VERSION=`getGitBasedVersion "./lang_modules/cs/czechnames/"`
  echo "CZECH NAMEGEN version: ${NAMEGEN_VERSION}"
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
if test "${CLEAN_CACHED}" = "true" || ! test -f "${F_ENTITIES_WITH_TYPEFLAGS}"; then
  # Be careful > "Ά" or "Α" in "sed" is foreign char not "A" from Latin(-base) chars.
  python3 get_entities_with_typeflags.py -k "$KB" --lang ${LANG} | awk -F"\t" 'NF>2{key = $1 "\t" $2 "\t" $3; a[key] = a[key] (a[key] ? " " : "") $4;};END{for(i in a) print i "\t" a[i]}' > "${F_TMP_ENTITIES_WITH_TYPEFLAGS}"
  mv "${F_TMP_ENTITIES_WITH_TYPEFLAGS}" "${F_ENTITIES_WITH_TYPEFLAGS}" 2>/dev/null
fi

if ! test -f "${F_ENTITIES_TAGGED_INFLECTIONS}" || test `stat -c %Y "${F_ENTITIES_TAGGED_INFLECTIONS}"` -lt `stat -c %Y "${F_ENTITIES_WITH_TYPEFLAGS}"` || test "${CLEAN_CACHED}" = true; then
  python3 get_entities_tagged_inflections.py -l ${LANG} -o "${F_TMP_ENTITIES_TAGGED_INFLECTIONS}" -i "${F_ENTITIES_WITH_TYPEFLAGS}" >"${F_TMP_ENTITIES_TAGGED_INFLECTIONS}.log" 2>"${F_TMP_ENTITIES_TAGGED_INFLECTIONS}.err.log" #-x "${F_ENTITIES_TAGGED_INFLECTIONS_INVALID}_gender" -X "${F_ENTITIES_TAGGED_INFLECTIONS_INVALID}_inflection" "${F_ENTITIES_WITH_TYPEFLAGS}"
  mv "${F_TMP_ENTITIES_TAGGED_INFLECTIONS}" "${F_ENTITIES_TAGGED_INFLECTIONS}"
fi

if test "${CLEAN_CACHED}" = true
then
  KB2NAMELIST_ARGS="--clean-cached"
fi
SCRIPT_KB2NAMELIST="python3 KB2namelist.py -l ${LANG} -k ${KB} -t \"${F_ENTITIES_TAGGED_INFLECTIONS}\" -I \"${DIR_INPUTS}\" -O \"${DIR_OUTPUTS}\" -n ${PROCESSES} ${KB2NAMELIST_ARGS}"
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
F_STOP_LIST="${F_STOPLIST_BASE}.all.sorted"
if $ATM_ALL || ! $ATM_URI
then
  python get_morphological_forms.py < "${DIR_INPUTS}/${LANG}/stoplist.txt" | sort -u > "${F_STOPLIST_BASE}.var"
  cp "${F_STOPLIST_BASE}.var" "${F_STOPLIST_BASE}.all"
  sed -e 's/\b\(.\)/\u\1/g' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
  tr 'a-z' 'A-Z' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
  tr 'A-Z' 'a-z' < "${F_STOPLIST_BASE}.var" >> "${F_STOPLIST_BASE}.all"
  sort -u "${F_STOPLIST_BASE}.all" > "${F_STOP_LIST}"
fi


if $ATM_COMMON || $ATM_LOWERCASE || $ATM_URI
then
  #=====================================================================
  # vytvoreni seznamu klicu entit v KB, pridani fragmentu jmen a prijmeni entit a zajmen
  F_INTEXT_BASE="${DIR_OUTPUTS}/intext"
  if $ATM_COMMON
  then
    eval "${SCRIPT_KB2NAMELIST}" | tr -s ' ' > "${F_INTEXT_BASE}"
  fi
  if $ATM_LOWERCASE
  then
    eval "${SCRIPT_KB2NAMELIST} -d" | tr -s ' ' > "${F_INTEXT_BASE}_lower"
  fi
  if $ATM_URI
  then
    eval "${SCRIPT_KB2NAMELIST} -u" > "${F_INTEXT_BASE}_uri"
  fi

  #=====================================================================
  # parsovanie confidence hodnot do samostatneho suboru
  # redukcia duplicit, abecedne zoradenie entit
  # odstranovani slov ze stop listu
  F_NAMELIST_BASE="${DIR_OUTPUTS}/namelist"
  if $ATM_ALL || ! $ATM_URI
  then
    cutoutConfidence "${F_CONFIDENCE}"
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
      python uniq_namelist.py -s "${STOP_LIST}" -c "${F_CONFIDENCE}" < "${F_INTEXT_BASE}${fname_suffix}" > "${F_NAMELIST_BASE}${fname_suffix}"
    done
  fi
  if $ATM_URI
  then
    python uniq_namelist.py -s "${STOP_LIST}" < "${F_INTEXT_BASE}_uri" > "${F_NAMELIST_BASE}_uri"
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
  F_INTEXT_AUTO="${DIR_OUTPUTS}/intext_auto"
  eval "${SCRIPT_KB2NAMELIST} -a" | tr -s ' ' | grep -v -e "[^;]N" > "${F_INTEXT_AUTO}"
  cat "${F_INTEXT_AUTO}" | grep -P "^person:" | sed -r 's/^person:\t//' > "${DIR_OUTPUTS}/p_intext"
  cat "${F_INTEXT_AUTO}" | grep -P "^geographical:" | sed -r 's/^geographical:\t//' > "${DIR_OUTPUTS}/l_intext"
  cut -f2- "${F_INTEXT_AUTO}" > "${DIR_OUTPUTS}/x_intext"

  #======================================================================
  # parsovanie confidence hodnot do samostatneho suboru + stop list
  cutoutConfidence "${F_CONFIDENCE}"
  # cp stop_list stop_list.all.sorted # TODO: is there needed some special version of stoplist for autocomplete?

  #======================================================================
  # skript, ktery slouci duplicty (cisla radku do jednoho) a vytvori pro prislusny soubor konecny automat
  for atm_type in "${ATM_TYPES_AUTOCOMPLETE[@]}"
  do
    python uniq_namelist.py -s "${STOP_LIST}" -c "${F_CONFIDENCE}" < "${DIR_OUTPUTS}/${atm_type}_intext" > "${DIR_OUTPUTS}/${atm_type}_namelist"
    for ext in "${EXTS[@]}"
    do
      makeAutomata "${DIR_OUTPUTS}/${atm_type}_namelist" "${DIR_OUTPUTS}/${atm_type}_automata${ext}"
    done
  done

  #=====================================================================
  # smazani mezivysledku
  #rm -f intext_auto *_intext
  #rm -f *_namelist
  #rm -f KB_confidence
fi
