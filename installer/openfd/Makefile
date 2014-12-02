#$L$
# Copyright (C) 2013-2014 Ridgerun (http://www.ridgerun.com). 
#$L$

ifeq ($(DEVDIR),)
$(error ====== DEVDIR variable is empty, invoke this Makefile from the BSP root, or provide the path to it =====)
endif

include $(DEVDIR)/bsp/mach/Make.conf
include $(INSTALLERDIR)/mach/Make.defs

default_rule:

# Mmapgen

MMAPGEN_DIR=$(DEVDIR)/installer/$(MMAPGEN)

# Installer

INSTALLER_EXE?=$(LOCALDIR)/bin/openfd
INSTALLER_LOG?=$(LOGDIR)/openfd.log
INSTALLER_FORCE?=$(if $(FORCEINSTALL:0=),--force)

INSTALLER_ARGS+=$(if $(VERBOSE:0=),--verbose)
INSTALLER_ARGS+=$(if $(DRYRUNINSTALL:0=),--dryrun)
INSTALLER_ARGS+=$(if $(NONINTERACTIVEINSTALL:0=),--assume-yes)
INSTALLER_ARGS+=--log $(INSTALLER_LOG)
INSTALLER_ARGS+=$(INSTALLER_BOARD)

# Installer mode

ifeq ($(CONFIG_INSTALLER_MODE_SD_CARD),y)
include $(INSTALLERDIR)/Makefile.sd
else ifeq ($(CONFIG_INSTALLER_MODE_ATTACHED_BOARD),y)
include $(INSTALLERDIR)/Makefile.board
# There is a mixed mode in which all the components are installed to NAND
# except the filesystem. For this case we have to live including both Makefiles
# and coordinate the installation targets. I.e. installfs is handled by the SD
# makefile, while others -installbootloader, installkernel, etc.- are handled
# by the NAND makefile.
ifeq ($(CONFIG_FS_TARGET_SD),y)
include $(INSTALLERDIR)/Makefile.sd
endif
else ifeq ($(CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER),y)
include $(INSTALLERDIR)/Makefile.external
endif

# Filesystem

# Nand block info needed in hex
ifeq ($(CONFIG_FS_TARGET_REQUIRES_INSTALLER_GENERATION),y)
ifeq ($(CONFIG_BSP_NAND_BLOCK_SIZE),)
$(error Filesystem generation needs to know the NAND block size, please define CONFIG_BSP_NAND_BLOCK_SIZE)
endif
NAND_BLOCKINFO="BLOCKSIZE=$(shell printf '0x%x' $(CONFIG_BSP_NAND_BLOCK_SIZE))"
endif

# Nand page info needed in decimal
ifeq ($(CONFIG_FS_TARGET_REQUIRES_INSTALLER_GENERATION),y)
ifeq ($(CONFIG_FS_TARGET_REQUIRES_INSTALLER_PAGESIZE),y)
ifeq ($(CONFIG_BSP_NAND_PAGE_SIZE),)
$(error Filesystem generation needs to know the NAND page size, please define CONFIG_BSP_NAND_PAGE_SIZE)
endif
NAND_PAGEINFO="PAGESIZE=$(CONFIG_BSP_NAND_PAGE_SIZE)"
endif
endif

.PHONY: $(IMAGEDIR)/fsimage

installmemorymap:
	$(V) make -C $(MMAPGEN_DIR) memorymapgen $(QOUT)

installbootloadercheck:
	 $(V) if [ -f  "$(DEVDIR)/bsp/mach/ubootinstaller_notsupported" ] ; then \
	    echo "The installbootloader target is not supported on $(MACH_DESCRIPTION)"; \
	    exit -1; \
	 fi

$(IMAGEDIR)/fsimage:
ifeq ($(CONFIG_FS_TARGET_REQUIRES_INSTALLER_GENERATION),y)
	$(V) make -sC $(DEVDIR)/fs/fstargets genimage $(NAND_BLOCKINFO) $(NAND_PAGEINFO)
endif
	$(V) # The only posible filesystem that may need an image prefix is initrd, and we don't use it anymore
	$(V) cp $(IMAGEDIR)/fsimage $(IMAGEDIR)/fsimage.uImage

clean::

help_targets::
	@echo "   install         - Install all out of date images to target"
	@echo "   installbootloader - Install bootloader to target"
	@echo "   installkernel   - Install kernel to target"
	@echo "   installfs       - Install file system to target"
	@echo "   installcmdline  - Install uBoot kernel command line"
	@echo "   installbootcmd  - Install uBoot boot command"
	@echo "   installmtdparts - Install uBoot mtdparts"

help_parameters::
	@echo ' U-boot Installer Parameters ($$DEVDIR/installer/u-boot-installer)'
	@echo "   FORCEINSTALL    - Set to y to force performing the requested install target"
	@echo "   DRYRUNINSTALL   - Set to y to run in dryrun mode (system and uboot commands will be logged but not executed)"
	@echo "   NONINTERACTIVEINSTALL   - Set to y to run in non-interactive mode (automatic 'yes' to prompts)"

help_examples::
	@echo "   make installbootloader FORCEINSTALL=y"
