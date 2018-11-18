name = "ZEdit"

# set current directory to immediate parent
import sys, os
MY_DIR = os.path.dirname(os.path.realpath(__file__))

def run():
  cwd = os.getcwd()
  os.chdir(MY_DIR)
  import main
  main.run()
  os.chdir(cwd)
  
    
run()
