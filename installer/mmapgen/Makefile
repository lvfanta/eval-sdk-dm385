#$L$
# Copyright (C) 2013-2014 Ridgerun (http://www.ridgerun.com). 
#$L$

ifeq ($(DEVDIR),)
$(error ====== DEVDIR variable is empty, invoke this Makefile from the BSP root, or provide the path to it =====)
endif
include $(DEVDIR)/bsp/mach/Make.conf
include $(MMAPGENDIR)/Makefile.board

.PHONY: memorymap memorymapgen

MMAPGEN_EXE=$(DEVDIR)/installer/$(MMAPGEN)/src/mmapgen.py
MMAPGEN_VERBOSE=$(if $(VERBOSE:0=),--verbose)

ifeq ($(CONFIG_INSTALLER_MODE_SD_CARD),y)
MMAPGEN_MODES=sd
else ifeq ($(CONFIG_INSTALLER_MODE_ATTACHED_BOARD),y)
ifeq ($(CONFIG_FS_TARGET_SD),y)
MMAPGEN_MODES=nand sd-fs
else
MMAPGEN_MODES=nand
endif
else ifeq ($(CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER),y)
MMAPGEN_MODES=nand sd-script
endif

ifneq ($(CONFIG_BSP_NAND_PAGE_SIZE),)
MMAPGEN_ARGS += --nand-page-size $(CONFIG_BSP_NAND_PAGE_SIZE)
endif

ifneq ($(CONFIG_BSP_NAND_BLOCK_SIZE),)
MMAPGEN_ARGS += --nand-block-size $(CONFIG_BSP_NAND_BLOCK_SIZE)
endif

memorymapgen::
	$(V) # If the bootloader and kernel images doesn't exist, then this SDK haven't been compiled yet
	$(V) if [ -e $(BOOTLOADERIMAGE) -a -e $(KERNELIMAGE) ] ; then \
	    for m in $(MMAPGEN_MODES) ; do \
	      $(MMAPGEN_EXE) --board $(MMAPGEN_BOARD) -m $$m $(MMAPGEN_ARGS) $(MMAPGEN_VERBOSE) $(if $(DRAW:0=),--draw) ; \
	    done ; \
	  fi

memorymap::
	$(V) $(MAKE) memorymapgen DRAW=y

help_targets::
	@echo "   memorymapgen    - Generates the memorymap"
	@echo "   memorymap       - Generates and draws the memory map"
