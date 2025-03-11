
import sys, traceback
from xaip_tools import xaip_tools, xaip_util


if __name__ == '__main__':
  xaip_tools.LOCAL=True
  xaip_util.set_local()
  d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn = sys.argv[1:]
  print (d_fn, p_fn, d_interp_fn, p_interp_fn)
  xaip_tools.interactive_from_files(d_fn, p_fn, d_interp_fn, p_interp_fn, sys_settings_fn)  
