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

iso: check test
	python3 scripts/make-build.py iso

check:
	python3 scripts/make-build.py check

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
	bash -n scripts/collect-packages.sh scripts/provision.sh scripts/verify.sh scripts/zeromatrix-code scripts/zeromatrix-first-login

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
	  'make iso       Build the candidate ISO for VERSION (default target)' \
	  'make check     Check build tools, base hash configuration and offline bundle' \
	  'make test      Run package/build-entry tests and Bash syntax checks' \
	  'make bundle DEBS_DIR=/path/to/debs  Prepare the offline repository' \
	  'make editor VSIX_DIR=/path/to/vsix  Import offline editor extensions' \
	  'make workspace ACLT_DIR=/path/to/ACLt  Export a clean offline project seed' \
	  'make code-info  Validate and show the imported VS Code package' \
	  'make code-lock CODE_DEB=/path/to/code.deb  Record an intentional package update' \
	  'make acquire    Download the reviewed package and extension locks (network required)' \
	  'VERSION defaults to the VERSION file.' \
	  'BASE_SHA256 must be the officially verified SHA256, or set config/base-iso.sha256.' \
	  'BASE_ISO defaults to ubuntu-26.04.1-desktop-amd64.iso.'
