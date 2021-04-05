set init_path=%CD%
call C:/Users/CassanR/Miniconda3/Scripts/activate
call conda activate shortcuts
call cd %~dp0%
call cd shortcuts
call python app.py
call conda deactivate
call cd %init_path%