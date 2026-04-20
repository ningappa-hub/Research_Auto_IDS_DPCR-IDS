#
# OMNeT++/OMNEST Makefile for dpcr-ids-sim
#
# This file was generated with the command:
#  opp_makemake -f --deep -O out -o dpcr-ids-sim -I/c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/include -L/c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/lib -lonnxruntime -X out
#

# Name of target to be created (-o option)
TARGET_DIR = .
TARGET_NAME = dpcr-ids-sim$(D)
TARGET = $(TARGET_NAME)$(EXE_SUFFIX)
TARGET_FILES = $(TARGET_DIR)/$(TARGET)

# User interface (uncomment one) (-u option)
USERIF_LIBS = $(ALL_ENV_LIBS) # that is, $(QTENV_LIBS) $(CMDENV_LIBS)
#USERIF_LIBS = $(CMDENV_LIBS)
#USERIF_LIBS = $(QTENV_LIBS)

# C++ include paths (with -I)
INCLUDE_PATH = -I/c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/include

# Additional object and library files to link with
EXTRA_OBJS =

# Additional libraries (-L, -l options)
LIBS = $(LDFLAG_LIBPATH)/c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/lib  -lonnxruntime

# Output directory
PROJECT_OUTPUT_DIR = ../out
PROJECTRELATIVE_PATH = src
O = $(PROJECT_OUTPUT_DIR)/$(CONFIGNAME)/$(PROJECTRELATIVE_PATH)

# Object files for local .cc, .msg and .sm files
OBJS = \
    $O/ids/CanExpertIDS.o \
    $O/ids/ConfidenceRouter.o \
    $O/ids/DecisionAggregator.o \
    $O/ids/EthExpertIDS.o \
    $O/ids/FusionIDS.o \
    $O/nodes/AlertSink.o \
    $O/nodes/CanBusHub.o \
    $O/nodes/EthBusHub.o \
    $O/traffic/CanTrafficGen.o \
    $O/traffic/DosAttacker.o \
    $O/traffic/EthTrafficGen.o \
    $O/traffic/FuzzyAttacker.o \
    $O/traffic/SpoofAttacker.o \
    $O/utils/OnnxInference.o \
    $O/msg/AlertMsg_m.o \
    $O/msg/CanFrameMsg_m.o \
    $O/msg/EthFrameMsg_m.o \
    $O/msg/ExpertOutput_m.o \
    $O/msg/FusionResult_m.o

# Message files
MSGFILES = \
    msg/AlertMsg.msg \
    msg/CanFrameMsg.msg \
    msg/EthFrameMsg.msg \
    msg/ExpertOutput.msg \
    msg/FusionResult.msg

# SM files
SMFILES =

#------------------------------------------------------------------------------

# Pull in OMNeT++ configuration (Makefile.inc)

ifneq ("$(OMNETPP_CONFIGFILE)","")
CONFIGFILE = $(OMNETPP_CONFIGFILE)
else
CONFIGFILE = $(shell opp_configfilepath)
endif

ifeq ("$(wildcard $(CONFIGFILE))","")
$(error Config file '$(CONFIGFILE)' does not exist -- add the OMNeT++ bin directory to the path so that opp_configfilepath can be found, or set the OMNETPP_CONFIGFILE variable to point to Makefile.inc)
endif

include $(CONFIGFILE)

# Simulation kernel and user interface libraries
OMNETPP_LIBS = $(OPPMAIN_LIB) $(USERIF_LIBS) $(KERNEL_LIBS) $(SYS_LIBS)
ifneq ($(PLATFORM),win32)
LIBS += -Wl,-rpath,$(abspath /c/ResearchAutoIDS/dpcr-ids-sim/onnxruntime-linux-x64-1.17.0/lib)
endif

COPTS = $(CFLAGS) $(IMPORT_DEFINES)  $(INCLUDE_PATH) -I$(OMNETPP_INCL_DIR)
MSGCOPTS = $(INCLUDE_PATH)
SMCOPTS =

# we want to recompile everything if COPTS changes,
# so we store COPTS into $COPTS_FILE (if COPTS has changed since last build)
# and make the object files depend on it
COPTS_FILE = $O/.last-copts
ifneq ("$(COPTS)","$(shell cat $(COPTS_FILE) 2>/dev/null || echo '')")
  $(shell $(MKPATH) "$O")
  $(file >$(COPTS_FILE),$(COPTS))
endif

#------------------------------------------------------------------------------
# User-supplied makefile fragment(s)
#------------------------------------------------------------------------------

# Main target
all: $(TARGET_FILES)

$(TARGET_DIR)/% :: $O/%
	@mkdir -p $(TARGET_DIR)
	$(Q)$(LN) $< $@
ifeq ($(TOOLCHAIN_NAME),clang-msabi)
	-$(Q)-$(LN) $(<:%.dll=%.lib) $(@:%.dll=%.lib) 2>/dev/null

$O/$(TARGET_NAME).pdb: $O/$(TARGET)
endif

$O/$(TARGET): $(OBJS)  $(wildcard $(EXTRA_OBJS)) Makefile $(CONFIGFILE)
	@$(MKPATH) $O
	@echo Creating executable: $@
	$(Q)$(CXX) $(LDFLAGS) -o $O/$(TARGET) $(OBJS) $(EXTRA_OBJS) $(AS_NEEDED_OFF) $(WHOLE_ARCHIVE_ON) $(LIBS) $(WHOLE_ARCHIVE_OFF) $(OMNETPP_LIBS)

.PHONY: all clean cleanall depend msgheaders smheaders

# disabling all implicit rules
.SUFFIXES :
.PRECIOUS : %_m.h %_m.cc

$O/%.o: %.cc $(COPTS_FILE) | msgheaders smheaders
	@$(MKPATH) $(dir $@)
	$(qecho) "$<"
	$(Q)$(CXX) -c $(CXXFLAGS) $(COPTS) -o $@ $<

%_m.cc %_m.h: %.msg
	$(qecho) MSGC: $<
	$(Q)$(MSGC) -s _m.cc -MD -MP -MF $O/$(basename $<)_m.h.d $(MSGCOPTS) $<

%_sm.cc %_sm.h: %.sm
	$(qecho) SMC: $<
	$(Q)$(SMC) -c++ -suffix cc $(SMCOPTS) $<

msgheaders: $(MSGFILES:.msg=_m.h)

smheaders: $(SMFILES:.sm=_sm.h)

clean:
	$(qecho) Cleaning $(TARGET)
	$(Q)-rm -rf $O
	$(Q)-rm -f $(TARGET_FILES)
	$(Q)-rm -f $(call opp_rwildcard, . , *_m.cc *_m.h *_sm.cc *_sm.h)

cleanall:
	$(Q)$(CLEANALL_COMMAND)
	$(Q)-rm -rf $(PROJECT_OUTPUT_DIR)

help:
	@echo "$$HELP_SYNOPSYS"
	@echo "$$HELP_TARGETS"
	@echo "$$HELP_VARIABLES"
	@echo "$$HELP_EXAMPLES"

# include all dependencies
-include $(OBJS:%=%.d) $(MSGFILES:%.msg=$O/%_m.h.d)
