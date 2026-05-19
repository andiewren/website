html:
	python3 make.py

clean:
	if [ -d "html" ]; then \
		rm -r html; \
	fi;
