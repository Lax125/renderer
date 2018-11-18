#!/usr/bin/env python
'''
main.py
Entry point for main graphical application.

Made solely by Marcus Koh
'''
import os

def start_debug():
    open("debug.log", "w").close()
def debug(msg):
    with open("debug.log", 'a') as f:
        f.write(msg+'\n')

def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

start_debug()

from all_modules import *
from mainapp import MainApp

def run(*args, **kwargs):
    '''Runs the main graphical application.'''
    sys.except_hook = except_hook
    window = QApplication(sys.argv)
    debug("Window made.")
    QCoreApplication.setApplicationName(APPNAME)
    app = MainApp()
    debug("App constructed.")
    app.restoreProject()
    debug("Startup sequence completed.")
    window.exec_()
    debug("Application exited normally.")

if __name__ == "__main__": # MAIN ENTRY POINT
    run()
