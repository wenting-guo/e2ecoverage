TEMPLATE ?= template/template.md
run-web-server:
	git config --global credential.helper store
	pip3 install anybadge
	export MODE=web; python3 scripts/main.py

get-score: verify_param
	pip3 install -r requirements.txt
	python3 main.py ${PROJECT}
	git add badges/${PROJECT}/*.svg

verify_param:
	@if [ "${PROJECT}" == "" ];then \
		echo [Error] Parameter PROJECT should not be blank!  USAGE:"make XXXXX  PROJECT=YOUR_NAME"; \
		exit 1; \
	fi

.PHONY: project update-template clean run-server
	
