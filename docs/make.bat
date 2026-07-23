@ECHO OFF
if "%SPHINXBUILD%" == "" set SPHINXBUILD=sphinx-build
set SOURCEDIR=src
set BUILDDIR=_build
set SPHINXOPTS=--fail-on-warning --keep-going
%SPHINXBUILD% -b %1 %SOURCEDIR% %BUILDDIR%\%1 %SPHINXOPTS%
