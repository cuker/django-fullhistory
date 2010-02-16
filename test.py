from testproject.manage import execute_manager, settings
import sys
sys.argv.insert(1, 'test')
execute_manager(settings)
