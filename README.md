# pyshader_minifier
Shader minifier interface and validation library for Python with a neat UI.

![Screenshot](https://github.com/LeStahL/pyshader_minifier/blob/main/screenshot.png?raw=true)

# Build
You need Python and poetry installed and in your system `PATH`. Before building, install the dependencies by running `poetry config virtualenvs.in-project true` and then `poetry install` from the source root.

For debugging, run `poetry run python -m shader_minifier` from the source root.

For building an executable, run `poetry run pyinstaller pyinstaller.spec` from the source root. The executable and a release archive will be generated in the `dist` subfolder.

# Use
pyshader_minifier can
* Find and download all tagged shader minifier versions.
* Interface shader_minifier from python.
* Automatically validate input and minified sources to detect problems quickly.
* Watch a shader file for changes on disk in the background.
* Display the minified file sizes of successive iterations of a shader file and their relative size gain when compared to the unminified source.
* Display the diff between the current state's (minified or original) source and a reference state in the history to obtain fine grained information on what shader_minifier did. That's a neat way to know whether or not your newest smart optimization actually decreased the minified source size!
* Change between tagged shader_minifier versions quickly.
* Create a commit with the current crunching state by only pressing a button in the UI.
* Display the entropy of your intro using a custom build command. Currently supports Crinkler(Loonies)-based output and Prost(Epoqe)-based output.
* Export the entire history of your crunching session to a JSON format (maybe you want to save that specific version you skipped over quickly?).

# License
pyshader_minifier is (c) 2024 Alexander Kraus <nr4@z10.info> and GPLv3; see LICENSE for details.
