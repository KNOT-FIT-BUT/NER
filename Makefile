.PHONY: all clean

all:
	git submodule update --init
	make -C ./SharedKB/var2/
	make -C ./figa/src/

clean:
	make -C ./SharedKB/var2/ clean
	make -C ./figa/src/ clean
