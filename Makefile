.PHONY: all clean

all:
	if test `git submodule status | grep -cP "^-"` -gt 0; then git submodule update --init; fi
	make -C ./SharedKB/var2/
	make -C ./figa/src/

clean:
	make -C ./SharedKB/var2/ clean
	make -C ./figa/src/ clean
