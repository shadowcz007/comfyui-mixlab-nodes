@echo off

set "requirements_txt=%~dp0\requirements.txt"
set "python_exec=..\..\..\python_embeded\python.exe"

echo Installing ComfyUI's Mixlab Nodes..

if exist "%python_exec%" (
    echo Installing with ComfyUI Portable
    for /f "delims=" %%i in (%requirements_txt%) do (
        %python_exec% -s -m pip install "%%i" -i https://pypi.tuna.tsinghua.edu.cn/simple
    )
) else (
    echo Installing with system Python
    for /f "delims=" %%i in (%requirements_txt%) do (
        pip install "%%i" -i https://pypi.tuna.tsinghua.edu.cn/simple
    )
)

pause