SPHINXOPTS    ?= --fail-on-warning --keep-going
SPHINXBUILD   ?= sphinx-build
PYTHON        ?= python
SOURCEDIR     = src
BUILDDIR      = _build

.PHONY: help browser clean html
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

clean:
	rm -rf $(BUILDDIR) $(SOURCEDIR)/reference/generated

browser:
	@$(PYTHON) build_browser.py

html: browser
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)
