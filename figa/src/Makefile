CFLAGSBASE=-g -std=c++11
CFLAGS=$(CFLAGBASE) -ftree-vectorize -fPIC -DFLEXIBLE -DSTOPBIT -DNEXTBIT
#HEADS=figa_cedar.h figa_cedar.tpp figa.h cedar.h darts.h
FIGA=figav1.0

MARKER_WRAP_CC=marker_wrap.cc
OUTDIR=..

UNAME := $(shell uname -m)

ifeq ($(UNAME), x86_64)
  SWIG_F=
  GPP_F=-m64
else
  SWIG_F=-classic
  GPP_F=
endif

ifeq ($(OUTDIR), "")
  OUTDIR=.
endif

FIGA := $(OUTDIR)/$(FIGA)
MARKER := $(OUTDIR)/_marker.so
KB_LOADER := $(OUTDIR)/kb_loader.so

.PHONY: all clean


all: $(FIGA) $(MARKER) $(KB_LOADER)

%.o: %.cpp
	g++ $(CFLAGS) -c $< -o $@

$(FIGA): main.o figa_cedar.o
	$(CXX) $(CFLAGSBASE) $^ -o $@

$(MARKER): figa_cedar.o figa.o marker_wrap.o
	$(CXX) $(GPP_F) $(CFLAGS) -shared $^ -o $@

marker_wrap.o: $(MARKER_WRAP_CC)
	$(CXX) -fPIC $(CFLAGS) -c $< $$(python3-config --includes)

$(MARKER_WRAP_CC): marker.i
	swig -c++ -python -py3 $(SWIG_F) -o $@ -outdir $(OUTDIR) $<

# fast stores entity to rows   |   slow stores each items of entity
# -> accesses to entity only   |   -> accesses to entity and its items
# mem: 90 MB RAM               |   mem: 317 MB RAM 

$(KB_LOADER): $(OUTDIR)/kb_loader_slow.so

$(OUTDIR)/kb_loader_%.so: kb_loader_%.o
	$(CXX) -shared -Wl,-soname,$(notdir $(KB_LOADER)) -o $(KB_LOADER) $<
	touch $@

kb_loader_%.o: kb_loader_%.cpp
	$(CXX) -fPIC -c $< -o $@


clean: 
	rm -f *.o *.pyc
	rm -f $(MARKER_WRAP_CC) $(OUTDIR)/marker.py
	rm -f $(OUTDIR)/*.so $(FIGA) $(MARKER)
