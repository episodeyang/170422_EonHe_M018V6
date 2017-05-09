default:
	make install
install:
	pip install -r requirements.txt
init-lib:
	# mkdir lib
	git subtree add --prefix lib/common https://github.com/gkoolstra/Common.git master
start-jupyter:
	sh start_jupyter.sh
list-jupyter:
	ps aux | grep jupyter
