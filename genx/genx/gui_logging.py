'''
  Module used to setup the default GUI logging and messaging system.
  The system contains on a python logging based approach with logfile,
  console output and GUI output dependent on startup options and
  message logLevel.
'''

import sys
import atexit
import logging
import traceback
import inspect
import warnings
from numpy import seterr, seterrcall, ComplexWarning
from io import StringIO
from .version import __version__ as str_version

# default options used if nothing is set in the configuration
CONSOLE_LEVEL, FILE_LEVEL, GUI_LEVEL=logging.WARNING, logging.DEBUG, logging.INFO

# set log levels according to options
if 'pdb' in list(sys.modules.keys()) or 'pydevd' in list(sys.modules.keys()):
  # if common debugger modules have been loaded, assume a debug run
  CONSOLE_LEVEL, FILE_LEVEL, GUI_LEVEL=logging.INFO, logging.DEBUG, logging.INFO
elif '--debug' in sys.argv:
  sys.argv.remove('--debug')
  CONSOLE_LEVEL, FILE_LEVEL, GUI_LEVEL=logging.DEBUG, logging.DEBUG, logging.INFO

def excepthook_overwrite(*exc_info):
  logging.critical('python error', exc_info=exc_info)

def ip_excepthook_overwrite(self, etype, value, tb, tb_offset=None):
  logging.critical('python error', exc_info=(etype, value, tb))

def goodby():
  logging.info('*** GenX %s Logging ended ***'%str_version)

def iprint(*objects, sep=None, end=None, file=None, flush=False):
  """
  A logging function that behaves like print but uses logging.info.
  """
  if sep is None:
    sep=' '
  if end is None:
    end='\n'
  logging.info(sep.join(map(str, objects))+end)
  

class NumpyLogger(logging.getLoggerClass()):
  '''
    A logger that makes sure the actual function definition filename, lineno and function name
    is used for logging numpy floating point errors, not the numpy_logger function.
  '''

  if sys.version_info[0:2]>=(3, 2): #sinfo was introduced in python 3.2
    def makeRecord(self, name, lvl, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
      curframe=inspect.currentframe()
      calframes=inspect.getouterframes(curframe, 2)
      # stack starts with:
      # (this method, debug call, debug call rootlogger, numpy_logger, actual function, ...)
      ignore, fname, lineno, func, ignore, ignore=calframes[4]
      return logging.getLoggerClass().makeRecord(self, name, lvl, fname, lineno,
                                   msg, args, exc_info, func=func, extra=extra, sinfo=sinfo)
  else:
    def makeRecord(self, name, lvl, fn, lno, msg, args, exc_info, func=None, extra=None):
      curframe=inspect.currentframe()
      calframes=inspect.getouterframes(curframe, 2)
      # stack starts with:
      # (this method, debug call, debug call rootlogger, numpy_logger, actual function, ...)
      ignore, fname, lineno, func, ignore, ignore=calframes[4]
      return logging.getLoggerClass().makeRecord(self, name, lvl, fname, lineno,
                                                 msg, args, exc_info, func=func, extra=extra)

nplogger=None
def numpy_logger(err, flag):
  nplogger.debug('numpy floating point error encountered (%s)'%err)

def setup_system():
  logger=logging.getLogger()
  logger.setLevel(min(FILE_LEVEL, CONSOLE_LEVEL, GUI_LEVEL))

  # no console logger for windows (win32gui)
  console=logging.StreamHandler(sys.__stdout__)
  formatter=logging.Formatter('%(levelname) 7s: %(message)s')
  console.setFormatter(formatter)
  console.setLevel(CONSOLE_LEVEL)
  logger.addHandler(console)

  logging.getLogger('matplotlib').setLevel(logging.WARNING)
  if min(FILE_LEVEL, CONSOLE_LEVEL, GUI_LEVEL)>logging.DEBUG:
    logging.getLogger('numba').setLevel(logging.WARNING)
  logging.info('*** GenX %s Logging started ***'%str_version)

  # define numpy warning behavior
  global nplogger
  old_class=logging.getLoggerClass()
  logging.setLoggerClass(NumpyLogger)
  nplogger=logging.getLogger('numpy')
  nplogger.setLevel(logging.DEBUG)
  null_handler=logging.StreamHandler(StringIO())
  null_handler.setLevel(logging.CRITICAL)
  nplogger.addHandler(null_handler)
  logging.setLoggerClass(old_class)
  seterr(divide='call', over='call', under='ignore', invalid='call')
  #warnings.filterwarnings(action="error", category=ComplexWarning)
  logging.captureWarnings(True)
  seterrcall(numpy_logger)

  # write information on program exit
  # sys.excepthook=excepthook_overwrite
  atexit.register(goodby)

def activate_logging(logfile):
  logger=logging.getLogger()
  logfile=logging.FileHandler(logfile, 'w')
  formatter=logging.Formatter('[%(levelname)s] - %(asctime)s - %(filename)s:%(lineno)i:%(funcName)s %(message)s', '')
  logfile.setFormatter(formatter)
  logfile.setLevel(FILE_LEVEL)
  logger.addHandler(logfile)
  logger.info('*** GenX %s Logging started to file ***'%str_version)


