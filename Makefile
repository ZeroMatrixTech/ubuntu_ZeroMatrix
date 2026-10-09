.DEFAULT_GOAL := iso

# Override at invocation: make iso VERSION=0.1.0-rc2 BASE_SHA256=...
# VERSION defaults to the VERSION file; relative paths are relative to this repo.
VERSION ?=
BASE_ISO ?= ubuntu-26.04.1-desktop-amd64.iso
BASE_SHA256 ?=
DEBS_DIR ?=
VSIX_DIR ?=
ACLT_DIR ?=
CODE_DEB ?=
ACQUIRE_DIR ?=
export VERSION BASE_ISO BASE_SHA256 DEBS_DIR VSIX_DIR ACLT_DIR CODE_DEB ACQUIRE_DIR

.PHONY: iso check test bundle editor workspace code-info code-lock acquire help

PROFILE ?= vm
export PROFILE

iso: check test rootfs
	python3 scripts/build-online.py

iso-vm:
	$(MAKE) iso PROFILE=vm

iso-physical:
	$(MAKE) iso PROFILE=physical

isos:
	$(MAKE) iso-vm
	$(MAKE) iso-physical

base-import:
	python3 scripts/media-tree.py import

base-check:
	python3 scripts/media-tree.py verify

ROOTFS_BUILD ?=
export ROOTFS_BUILD
rootfs: base-check
	python3 scripts/rootfs-entry.py


legacy-iso:
	python3 scripts/make-build.py iso

check:
	python3 scripts/build-online.py check

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
	bash -n scripts/collect-packages.sh scripts/provision.sh scripts/verify.sh scripts/zeromatrix-code scripts/zeromatrix-first-login scripts/provision-online.sh

bundle:
	python3 scripts/make-build.py bundle

editor:
	python3 scripts/make-build.py editor

workspace:
	python3 scripts/make-build.py workspace

code-info:
	python3 scripts/code-input.py info

code-lock:
	python3 scripts/code-input.py lock

acquire:
	python3 scripts/acquire.py

help:
	@printf '%s\n' \
	  'make iso PROFILE=vm|physical  Build an online installation ISO (default: vm)' \
	  'make isos      Build both profiles' \
	  'make base-import  Import original ISO as browsable files and boot records' \
	  'make base-check Verify the expanded base/media tree' \
	  'make check     Check online build tools and selected profile' \
	  'make test      Run package/build-entry tests and Bash syntax checks' \
	  'make bundle DEBS_DIR=/path/to/debs  Prepare the offline repository' \
	  'make editor VSIX_DIR=/path/to/vsix  Import offline editor extensions' \
	  'make workspace ACLT_DIR=/path/to/ACLt  Export a clean offline project seed' \
	  'make code-info  Validate and show the imported VS Code package' \
	  'make code-lock CODE_DEB=/path/to/code.deb  Record an intentional package update' \
	  'make acquire    Download the reviewed package and extension locks (network required)' \
	  'VERSION defaults to the VERSION file.' \
	  'Online builds default to the verified SHA256 in config/base-iso.json.' \
	  'BASE_ISO defaults to ubuntu-26.04.1-desktop-amd64.iso.'

.PHONY: iso-vm iso-physical isos base-import base-check legacy-iso
.NOTPARALLEL:

.PHONY: rootfs base-check
