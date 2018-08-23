#!/usr/bin/python

from setuptools import setup
import distutils.command.install_scripts
import shutil

f = open('README')
long_description = f.read().strip()
f.close()

# idea from http://stackoverflow.com/a/11400431/2139420
class strip_py_ext(distutils.command.install_scripts.install_scripts):
    def run(self):
        distutils.command.install_scripts.install_scripts.run(self)
        for script in self.get_outputs():
            if script.endswith(".py"):
                shutil.move(script, script[:-3])


setup(
    name = "gstatus2",
    version= "1.00",
    description= "Show the current health of the components in a glusterfs Trusted Storage Pool (fork from https://github.com/pcuzner/gstatus)",
    long_description = long_description,
    author = "Filippo Ferrazini",
    author_email = "filippo.ferrazini@gmail.com",
    url = "https://github.com/Filippo125/gstatus",
    license = "GPLv3",
    packages = [
        "gstatus",
        "gstatus.gstatuscfg",
        "gstatus.libgluster",
        "gstatus.libcommand",
        "gstatus.libutils"
        ],
    scripts = [ "gstatus.py" ],
    cmdclass = {
        "install_scripts" : strip_py_ext
    }
)
