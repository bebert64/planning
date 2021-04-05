set init_path=%CD%
call C:/Users/CassanR/Miniconda3/Scripts/activate
call conda activate planning 
call cd %~dp0%
call sphinx-build -b html -c documentation documentation/source documentation/build
call conda deactivate
call cd %init_path%