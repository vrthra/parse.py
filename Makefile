test: example.calc
	python3 ./parser.py x.eg

debug: example.calc
	python3 -mpudb  ./parser.py x.eg

example.calc:
	echo 22 + 33 > example.calc


doctest:
	python3 -m doctest ./parser.py
