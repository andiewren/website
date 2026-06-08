html: clean
	python3 make.py

clean:
	if [ -d "html" ]; then \
		rm -r html; \
	fi;

serve: clean html
	cd html; python -m http.server
	
