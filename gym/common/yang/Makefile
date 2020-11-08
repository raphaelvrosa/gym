.DEFAULT_GOAL := all

DOC_DIR := "docs"
PYBINDPLUGIN := $(shell python3 -c 'import pyangbind; import os; print("{}/plugin".format(os.path.dirname(pyangbind.__file__)))')

validate:
	# generate docs
	pyang vnf-bd.yang -f tree -o "$(DOC_DIR)/vnf-bd.tree"
	pyang vnf-bd.yang -f jstree -o "$(DOC_DIR)/vnf-bd.html"
	pyang vnf-bd.yang -f uml -o "$(DOC_DIR)/vnf-bd.uml"
	
	pyang vnf-pp.yang -f tree -o "$(DOC_DIR)/vnf-pp.tree"
	pyang vnf-pp.yang -f jstree -o "$(DOC_DIR)/vnf-pp.html"
	pyang vnf-pp.yang -f uml -o "$(DOC_DIR)/vnf-pp.uml"
	
	pyang vnf-br.yang -f tree -o "$(DOC_DIR)/vnf-br.tree"
	pyang vnf-br.yang -f jstree -o "$(DOC_DIR)/vnf-br.html"
	pyang vnf-br.yang -f uml -o "$(DOC_DIR)/vnf-br.uml"
	
build:
	# generate / compile python model
	pyang --plugindir $(PYBINDPLUGIN) -f pybind -p --use-xpath-helper --use-extmethods -o vnf_bd.py vnf-bd.yang
	pyang --plugindir $(PYBINDPLUGIN) -f pybind -p --use-xpath-helper --use-extmethods -o vnf_pp.py vnf-pp.yang
	pyang --plugindir $(PYBINDPLUGIN) -f pybind -p --use-xpath-helper --use-extmethods -o vnf_br.py vnf-br.yang

	#In vnf_bd.py and vnf_pp.py - Replace ALL: self._path_helper = False -> self._path_helper = kwargs.get("path_helper", False)

all: validate build

clean:
	rm doc/*