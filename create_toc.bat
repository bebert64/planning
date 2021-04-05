call C:/Users/CassanR/Miniconda3/Scripts/activate
call conda activate planning 
call sphinx-apidoc --force --separate --full -o documentation/source planning
call python documentation/modify_toc.py
call sphinx-build -b html -c documentation documentation/source documentation/build
call conda deactivate

